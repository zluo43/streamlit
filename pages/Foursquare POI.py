import streamlit as st
import os
import duckdb
import pandas as pd
import pydeck as pdk
import geopandas as gpd
import requests
import json 


def connect_to_duckdb(db_path ='data/coffee.db'):
    """
    Connect to the DuckDB database and load the spatial extension.
    Parameters:
    - db_path (str): Path to the DuckDB database.
    Returns:
    - DuckDB connection object.
    """
    con=duckdb.connect(database=db_path,read_only=False)
    con.execute("INSTALL spatial;")
    con.execute("LOAD spatial;")
    return con

# def load_map(session_state):


def main():
    # Streamlit page configuration
    st.set_page_config(layout="wide")

    # DuckDB connect
    con = connect_to_duckdb()
    df = con.sql("SELECT name, longitude, latitude, website, tel FROM fsq_coffee").df()
    
    st.title("Explore Coffee Shops in Hong Kong Using Foursquare POI Dataset")
    st.write(
        """
        Overview:
        
        A very simple visualization of coffee shops in Hong Kong using 
        Foursquare's latest open POI data.
        
        I attempt to implement an on-click event handling for zooming 
        and returning specific information on the point. Pydeck in 
        Streamlit doesn't support this feature natively. Right now I 
        have implemented a very simple workaround, but I will continue 
        to explore if I can build a custom component for this simple feature.
        """
    )
    st.markdown(
        "<span style='color: #0066cc; font-weight: bold;'>Click on a point to see details about the coffee shop.</span>", 
        unsafe_allow_html=True
    )

    # Initialize session state for events
    if "current_event_num" not in st.session_state:
        st.session_state["current_event_num"] = 1

    # Dictionary to hold all pydeck chart objects by key: "event1", "event2", ...
    if "events" not in st.session_state:
        st.session_state["events"] = {}
    
    #Initialize selected shop 
    if "selected_shop" not in st.session_state:
        st.session_state["selected_shop"] = None
    # Create containers
    map_container = st.empty()
    info_container = st.empty()

    # Define our Scatterplot layer
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        id="Coffee Shop",
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

        # Function to create a deck at given lat/lon/zoom
    def create_deck(latitude, longitude, zoom=10):
        view_state = pdk.ViewState(
            latitude=latitude,
            longitude=longitude,
            zoom=zoom,
            bearing=0,
            pitch=0
        )
        return pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip
        )

    # Figure out which event key we are dealing with
    current_event_key = f"event{st.session_state['current_event_num']}"

    # If we haven't created this "event" deck yet, do so
    if current_event_key not in st.session_state["events"]:
        # For the first event, default citywide view
        if st.session_state["current_event_num"] == 1:
            st.session_state["events"][current_event_key] = create_deck(
                latitude=22.3193,
                longitude=114.1694,
                zoom=10
            )
        else:
            # Fallback or placeholder if an event somehow got created
            # without a specific lat/lon. (Right now it uses the same city view.)
            st.session_state["events"][current_event_key] = create_deck(
                latitude=22.3193,
                longitude=114.1694,
                zoom=10
            )

    # Display the current deck
    current_deck = map_container.pydeck_chart(
        st.session_state["events"][current_event_key],
        on_select="rerun",
        selection_mode="single-object"
    )

    # Check if we have a previously selected shop stored
    if st.session_state["selected_shop"] is not None:
        obj = st.session_state["selected_shop"]
        # Display details about this previously selected coffee shop
        info_html = f"""
        <span style='color: #0066cc; font-weight: bold;'>Selected coffee shop: {obj['name']}</span><br>
        """
        if obj["website"]:
            info_html += f"<span style='color: #0066cc; font-weight: bold;'>Website: {obj['website']}</span><br>"
        else:
            info_html += "<span style='color: #0066cc; font-weight: bold;'>Website Info Not Provided!</span><br>"

        if obj["tel"]:
            info_html += f"<span style='color: #0066cc; font-weight: bold;'>Telephone Number: {obj['tel']}</span><br>"
        else:
            info_html += "<span style='color: #0066cc; font-weight: bold;'>Phone Number Not Available!</span><br>"

        info_container.markdown(info_html, unsafe_allow_html=True)

    # Check the current selection from the deck
    selection = current_deck.selection
    # Uncomment this if you want to see the raw selection in the UI:
    # st.write("Raw selection state:", selection)

    # If the user just clicked on a new coffee shop
    if (
        selection is not None
        and hasattr(selection, "objects")
        and "Coffee Shop" in selection.objects
    ):
        # The first object in the "Coffee Shop" list
        obj = selection.objects["Coffee Shop"][0]

        # Store the details in session_state so we remember it after rerun
        st.session_state["selected_shop"] = obj

        # Create and store a new event (zoomed-in view) for the next run
        st.session_state["current_event_num"] += 1
        new_event_key = f"event{st.session_state['current_event_num']}"

        st.session_state["events"][new_event_key] = create_deck(
            latitude=obj["latitude"],
            longitude=obj["longitude"],
            zoom=18
        )

        # Force a rerun to pick up the new event deck
        st.rerun()

    # Reset button
    if st.button("Reset View"):
        # Clear out everything: events, selected shop, event number
        st.session_state["events"] = {}
        st.session_state["selected_shop"] = None
        st.session_state["current_event_num"] = 1
        st.rerun()


if __name__ == "__main__":
    main()