import streamlit as st
import os
import duckdb
import pandas as pd
import pydeck as pdk
import geopandas as gpd
import requests
import json 
import math 
import osmnx as ox 
import time


def connect_to_duckdb():
    """
    Connect to the DuckDB database and load the spatial extension.
    Parameters:
    - db_path (str): Path to the DuckDB database.
    Returns:
    - DuckDB connection object.
    """
    con=duckdb.connect(database = ":memory")
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    con.execute('INSTALL h3 FROM community;')
    con.execute('Load h3')
    return con


def get_street_network(lat, lon, radius=1000, network_type="walk"):
    """
    Retrieve a street network from OSMnx, given a point and a radius (in meters),
    plus a network type ("walk", "drive", etc.).
    """
    G = ox.graph_from_point((lat, lon), dist=radius, network_type=network_type)
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(G)
    return nodes_gdf, edges_gdf
def create_street_layers(nodes_gdf, edges_gdf):
    # Edges as a GeoJsonLayer or PathLayer
    edges_layer = pdk.Layer(
        "GeoJsonLayer",
        data=edges_gdf,   
        pickable=False,
        stroked=True,
        filled=False,
        lineWidthScale=2,
        lineWidthMinPixels=2,
        get_line_color=[0, 0, 255],
        get_line_width=2
    )
    # Nodes as a ScatterplotLayer
    nodes_layer = pdk.Layer(
        "ScatterplotLayer",
        data=nodes_gdf,
        pickable=False,
        get_position=["x", "y"],
        get_radius=10,
        get_fill_color=[255, 255, 0],
    )
    return [edges_layer, nodes_layer]
def main():
    # Streamlit page configuration
    st.set_page_config(layout="wide")

    # DuckDB connect
    con = connect_to_duckdb()
    df = con.sql("""
    SELECT 
    id,
    listing_url,
    name,
    host_is_superhost,
    neighbourhood_cleansed,
    latitude,
    longitude,
    review_scores_cleanliness,
    review_scores_checkin,
    review_scores_communication,
    review_scores_location,
    review_scores_value
    FROM read_csv('data/hk_listing.csv')
    """
    ).df()

    con.sql(
    """
            CREATE OR REPLACE TABLE airbnb AS
            WITH CTE AS (
            SELECT latitude,longitude,
            h3_latlng_to_cell_string (latitude,longitude,9) as h3_string,
            FROM read_csv_auto('data/hk_listing.csv')
            )
            SELECT h3_string,
            COUNT(*) as count
            FROM CTE
            GROUP BY h3_string
    """
            )

    #print (con.sql("""SHOW TABLES"""))

    h3_df=con.sql("""SELECT * FROM airbnb""").df()
    print (h3_df.head())

    # Initialize session state for events
   
    
    st.title("Explore Street Density Around your Airbnb Units")
    st.write(
        """
        Overview:
        In this section, I use OpenStreetMap's OSMnx to calculate the street density around any Airbnb locations listed (Source: Inside Airbnb).
        Users can select a point location, define a radius, and then select whether you want to see a "walk density" or "drive density".
        Give it a try!

        """
    )
    network_type = st.selectbox("Choose Network Type", ["walk", "drive"])
    user_radius = st.number_input("Radius in meters", value=1000, min_value=100, max_value=10000, step=100)

    # Define our Scatterplot layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        id="Airbnb",
        get_position=["longitude", "latitude"],
        get_fill_color=[0, 140, 255, 160],
        get_line_color=[0, 0, 0, 255],
        pickable=True,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=3,
        radius_max_pixels=10,
        line_width_min_pixels=1
    )

    # Pydeck tooltip
    tooltip = {
        "html": "<b>Name:</b> {name}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    view_state = pdk.ViewState(
                latitude=22.3193,     # Approximate latitude for Hong Kong
                longitude=114.1694,   # Approximate longitude for Hong Kong
                zoom=10,              # Adjust zoom level as needed
                bearing=0,
                pitch=0
            )
    r = pdk.Deck(
        layers=layer,
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/streets-v11",
    )
    event=st.pydeck_chart(r,on_select='rerun',selection_mode="single-object")
    

    if (
        event.selection is not None
        and hasattr(event.selection, "objects")
        and "Airbnb" in event.selection.objects
    ): 
        
        selected_obj = event.selection.objects["Airbnb"][0]  # single-object mode => first item
        sel_lat = selected_obj["latitude"]
        sel_lon = selected_obj["longitude"]
        apt_name = selected_obj["name"]
        cleanliness=selected_obj['review_scores_cleanliness'],
        checkin=selected_obj["review_scores_checkin"],
        communication=selected_obj['review_scores_communication'],
        location=selected_obj['review_scores_location'],
        value=selected_obj['review_scores_value']
        dist=selected_obj['neighbourhood_cleansed']
        
        st.session_state["selected_airbnb"] = {
            "name": apt_name, 
            "lat": sel_lat, 
            "lon": sel_lon,
            "review_scores_cleanliness": cleanliness,
            "review_scores_checkin": checkin,
            "review_scores_communication": communication,
            "review_scores_location": location,
            "review_scores_value": value,
            "district": dist
        }
    if "selected_airbnb" in st.session_state:
        selected_airbnb = st.session_state["selected_airbnb"]
        
        st.write(f"**Selected Airbnb (Names might not be accurate as source is scraped)**: {selected_airbnb['name']}")
        st.write(f"**Coordinates**: Latitude={selected_airbnb['lat']}, Longitude={selected_airbnb['lon']}")
        st.write(f"**District**: {selected_airbnb['district']}")

        nodes_gdf, edges_gdf = get_street_network(
                selected_airbnb["lat"], selected_airbnb["lon"],
                radius=user_radius,        # Use user-defined radius
                network_type=network_type  # Use user-defined network type
        )
        # Calculate street density as an example
        total_length_km = edges_gdf["length"].sum() / 1000.0
        area_km2 = math.pi * (1**2)  # 1 km radius => pi*(1km^2)
        density = total_length_km / area_km2
        with st.spinner('Calculating Street Density and Preparing New Maps...'):
            time.sleep(2)
            st.write(f"**Pedastrian Street Density**: {density:.2f} km/km² within 1km radius")
        street_layers = create_street_layers(nodes_gdf, edges_gdf)
        second_layers=[
                pdk.Layer(
                "GeoJsonLayer",
                data=edges_gdf,       # This is a GeoDataFrame with line geometries
                stroked=True,
                filled=False,         # We don't fill lines
                lineWidthScale=1,
                lineWidthMinPixels=1,
                get_line_color=[0, 0, 255],
                get_line_width=2,
                
            ),
            pdk.Layer(
                "ScatterplotLayer",
                nodes_gdf,
                pickable=True,
                opacity=1,
                stroked=True,
                filled=True,
                radius_scale=3,
                radius_min_pixels=1,
                radius_max_pixels=100,
                line_width_min_pixels=1,
                get_position=["x", "y"],
                get_fill_color=[255, 140, 0],
                get_line_color=[0, 0, 0],
            )


        ]
        second_view_state = pdk.ViewState(
            latitude=selected_airbnb["lat"],
            longitude=selected_airbnb["lon"],
            zoom=14
        )
        deck2 = pdk.Deck(
            layers=second_layers,
            initial_view_state=second_view_state
            
        )
        deck3 = pdk.Deck(
        layers= pdk.Layer(
                "H3HexagonLayer",
                h3_df,
                pickable=True,
                stroked=True,
                filled=True,
                extruded=False,
                get_hexagon="h3_string",
                get_fill_color="[255 - count, 255, count]",
                get_line_color=[255, 255, 255],
                line_width_min_pixels=2
                )

        ,  
        initial_view_state=pdk.ViewState(
            latitude=22.3193,     # Approximate latitude for Hong Kong
            longitude=114.1694,   # Approximate longitude for Hong Kong
            zoom=10
            
    )
    
    )

        # Split into two columns
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Pedastrian Street Network for Selected Airbnb")
            st.pydeck_chart(deck2)

        with col2:
            st.subheader("Full-City H3 Grid View of Airbnb Density")
            st.pydeck_chart(deck3)
                
                
           



if __name__ == "__main__":
    main()