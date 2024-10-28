import streamlit as st
import os
import duckdb
import pydeck as pdk
import geopandas as gpd

def geojson_to_gdf(geojson_path):
    """
    Convert a GeoJSON file to a GeoDataFrame.
    Parameters:
    - geojson_path (str): Path to the GeoJSON file.
    Returns:
    - GeoDataFrame: Loaded GeoDataFrame.
    """
    gdf = gpd.read_file(geojson_path)
    return gdf

def connect_to_duckdb(db_path ='hk_711.duckdb'):
    """
    Connect to the DuckDB database and load the spatial extension.
    Parameters:
    - db_path (str): Path to the DuckDB database.
    Returns:
    - DuckDB connection object.
    """
    con = duckdb.connect(database=db_path, read_only=False)
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    return con

def main():
    # Streamlit page configuration
    st.set_page_config(layout="wide")
    st.title("Visualize Locations of Convenience Stores in HongKong")
    st.write("""
             Overview:
             This application visualizes the locations of convenience stores in Hong Kong. Currently, it only supports **7-Eleven**.
             The addresses are obtained via scrapped the official 7-11 Hongkong website and converted to coordinates via Nominatim geocoding service API.
             There are roughly 1100 Seven-Eleven in Hongkong but my code only catches 657 valid coordinates.
             Isochrones are generated via Vahalla to provide a very general idea of how close each 711 store is in Hongkong.
             Please refer to the repository for specific code.
             More analysis is coming!
             """)

    # Step 1: Dropdown menu for selecting store names
    store_names = ["7-Eleven", "Circle K", "Family Mart"]
    selected_store = st.selectbox("Select Store", options=store_names)

    # Path to the DuckDB file
    
    
    # Connect to DuckDB
    con = connect_to_duckdb()

    # Step 2: Check if a store is selected
    if selected_store:
        # Display selected store name
        st.write(f"You selected: **{selected_store}**")
        st.write("### Hold On! Extracting Data For You...")

        if selected_store == "7-Eleven":
            # Query the DuckDB database for 7-Eleven data
            query = """SELECT * FROM hk_711"""
            df_point_data = con.sql(query).df()  # Load data into a DataFrame

            # Clean up DataFrame (you can customize this based on actual columns)
            df_cleaned = df_point_data[['latitude', 'longitude', 'Address']]  # Adjust based on your actual column names

            # Define the PyDeck layer for store locations (Scatterplot for points)
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_cleaned,
                get_position=["longitude", "latitude"],
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

            # 4. Set the viewport to focus on Hong Kong
            view_state = pdk.ViewState(
                latitude=22.3193,     # Approximate latitude for Hong Kong
                longitude=114.1694,   # Approximate longitude for Hong Kong
                zoom=10,              # Adjust zoom level as needed
                bearing=0,
                pitch=0
            )

            # 5. Define the tooltip to display the Address
            tooltip = {
                "html": "<b>Address:</b> {Address}",
                "style": {
                    "backgroundColor": "steelblue",
                    "color": "white"
                }
            }

            # Step 3: Checkbox for displaying isochrones
            show_isochrones = st.checkbox("Show Isochrones")

            layers = [layer]  # Initialize with the store layer

            if show_isochrones:
                # Dynamically construct the isochrones GeoJSON path based on the selected store name
                store_filename = selected_store.replace(' ', '_')  # Replace spaces with underscores
                isochrones_geojson_path = f"data/isochrones_{store_filename}_hongkong.geojson"

                # Load isochrones data if the checkbox is checked
                if os.path.exists(isochrones_geojson_path):
                    gdf_isochrones = geojson_to_gdf(isochrones_geojson_path)

                    # Define the PyDeck layer for isochrones
                    isochrones_layer = pdk.Layer(
                        "GeoJsonLayer",
                        gdf_isochrones,
                        opacity=0.8,
                        stroked=True,
                        filled=True,
                        extruded=False,  # No elevation
                        wireframe=True,  # Keep wireframe to show polygon borders
                        get_fill_color="[255, 255, 0, 100]",  # Yellow fill color with transparency
                        get_line_color=[255, 255, 255],  # White polygon borders
                        line_width_min_pixels=1  # Minimize polygon border width
                    )

                    # Add the isochrones layer to the PyDeck layers
                    layers.append(isochrones_layer)
                else:
                    st.error(f"❌ Isochrones data not found at {isochrones_geojson_path}")

            # 6. Create the Deck and render it to the Streamlit page
            r = pdk.Deck(
                layers=layers,
                initial_view_state=view_state,
                tooltip=tooltip
            )

            st.pydeck_chart(r)

        else:
            st.write(f"Sorry, data for {selected_store} is not available yet.")

if __name__ == "__main__":
    main()


