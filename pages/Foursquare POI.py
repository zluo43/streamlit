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
    con=duckdb.connect(database='data/coffee.duckdb')
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    return con


def main():
    # Streamlit page configuration

    #Duckdb conneect
    con=connect_to_duckdb()
    con.sql("""SHOW TABLES""")
    #df=con.sql("""SELECT name,latitude,longitude FROM fsq_coffee """).df()

    st.set_page_config(layout="wide")
    st.title("Explore Coffee Shops in Hong Kong Using Foursquare POI Dataset")
    st.write("""
             Overview:
            

             """)

    
    

    layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
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
    view_state = pdk.ViewState(
                latitude=22.3193,     # Approximate latitude for Hong Kong
                longitude=114.1694,   # Approximate longitude for Hong Kong
                zoom=10,              # Adjust zoom level as needed
                bearing=0,
                pitch=0
            )
    tooltip = {
                "html": "<b>Name:</b>{name}",
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



if __name__ == "__main__":
    main()
