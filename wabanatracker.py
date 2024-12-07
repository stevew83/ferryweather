import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load api key from streamlit
API_KEY = st.secrets["api_keys"]["visual_crossing_api_key"]

if not API_KEY:
    st.error("API key not found. Please ensure it's set in the '.env' file.")
    st.stop()

# API Configuration
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Coordinates for the ferry docks
LOCATIONS = {
    "Bell Island": "47.6274,-52.9395",
    "Portugal Cove": "47.6196,-52.8672",
}

# Load schedule from CSV using Pandas
try:
    schedule_df = pd.read_csv("ferry_schedule.csv")
except FileNotFoundError:
    st.error("CSV file not found. Ensure 'ferry_schedule.csv' is in the same directory.")
    st.stop()

def fetch_weather(location, date_str):
    """Fetch hourly forecast data from Visual Crossing for the specified date."""
    url = f"{BASE_URL}/{location}/{date_str}?unitGroup=metric&key={API_KEY}&include=hours"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch weather data: {response.status_code}")
        return None

def round_schedule_time(schedule_time):
    """Round schedule time to the nearest hour for weather matching."""
    try:
        schedule_dt = datetime.strptime(schedule_time, "%I:%M %p")
    except ValueError:
        return schedule_time  # Return as-is for non-standard times
    if schedule_dt.minute >= 30:
        rounded_dt = schedule_dt + timedelta(minutes=(60 - schedule_dt.minute))
    else:
        rounded_dt = schedule_dt - timedelta(minutes=schedule_dt.minute)
    return rounded_dt.strftime("%I:%M %p")

def get_cardinal_direction(degrees):
    """Convert degrees to cardinal directions."""
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = round(degrees / 22.5) % 16
    return directions[idx]

# Define icons for wind levels
WIND_ICONS = {
    "strong": "💨",          # Strong wind
    "very_strong": "💨⚠️"   # Very strong wind
}



def display_wind_message(weather_data, day_label):
    """Display wind gust message for the selected day between 5 AM and 11 PM."""
    # Filter hours between 5 AM and 11 PM
    relevant_hours = [
        hour for hour in weather_data["days"][0]["hours"]
        if 5 <= datetime.strptime(hour["datetime"], "%H:%M:%S").hour <= 23
    ]
    
    # Icons for wind intensity
    WIND_ICONS = {
        "strong": "💨",          # Strong wind
        "very_strong": "💨⚠️"   # Very strong wind
    }
    
    if relevant_hours:
        max_gust = max(relevant_hours, key=lambda x: x.get("windgust", 0))
        gust_speed = max_gust.get("windgust", 0)
        gust_time = datetime.strptime(max_gust["datetime"], "%H:%M:%S").strftime("%I:%M %p")
        
        if gust_speed >= 80:
            st.warning(f"{day_label}: {WIND_ICONS['very_strong']} WARNING: Very strong winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
        elif 50 <= gust_speed < 80:
            st.info(f"{day_label}: {WIND_ICONS['strong']} Strong winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
        elif 30 <= gust_speed < 50:
            st.info(f"{day_label}: Moderate winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
    else:
        st.info(f"{day_label}: No significant wind data available between 5 AM and 11 PM.")



# Current date and time
current_datetime = datetime.now()
st.write(f"**Current Date and Time:** {current_datetime.strftime('%A, %b %d, %Y %I:%M %p')}")

# Dropdown for day selection
days = [(current_datetime + timedelta(days=i)).strftime("%A, %b %d") for i in range(7)]
selected_day = st.selectbox("Select a day:", days)
selected_day_name = (current_datetime + timedelta(days=days.index(selected_day))).strftime("%A")
selected_date = (current_datetime + timedelta(days=days.index(selected_day))).strftime("%Y-%m-%d")

# Dropdown to select location
selected_dock = st.selectbox("Select Ferry Dock", LOCATIONS.keys())

if selected_dock:
    # Filter the schedule for the selected dock and day
    # Map day ranges to corresponding days
    def is_day_in_range(day_field, selected_day):
        if day_field == "Monday to Friday":
            return selected_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        return day_field == selected_day  # Match exact days (e.g., "Saturday", "Sunday")

# Filter the schedule for the selected dock and day
    filtered_schedule = schedule_df[
        (schedule_df["Location"] == selected_dock) & 
        (schedule_df["Day"].apply(lambda x: is_day_in_range(x, selected_day_name)))
]


    if filtered_schedule.empty:
        st.warning("No ferry schedules found for the selected location and day.")
    else:
        weather_data = fetch_weather(LOCATIONS[selected_dock], selected_date)
        
        if weather_data:
            st.header(f"Schedule and Weather for {selected_day} at {selected_dock}")
            display_wind_message(weather_data, selected_day)

            # Display all scheduled times with weather
            for _, row in filtered_schedule.iterrows():
                original_time = row["Time"]
                rounded_time = round_schedule_time(original_time)
                
                # Match rounded time with weather data
                for hour in weather_data["days"][0]["hours"]:
                    forecast_time = datetime.strptime(hour["datetime"], "%H:%M:%S").strftime("%I:%M %p")
                    if forecast_time == rounded_time:
                        st.write(
                            f"**{original_time} ({row['Ferry']})**: {hour.get('temp', 'N/A')}°C, {hour.get('conditions', 'N/A')}, "
                            f"Wind {get_cardinal_direction(hour.get('winddir', 0))}: {hour.get('windspeed', 'N/A')} km/h, "
                            f"Gusts: {hour.get('windgust', 'N/A')} km/h"
                        )
                        break
