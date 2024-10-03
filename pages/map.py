import os
import ijson
import re
import geopandas as gpd
import duckdb
import streamlit as st
import pandas as pd
from shapely import wkt
import pydeck  as pdk
print (duckdb.__version__)

def is_geojson_empty(file_path):
    """
    Check if a GeoJSON file has no features.

    Parameters:
    - file_path (str): Path to the GeoJSON file.

    Returns:
    - bool: True if the GeoJSON has no features, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Create an ijson parser
            parser = ijson.parse(f)
            for prefix, event, value in parser:
                if prefix == 'features.item' and event == 'start_map':
                    # Found the start of the first feature
                    return False
                elif prefix == 'features' and event == 'start_array':
                    continue
                elif prefix == 'features' and event == 'end_array':
                    # Reached the end of the features array without finding any features
                    break
        return True  # No features found
    except Exception as e:
        # Log the error if necessary
        print(f"Error checking GeoJSON file {file_path}: {e}")
        return True  # Assume empty if there's an error
def sanitize_filename(name):
    """
    Sanitize the district name to create a valid filename.
    Removes or replaces characters that are invalid in filenames.
    """
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    # Remove any character that is not alphanumeric, underscore, or hyphen
    name = re.sub(r'[^\w\-]', '', name)
    return name
@st.cache_data
def build_duckdb_queries(sanitized_name, district_lot_geojson_path, district_housing_geojson_path):
    """
    Build a list of DuckDB SQL queries for the selected district.

    Parameters:
    - sanitized_name (str): Sanitized district name.
    - district_lot_geojson_path (str): Path to the district's lot GeoJSON file.
    - district_housing_geojson_path (str): Path to the district's housing GeoJSON file.

    Returns:
    - list of str: List containing all queries.
    """
    queries=[];
    # Check if the housing data file exists and is not empty
    if os.path.exists(district_housing_geojson_path):
        if is_geojson_empty(district_housing_geojson_path):
            # Housing data is empty, return an empty list of queries
            return queries
    else:
        # Housing data file does not exist, return an empty list of queries
        return queries

    # Proceed to build queries only if housing data is not empty

    # For districts with split files ("North", "Tai Po", "Yuen Long"), we need to handle them differently
    if sanitized_name in ["North", "Tai_Po", "Yuen_Long"]:
        print (f'{sanitized_name}')
        # Assume we have 4 parts for each of the split districts
        part_files = [f"data/{sanitized_name}_lot_part{i+1}.parquet" for i in range(4)]
        
        # Construct the UNION ALL query to combine all parts of the split files
        union_query = " UNION ALL ".join([f"SELECT OBJECTID,LOTID,ST_simplify(geometry,0.0001) as geom FROM read_parquet('{file}')" for file in part_files])
        
        # Query 1: Create or replace table for combined lot data
        query1 = f"""
        CREATE OR REPLACE TABLE {sanitized_name}_lot AS
        {union_query};
        """
        queries.append(query1)
    
    else:
        # For districts that do not have split files, load the single GeoJSON file as usual
        query1 = f"""
        CREATE OR REPLACE TABLE {sanitized_name}_lot AS
        SELECT OBJECTID, LOTID,
        geometry as geom
        FROM read_parquet('{district_lot_geojson_path}');
        """
        queries.append(query1)

    # Query 2: Create or replace table for housing units
    query2 = f"""
    CREATE OR REPLACE TABLE housing_units AS 
    SELECT 
        date, 
        address, 
        price, 
        CASE 
        WHEN changes LIKE '--' THEN 0 
        ELSE CAST(REGEXP_REPLACE(changes, '%', '') AS INT) 
        END AS changes,
        "saleable_area(ft^2)", 
        unit_rate, 
        district, 
        Tower, 
        Flat, 
        Phase, 
        Block, 
        Rental, 
        "Public Housing",   
        floor, 
        latitude,
        longitude,
        geom
    FROM st_read('{district_housing_geojson_path}');
    """
    queries.append(query2)

    # Query 3: Create average_price_per_lot table
    query3 = f"""
    CREATE OR REPLACE TABLE average_price_per_lot AS
    SELECT
        lot.LOTID,
        AVG(h.unit_rate) AS avg_unit_price,
        AVG(h.changes) AS avg_change
    FROM
        {sanitized_name}_lot AS lot
    LEFT JOIN
        housing_units AS h
    ON
        ST_Contains(lot.geom, h.geom)
    GROUP BY
        lot.LOTID;
    """
    queries.append(query3)
    # Query 4: Create lots_with_avg_price table
    query4 = f"""
    CREATE OR REPLACE TABLE lots_with_avg_price AS 
    SELECT
        lot.*,
        COALESCE(avg_price.avg_unit_price, 0) AS avg_unit_price,
        COALESCE(avg_price.avg_change,0) as avg_change_percent
    FROM
        {sanitized_name}_lot AS lot
    LEFT JOIN
        average_price_per_lot AS avg_price
    ON
        lot.LOTID = avg_price.LOTID;
    """
    queries.append(query4)
    return queries

@st.cache_data
def execute_duckdb_queries(queries, db_path='hong_kong_data.duckdb'):
    """
    Execute a list of DuckDB SQL queries.

    Parameters:
    - queries (list of str): List of SQL queries to execute.
    - db_path (str): Path to the DuckDB database file. Defaults to in-memory.

    Returns:
    - None
    """
    if not queries:
        st.warning("⚠️ No data in the selected area.")
        return
    con = duckdb.connect(database=db_path, read_only=False)
    # Load spatial extension
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    for idx, query in enumerate(queries, start=1):
        try:
            con.execute(query)
            #st.write(f"✅ Query {idx} executed successfully.")
        except Exception as e:
            st.error(f"❌ Error executing Query {idx}: {e}")
            con.close()
            raise e
    con.close()

@st.cache_data
def execute_duckdb_select_query(sanitized_name, db_path='hong_kong_data.duckdb'):
    """
    Execute a DuckDB SELECT query to retrieve the final results.

    Parameters:
    - sanitized_name (str): Sanitized district name.
    - db_path (str): Path to the DuckDB database file. Defaults to in-memory.
    - limit (int): Number of records to retrieve.

    Returns:
    - pandas.DataFrame: Resulting DataFrame from the SELECT query.
    """
    
    con = duckdb.connect(database=db_path, read_only=False)
    con.execute("LOAD spatial;")
    try:
        query = f"""
        SELECT LOTID,avg_unit_price,avg_change_percent,ST_ASTEXT(geom) as wkt_geom
        FROM lots_with_avg_price
        ORDER BY avg_unit_price DESC
        ;
        """
        result = con.execute(query).df()  
        #Need a gdf as well for pydeck geojson layer? 
        result['geometry'] = result['wkt_geom'].apply(wkt.loads)
        gdf= gpd.GeoDataFrame(result, geometry='geometry')
        con.close()
        return result
    except Exception as e:
        con.close()
        st.error(f"❌ Error executing SELECT query: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error
    
@st.cache_data
def gdf_create(result_df):
     #Create a geopandas dataframe
     gdf = gpd.GeoDataFrame(result_df, geometry='geometry')
     return gdf 
    
def main():
    st.set_page_config(layout="wide")
    st.title("Hong Kong Housing Price Visualizer")
    st.write("Overview: I built an interactive Hong Kong housing price visualizer using Streamlit, DuckDB, and PyDeck, where we transformed the housing data through clipping, aggregation, and geometry simplification, efficiently handling large datasets in parquet format to showcase housing price trends from 2020 to 2023 across different districts categorized by lot")
    st.write("Select a scale and district to view corresponding data.")

    # Define your scale options
    scale_options = ["Lot"]

    # Step 1: User selects the scale
    scale = st.selectbox("Select Scale", options=scale_options)

    # Step 2: Conditionally show the district dropdown if "Lot" is selected
    selected_district = None
    if scale == "Lot":
        # List of 18 Hong Kong districts
        districts = [
            "Central and Western",
            "Eastern",
            "Southern",
            "Wan Chai",
            "Kowloon City",
            "Kwun Tong",
            "Sham Shui Po",
            "Wong Tai Sin",
            "Yau Tsim Mong",
            "Islands",
            "Kwai Tsing",
            "North",
            "Sai Kung",
            "Sha Tin",
            "Tai Po",
            "Tsuen Wan",
            "Tuen Mun",
            "Yuen Long"
        ]
        selected_district = st.selectbox("Select a District (Lot geometry is simplified in some districts due to size limit)", options=districts)

    # Step 3: Display the selected values and execute queries
    if selected_district:
        # Define paths
        output_directory = 'data'  # Replace with your actual output directory path
        sanitized_name = sanitize_filename(selected_district)
        
        # Define lot and housing GeoJSON paths
        district_lot_geojson_path = os.path.join(output_directory, f"{sanitized_name}_lot.parquet")
        district_housing_geojson_path = os.path.join(output_directory, f"{sanitized_name}_hk2020.geojson")
        
        # Display selection
        st.write(f"You selected: **Average Price by {selected_district} ({scale})**")
        st.write("### Hold On! Extracting Data For You...")
        
        # Build DuckDB queries
        try:
            queries = build_duckdb_queries(sanitized_name, district_lot_geojson_path, district_housing_geojson_path)
        except Exception as e:
            st.error(f"❌ Error building DuckDB queries: {e}")
            st.stop()
        # Check if queries is empty
        if not queries:
            st.warning("⚠️ Sorry,no data in the selected area within this dataset.")
            st.stop()
        
        # Execute the queries
        try:
            execute_duckdb_queries(queries)
            st.success("All queries executed successfully.")
        except Exception as e:
            st.error(f"❌ DuckDB queries failed: {e}")
            st.stop()
        
        # Execute SELECT query to retrieve results
        # st.write("### Retrieving Results...")
        try:
            result_df = execute_duckdb_select_query(sanitized_name)
            if not result_df.empty:
                  # Map is 4 times larger than DataFrame

               
                with st.expander("Expand to see the data"):
                      st.write(f"#### {len(result_df)} Records Extracted")
                      st.dataframe(result_df.drop(columns=['wkt_geom']))

                
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                      #Make sure there is only one geom column
                      gdf=gdf_create(result_df)

                      view_state = pdk.ViewState(
                        longitude=114.1694 ,
                        latitude=22.3193,
                        zoom=10,
                        min_zoom=5,
                        max_zoom=15,
                        pitch=40.5,
                        bearing=-27.36,
                    )
                      layer = pdk.Layer(
                        'GeoJsonLayer',
                        gdf,
                        opacity=0.8,
                        stroked=False,
                        filled=True,
                        extruded=True,
                        wireframe=True,
                        get_elevation='avg_unit_price/100',
                        get_fill_color='[255,255,255-avg_change_percent]',
                        get_line_color=[255, 255, 255],
                        pickable=True
                        
                    )  
                      # Define the tooltip
                      tooltip = {
                            "html": "<b>LOTID:</b> {LOTID} <br/> <b>Average Unit Price:</b> {avg_unit_price}",
                            "style": {"backgroundColor": "steelblue", "color": "white"},
                        }

                      r = pdk.Deck(layers=[layer], initial_view_state=view_state,tooltip=tooltip)
                      st.pydeck_chart(r)
                    with col2:
                        st.markdown("HongKong Housing Price Visualizer")
                        st.write("""
                            **Average Price Change From Last Transaction:**

                            <div style="width: 100px; height: 300px; background: linear-gradient(to top, #ffff00, #ffeb3b, #fdd835, #ffc107, #ff9800); border: 1px solid #ccc;"></div>
                            <div style="margin-top: 10px;">
                                <span>Brighter Yellow = Higher Average Change Percent</span>
                                 <br>
                                <span>Hover to see more information on each lot</span>
                            </div>
                        """, unsafe_allow_html=True)      
                        
                
            else:
                st.write(f"{sanitized_name}")
                st.warning("No data available to display.")
        except Exception as e:
            st.error(f"❌ Error retrieving results: {e}")
    else:
        st.write(f"You selected: **Average Price by {scale}**")
    st.write("Data Source: [Hong Kong Housing Price (2020-2023)](https://www.kaggle.com/datasets/cyrusttf/hong-kong-housing-price-2020-2023/data)")


if __name__ == "__main__":
    main()


