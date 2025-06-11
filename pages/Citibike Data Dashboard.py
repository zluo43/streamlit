import streamlit as st
import duckdb
import pandas as pd
# import pydeck as pdk # Not used in the provided relevant code
# import numpy as np # Not used in the provided relevant code
import plotly.express as px



def connect_to_duckdb():
    """
    Establishes a DuckDB in-memory connection and ensures 'httpfs' and 'spatial'
    extensions are loaded.
    """
    try:
        con = duckdb.connect(database=':memory:', read_only=False)
        con.execute("INSTALL spatial;")
        con.execute("LOAD spatial;")
        return con
    except Exception as e:
        st.error(f"Error connecting to DuckDB or loading extensions: {e}")
        return None

def load_citibike_data(con, year):
    """
    Loads Citibike data for the specified year from an S3 source into DuckDB,
    takes a 25% Bernoulli sample, and returns the sample as a PyArrow Table.
    """
    if con is None:
        return None

    main_table_name = f"citibike_data_{year}"
    sample_table_name = f"citibike_sample_{year}_12percent"

    try:
        st.info(f"Starting data load for {year}: Extracting data from Source Cooperative...Just a moment!")
        
        query_create_main_table = f"""
        CREATE OR REPLACE TABLE {main_table_name} AS
        SELECT ride_id, rideable_type, started_at as start_time, ended_at as end_time, 
               start_station_id, start_station_name, end_station_id, end_station_name, member_casual
        FROM read_parquet('s3://us-west-2.opendata.source.coop/zluo43/citibike/new_schema_combined_with_geom.parquet/**/*.parquet', hive_partitioning=1)
        WHERE year={year};
        """
        con.execute(query_create_main_table)

        st.info(f"Sampling 12% of the {year} data with Bernoulli...")
        query_create_sample_table = f"""
        CREATE OR REPLACE TABLE {sample_table_name} AS
        SELECT * FROM {main_table_name}
        USING SAMPLE 12% (BERNOULLI);
        """
        con.execute(query_create_sample_table)

        arrow_sample = con.execute(f"SELECT * FROM {sample_table_name}").arrow()

        if arrow_sample.num_rows == 0:
            st.warning(f"The sampled data for {year} is empty.")
        else:
            st.success(f"Sampled data for {year} fetched: {arrow_sample.num_rows} total rows.")
        return arrow_sample

    except Exception as e:
        st.error(f"Error during Citibike data loading or sampling for {year}: {e}")
        return None

def display_top_start_stations_chart(db_connection, year):
    if db_connection is None:
        st.warning("Database connection is not available for top stations chart.")
        return

    sample_table_name = f"citibike_sample_{year}_12percent"
    st.header(f"Top 7 Most Popular Start Stations ({year} Sampled Data)")
    try:
        query_top_stations = f"""
        SELECT
            start_station_name,
            COUNT(*) AS number_of_trips
        FROM {sample_table_name}
        WHERE start_station_name IS NOT NULL
        GROUP BY start_station_name
        ORDER BY number_of_trips DESC
        LIMIT 7;
        """
        top_stations_arrow = db_connection.execute(query_top_stations).arrow()

        if top_stations_arrow.num_rows > 0:
            st.bar_chart(
                top_stations_arrow, 
                x='start_station_name', 
                y='number_of_trips', 
                x_label="Total Trips from Station", # Corrected: For horizontal, y is values (x-axis)
                y_label="Start Station Name",     # Corrected: For horizontal, x is categories (y-axis)
                horizontal=True
            )
        else:
            st.warning(f"No data available to display for top start stations for {year}.")
    except Exception as e:
        st.error(f"Error generating 'Top Start Stations' chart for {year}: {e}")

def display_member_casual_pie_chart(db_connection, year):
    if db_connection is None:
        st.warning("Database connection is not available for member/casual pie chart.")
        return

    sample_table_name = f"citibike_sample_{year}_12percent"
    st.header(f"Rider Type Distribution ({year} Sampled Data)")
    try:
        query_member_casual = f"""
        SELECT
            member_casual,
            COUNT(*) AS trip_count
        FROM {sample_table_name}
        WHERE member_casual IS NOT NULL AND member_casual IN ('member', 'casual')
        GROUP BY member_casual;
        """
        arrow_member_casual = db_connection.execute(query_member_casual).arrow()

        if arrow_member_casual.num_rows > 0:
            fig = px.pie(
                arrow_member_casual,
                names='member_casual',
                values='trip_count',
                title=f'Distribution of Trips by Rider Type ({year})',
                color='member_casual',
                color_discrete_map={'member':'#636EFA','casual':'#EF553B'}
            )
            fig.update_traces(textinfo='percent+label', pull=[0, 0.05])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No data available for rider type distribution for {year}.")
    except Exception as e:
        st.error(f"Error generating rider type pie chart for {year}: {e}")

def display_hourly_trip_distribution(db_connection, year):
    if db_connection is None:
        st.warning("Database connection is not available for hourly trip distribution chart.")
        return
    
    sample_table_name = f"citibike_sample_{year}_12percent"
    st.header(f"Trip Distribution by Hour of the Day ({year} Sampled Data)")
    try:
        query_hourly_trips = f"""
        SELECT
            strftime(start_time, '%H') AS hour_of_day,
            COUNT(*) AS number_of_trips
        FROM {sample_table_name}
        WHERE start_time IS NOT NULL
        GROUP BY hour_of_day
        ORDER BY hour_of_day ASC;
        """
        hourly_trips_arrow = db_connection.execute(query_hourly_trips).arrow()

        if hourly_trips_arrow.num_rows > 0:
            st.line_chart(
                hourly_trips_arrow, 
                x='hour_of_day', 
                y='number_of_trips', 
                x_label='Hour of the Day', 
                y_label='Number of Trips'
            )
        else:
            st.warning(f"No data available to display for hourly trip distribution for {year}.")
    except Exception as e:
        st.error(f"Error generating 'Hourly Trip Distribution' chart for {year}: {e}")

def main():
    st.set_page_config(layout="wide")
    year_options = list(range(2020, 2026)) # 2020 through 2025
    default_year = 2024 if 2024 in year_options else year_options[-1]
    st.title(f"NYC Citibike Data Dashboard ")
    
    selected_year = st.selectbox( 
        "Select Year (currently only support 2020-2025):", 
        options=year_options, 
        index=year_options.index(default_year)
    )

    

    con = connect_to_duckdb()
    
    if not con:
        st.error("Critical: Failed to connect to DuckDB. Dashboard cannot proceed.")
        st.stop()

    arrow_sample = load_citibike_data(con, selected_year)

    if arrow_sample is not None and arrow_sample.num_rows > 0:
        with st.expander(f"View Raw Data Preview for {selected_year} (First 10 Rows)", expanded=False):
            st.write(f"Previewing {min(10, arrow_sample.num_rows)} row(s) from the {arrow_sample.num_rows} sampled rows.")
            st.dataframe(arrow_sample.slice(0, 10)) # Display only up to 10 rows or fewer if less are available
    elif arrow_sample is not None and arrow_sample.num_rows == 0:
        st.warning(f"Data loading and sampling for {selected_year} completed, but the resulting sample is empty.")
    else:
        st.error(f"Data for {selected_year} could not be loaded or sampled. Please check error messages.")
    
    st.markdown("---")
    display_top_start_stations_chart(con, selected_year)
    st.markdown("---")
    display_member_casual_pie_chart(con, selected_year)
    st.markdown("---")
    display_hourly_trip_distribution(con, selected_year)

    if con:
        try:
            con.close()
        except Exception as e:
            st.warning(f"Notice: Issue closing DuckDB connection: {e}")

if __name__ == "__main__":
    main()