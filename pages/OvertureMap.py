import streamlit as st
import os
import duckdb
import pandas as pd
import pydeck as pdk
import geopandas as gpd
import requests
import json 
def connect_to_duckdb():
    """
    Connect to the DuckDB database and load the spatial extension.
    Parameters:
    - db_path (str): Path to the DuckDB database.
    Returns:
    - DuckDB connection object.
    """
    con=duckdb.connect(database=':memory:')
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    return con
def get_country_bounding_box(country):
    try:
        # Set up the request headers including a User-Agent
        headers = {
            'User-Agent': 'zluo43@wisc.edu'
        }
        
        # Make the request to Nominatim API with the country name
        r = requests.get(f"http://nominatim.openstreetmap.org/search?q={country}&format=json", headers=headers)

        # Check if the response status code is 200 (OK)
        if r.status_code == 200:
            # Parse the response and get the bounding box
            data = json.loads(r.text)

            # Ensure there is at least one result
            if len(data) > 0:
                bounding_box = data[0]["boundingbox"]
                # Convert bounding box values from string to float for easy manipulation
                bounding_box = [float(coord) for coord in bounding_box]
                return bounding_box
            else:
                print(f"No results found for {country}")
                return None
        else:
            print(f"Failed to retrieve data: {r.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def main():
    # Streamlit page configuration

    #Duckdb conneect
    con=connect_to_duckdb()

    st.set_page_config(layout="wide")
    st.title("Search Places in Hong Kong")
    st.write("""
             Overview:
             This web map allows you to search for different types of places in Hong Kong using Overture Places data.
             The underlyding bounding box used in the SQL query is obtained from Nominatim API.

             """)

    # Read the categories CSV file
    try:
        
        df_categories = pd.read_csv('data/categories.csv', sep=";", engine='python')
        
        # Only need this column
        df_categories = df_categories[['Category code']]

        # Create an expander to show the categories
        with st.expander("📋Please View Available Categories For Specific Wording Requirements"):
            st.markdown("<p style='color:red;'>Browse through the categories below and copy the desired category value from Overture Maps:</p>", unsafe_allow_html=True)
            st.dataframe(
                df_categories,
                use_container_width=True,
                height=300,
                hide_index=True
            )

        # Create a text input for category search
        user_category = st.text_input(
            "Enter a place category:",
            placeholder="Copy a category from the above",
            help="Copy a category from the list above or type your own keyword"
        )
        
        country = st.text_input(
            "Enter a country you want to search in:",
            placeholder='Hong Kong'
        )

        # If user enters a category, validate it against the categories file
        valid_category = False
        if user_category:
            # Convert input to lowercase for case-insensitive matching
            user_category_lower = user_category.lower()
            
            # Check if the category exists in the CSV
            matching_categories = df_categories[
                df_categories['Category code'].str.lower().str.contains(user_category_lower, na=False)
            ]

            if not matching_categories.empty:
                st.success(f"✅ Found matching categories for '{user_category}'")
                st.write("Matching categories found:")
                # st.dataframe(
                #     matching_categories,
                #     use_container_width=True
                # )
                valid_category = True
            else:
                st.warning(f"⚠️ No exact matches found for '{user_category}'. Please check the category list above for valid options.")

        # Validate the country and check if it has a valid bounding box
        valid_bounding_box = False
        if country:
            bounding_box = get_country_bounding_box(country)
            
            
            if bounding_box and len(bounding_box) == 4:
                min_y, max_y, min_x, max_x = bounding_box
                valid_bounding_box = True
            else:
                st.warning(f"⚠️ No exact matches found for '{country}'. Please check the country name.")

        # If both category and country (with valid bounding box) are valid, generate the query
        if valid_category and valid_bounding_box:
            query = f""" 
            SELECT names,ST_X(geometry) as lon, ST_Y(geometry) as lat
            FROM read_parquet('s3://overturemaps-us-west-2/release/2024-09-18.0/theme=places/*/*')
            WHERE
            bbox.xmin >= {min_x} AND bbox.xmax <={max_x}
            AND bbox.ymin >= {min_y} AND bbox.ymax <={max_y}
            AND (categories.primary='{user_category}')
            """
            st.info(f"🔍 Generating the map for you!")
            df_overture=con.sql(query).df()
            df_overture['name_value'] = df_overture['names'].apply(lambda x: x['primary'])
            #st.dataframe(df_overture)

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_overture,
                get_position=["lon", "lat"],
                get_fill_color=[0, 140, 255, 160],  # Blue color with transparency
                get_line_color=[0, 0, 0, 255],      # Black border
                pickable=True,
                stroked=True,
                filled=True,
                radius_scale=1,                     # Fixed radius scale
                radius_min_pixels=3,                # Minimum radius size
                radius_max_pixels=10,               # Maximum radius size
                line_width_min_pixels=1             # Border width
            )
            view_state = pdk.ViewState(
                latitude=22.3193,     # Approximate latitude for Hong Kong
                longitude=114.1694,   # Approximate longitude for Hong Kong
                zoom=10,              # Adjust zoom level as needed
                bearing=0,
                pitch=0
            )
            tooltip = {
                "html": "<b>Name:</b>{name_value}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white"
                }
            }
            r = pdk.Deck(
                layers=layer,
                initial_view_state=view_state,
                tooltip=tooltip
            )

            st.pydeck_chart(r)

    except FileNotFoundError:
        st.error("❌ Categories file not found. Please ensure 'categories.csv' is in the correct location.")
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
