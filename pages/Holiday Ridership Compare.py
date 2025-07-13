import streamlit as st
import duckdb
import datetime
import pandas as pd
import plotly.express as px
import geopandas as gpd
import pydeck as pdk

def set_page_theme():
    """
    Injects CSS to style the page theme and widgets correctly.
    """
    css = """
    <style>
        /* General page and text styling */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #000000;
        }
        body, p, h1, h2, h3, h4, h5, h6, label {
            color: #FFFFFF !important;
            text-align: center;
        }
        [data-testid="stForm"] {
            background-color: #000000;
            border: 1px solid #444;
            border-radius: 10px;
        }

        /* Styles the visible selectbox */
        div[data-baseweb="select"] > div {
            background-color: #262730 !important;
            border-radius: 5px;
        }
        
        /* Ensures the text inside the visible box is white */
        div[data-baseweb="select"] > div > div {
             color: white !important;
        }

        /* Styles the dropdown menu that appears on click */
        div[data-baseweb="popover"] ul {
            background-color: #262730;
        }
        
        /* Sets the font color for the options in the dropdown menu */
        div[data-baseweb="popover"] ul li {
            color: white !important;
        }

        /* Styles the options on hover */
        div[data-baseweb="popover"] ul li:hover {
            background-color: #555555;
        }

        /* Styles the "Analyze" button */
        [data-testid="stFormSubmitButton"] button {
            background-color: #000000;
            color: white;
            border: 1px solid #555;
        }

        /* Styles the min/max value labels on the slider */
        [data-testid="stSlider-mark-value"] {
            color: white !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_resource(ttl=datetime.timedelta(hours=1))
def get_db_connection():
    """
    Establishes and caches a DuckDB in-memory connection that has the spatial extension loaded.
    """
    try:
        con = duckdb.connect(database=':memory:', read_only=False)
        con.execute("INSTALL spatial; LOAD spatial;")
        return con
    except Exception as e:
        st.error(f"Error connecting to DuckDB and loading spatial extension: {e}")
        return None

def materialize_unique_stations_table(_con, year):
    """
    Creates the 'unique_stations' table for a specific year.
    """
    s3_path = 's3://us-west-2.opendata.source.coop/zluo43/citibike/new_schema_combined_with_geom.parquet/**/*.parquet'
    
    query = f"""
    CREATE OR REPLACE TABLE unique_stations AS
    SELECT
        start_station_name,
        AVG(start_lat) as lat,
        AVG(start_lng) as lon
    FROM read_parquet('{s3_path}', hive_partitioning=1)
    WHERE start_station_name IS NOT NULL AND year = {year}
    GROUP BY start_station_name;
    """
    _con.execute(query)

def materialize_station_neighborhood_join(_con, geojson_path):
    """
    Spatially joins the unique_stations table with neighborhood polygons
    and creates a new table 'stations_with_neighborhoods'.
    """
    query = f"""
    CREATE OR REPLACE TABLE stations_with_neighborhoods AS
    SELECT
        s.start_station_name,
        n.ntaname AS neighborhood
    FROM unique_stations s
    LEFT JOIN ST_Read('{geojson_path}') n
    ON ST_Within(ST_Point(s.lon, s.lat), n.geom);
    """
    _con.execute(query)

def get_holiday_comparison_data(con, holiday_date):
    """
    Queries the S3 dataset to get aggregated hourly trip counts by neighborhood for the holiday
    vs. a baseline of similar weekdays in the same month.
    """
    if con is None: return None

    year = holiday_date.year
    month = holiday_date.month
    day_of_week_iso = holiday_date.isoweekday()
    holiday_date_str = holiday_date.strftime('%Y-%m-%d')
    
    s3_path = 's3://us-west-2.opendata.source.coop/zluo43/citibike/new_schema_combined_with_geom.parquet/**/*.parquet'

    query = f"""
    WITH categorized_trips AS (
        SELECT
            strftime(trips.started_at, '%H') AS hour_of_day,
            date_trunc('day', trips.started_at) AS trip_date,
            map.neighborhood,
            CASE
                WHEN date_trunc('day', trips.started_at) = '{holiday_date_str}' THEN 'Holiday'
                ELSE 'Baseline'
            END AS category
        FROM read_parquet('{s3_path}', hive_partitioning=1) AS trips
        JOIN stations_with_neighborhoods AS map
        ON trips.start_station_name = map.start_station_name
        WHERE
            trips.year = {year} AND
            trips.month = {month} AND
            isodow(trips.started_at) = {day_of_week_iso}
    )
    SELECT
        hour_of_day,
        category,
        neighborhood,
        COUNT(*) / COUNT(DISTINCT trip_date) AS trips
    FROM categorized_trips
    GROUP BY hour_of_day, category, neighborhood
    ORDER BY hour_of_day, category;
    """

    try:
        with st.spinner("Querying data and performing aggregations..."):
            result_df = con.execute(query).df()
        return result_df
    except Exception as e:
        st.error(f"Error during data query: {e}")
        return None

def display_nyc_map(geojson_path, neighborhood_df, hour):
    """
    Displays neighborhood ridership data on a PyDeck map for a specific hour.
    """
    try:
        gdf = gpd.read_file(geojson_path)
    except Exception as e:
        st.error(f"Could not read the GeoJSON file at '{geojson_path}'. Error: {e}")
        return
        
    # Filter the neighborhood_df for the selected hour
    hourly_data = neighborhood_df[neighborhood_df['hour_of_day'] == str(hour).zfill(2)].copy()
    
    #Turn neighborhood "Upper East Side" into index

    #Row example:  Upper East Side 110 xx
    #Row example:  Upper East Side 150 xx
    #Row example:  Upper East Side 40  xx

    pivot_df = hourly_data.pivot(index='neighborhood', columns='category', values='trips').fillna(0)


    pivot_df['difference'] = pivot_df.get('Holiday', 0) - pivot_df.get('Baseline', 0)

    gdf = gdf.merge(pivot_df, left_on='ntaname', right_on='neighborhood', how='left').fillna(0)
    gdf['difference_rounded'] = gdf['difference'].round().astype(int)


    max_abs_diff = max(abs(gdf['difference'].max()), abs(gdf['difference'].min()))
    if max_abs_diff == 0: max_abs_diff = 1 

    #RGBA (Red, Green, Blue, Alpha)
    #Stronger the red, the larger the decrease in ridership over holiday 
    #Stronger the blue, the larger the increase in ridership over holiday
    gdf['fill_color'] = gdf['difference'].apply(
        lambda diff: [0, 191, 255, (diff / max_abs_diff) * 255] if diff > 0 else [255, 0, 0, (abs(diff) / max_abs_diff) * 255]
    )

    view_state = pdk.ViewState(longitude=-73.98, latitude=40.75, zoom=10, pitch=45, bearing=0)

    layer = pdk.Layer(
        'GeoJsonLayer',
        gdf,
        opacity=0.6,
        stroked=True,
        filled=True,
        get_fill_color='fill_color',
        get_line_color=[255, 255, 255, 100],
        get_line_width=10,
        pickable=True
    )

    tooltip = {
        "html": "<b>Neighborhood:</b> {ntaname}<br/><b>Ridership Change:</b> {difference}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white",
            "padding": "5px",
            "maxWidth": "200px"
        }
    }

    r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
    st.pydeck_chart(r)

def main():
    st.set_page_config(layout="wide")
    set_page_theme() 

    con = get_db_connection()
    
    left_margin, content_column, right_margin = st.columns([1, 2, 1])

    with content_column:
        with st.form(key="analysis_controls_form"):
            st.title("Holiday vs. Average Day: A Citi Bike Ridership Analysis 🚴")
            st.markdown("""
            Inspired by New York City MTA's article, this dashboard presents how New Yorkers' bike-riding habits change on major holidays. 
            Select a holiday and year, then click 'Analyze' to see how ridership on that day 
            compares to a typical day.
            """)
            st.subheader("Select Your Analysis Parameters")

            holidays = {
                "New Year's Day": (1, 1), "Valentine's Day": (2, 14), "St. Patrick's Day": (3, 17),
                "Juneteenth": (6, 19), "Independence Day (July 4th)": (7, 4), "Halloween": (10, 31),
                "Veterans Day": (11, 11), "Christmas Day": (12, 25)
            }

            col1, col2 = st.columns(2)
            with col1:
                selected_holiday_name = st.selectbox("Select a Holiday:", options=list(holidays.keys()))
            with col2:
                year_options = list(range(2020, 2025))
                selected_year = st.selectbox("Select a Year:", options=year_options, index=len(year_options) - 1)
            
            time_options = [datetime.time(h, 0) for h in range(24)]
            selected_time = st.slider(
                "Select Hour of Day to Visualize on Map:",
                min_value=datetime.time(0, 0),
                max_value=datetime.time(23, 0),
                value=datetime.time(17, 0),
                step=datetime.timedelta(hours=1),
                format="HH:mm"
            )

            submitted = st.form_submit_button("Analyze")

        if submitted:
            if con:
                if st.session_state.get('materialized_for_year') != selected_year:
                    with st.spinner(f"Preparing spatial data for {selected_year}..."):
                        materialize_unique_stations_table(con, selected_year)
                        materialize_station_neighborhood_join(con, 'data/nyc_bound.geojson')
                        st.session_state.materialized_for_year = selected_year

                month, day = holidays[selected_holiday_name]
                holiday_date = datetime.date(selected_year, month, day)
                
                st.info(f"Analyzing **{selected_holiday_name}** which fell on a **{holiday_date.strftime('%A')}** in **{selected_year}**.")

                neighborhood_analysis_df = get_holiday_comparison_data(con, holiday_date)
                
                if neighborhood_analysis_df is not None and not neighborhood_analysis_df.empty:
                    
                    # --- ADDED THE LINE CHART BACK IN ---
                    st.markdown("---")
                    st.header(f"Overall Hourly Ridership: {selected_holiday_name} vs. A Typical Day")
                    
                    # 1. Aggregate neighborhood data to get city-wide totals
                    line_chart_df = neighborhood_analysis_df.groupby(['hour_of_day', 'category'])['trips'].sum().reset_index()

                    # 2. Create and display the line chart
                    fig = px.line(
                        line_chart_df,
                        x='hour_of_day',
                        y='trips',
                        color='category',
                        labels={'hour_of_day': 'Hour of the Day', 'trips': 'Total Number of Trips', 'category': 'Day Type'},
                        markers=True,
                        color_discrete_map={'Baseline': 'darkorange', 'Holiday': 'aqua'}
                    )
                    fig.update_layout(
                        template='plotly_dark',
                        plot_bgcolor='rgba(0, 0, 0, 0)',
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                        font_color='white',
                        legend_font_color='white'
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # --- GEOGRAPHIC MAP VISUALIZATION ---
                    st.markdown("---")
                    #st.header("Geographic Hotspots by Hour")
                    st.header(f"Geographic Hotspots at {selected_time.strftime('%H:%M')}")
                    st.markdown("""
                    (Red: Decrease ridership count over holiday; Blue: Increase ridership count over holiday)
                    """)
                    display_nyc_map('data/nyc_bound.geojson', neighborhood_analysis_df, selected_time.hour)


                else:
                    st.warning("No data returned for the selected period. Please try a different year.")

if __name__ == "__main__":
    main()