import streamlit as st
import os
import duckdb
import pydeck as pdk
import geopandas as gpd
import pandas as pd


def main():
    st.set_page_config(layout="wide")
    st.title("Visualize Population Distribution of HongKong By H3 Grid")
    st.write('Overview:')
    st.write("""
             Demographic data usually comes in irregular shape (Census block, group, etc). Hong Kong population distribution datasets available on ESRI HongKong
             are categorized by local planning units. To come up with a uniformly shaped population data across any location, similar to what Kontur offers,
             I intersected planning units with H3 cells, calculated the percent of overlapping area, multiplied population proportionally as a simplification,
             and then sum everything up based on H3 hexagon cells. Please refer to the code in my repo!
             """)
    



    with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                      
                      df_h3=pd.read_csv('data/hk_pop_dist.csv')

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
                        "H3HexagonLayer",
                        df_h3,
                        pickable=True,
                        stroked=True,
                        filled=True,
                        extruded=False,
                        get_hexagon="hex_id",
                        get_fill_color="[0, 255 - (total_population/100000 * 255), 255]",
                        get_line_color=[255, 255, 255],
                        line_width_min_pixels=2,
                    )

                        
                     
                      # Define the tooltip
                      tooltip = {
                            "html": "<b>LOTID:</b> {hex_id} <br/> <b>Total Population:</b> {total_population}",
                            "style": {"backgroundColor": "steelblue", "color": "white"},
                        }

                      r = pdk.Deck(layers=[layer], initial_view_state=view_state,tooltip=tooltip)
                      st.pydeck_chart(r)
                      st.markdown(
                              """<a href="https://www.kontur.io/portfolio/population-dataset/" target="_blank"><em>🔗 Reference to Kontur Global Population Data</em></a>""",
                              unsafe_allow_html=True
                          )
                    with col2:
                        st.markdown("Hong Kong Population Distribution")
                        st.write("""
                            

                            <div style="width: 100px; height: 300px; background: linear-gradient(to top, #E3F2FD,#64B5F6,#2196F3,#1976D2,#0D47A1); border: 1px solid #ccc;"></div>
                            <div style="margin-top: 10px;">
                                <span>Brighter Blue = Less population</span>
                                 <br>
                                 <br>
                                <span>Hover to see more information on each Hexagon</span>
                            </div>
                        """, unsafe_allow_html=True)
if __name__ == "__main__":
    main()
