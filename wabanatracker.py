import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import os

# Load api key from streamlit
API_KEY = st.secrets["api_keys"]["visual_crossing_api_key"]

if not API_KEY:
    st.error("API key not found. Please ensure it's set in Streamlit's settings.")
    st.stop()

# API Configuration
BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

# Coordinates for the ferry docks
LOCATIONS = {
    "Bell Island": "47.6274,-52.9395",
    "Portugal Cove": "47.6196,-52.8672",
}

# Load schedule from CSV using Pandas

# --- Schedule selection ---
SCHEDULES = {
    "Legionnaire-Beaumont Temporary Dock Work 2025": "legionnaire-bh-dock_winter2025.csv",
    "Legionnaire–Flanders": "ferry_schedule.csv",
    "Beaumont–Flanders Winter 2024": "beaumont-flanders_winter2024.csv"
}

# Dropdown for schedule selection
schedule_choice = st.selectbox("Select a schedule:", list(SCHEDULES.keys()))

# Load the chosen CSV
schedule_file = SCHEDULES[schedule_choice]
try:
    schedule_df = pd.read_csv(schedule_file)
    st.write(f"✅ Current schedule loaded: **{schedule_choice}**")
except FileNotFoundError:
    st.error(f"CSV file '{schedule_file}' not found.")
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



# Set Newfoundland timezone
newfoundland_tz = pytz.timezone("America/St_Johns")

# Current date and time in Newfoundland timezone
current_datetime = datetime.now(newfoundland_tz)
st.write(f"**Current Date and Time:** {current_datetime.strftime('%A, %b %d, %Y %I:%M %p')}")

# Add About and Links section to the sidebar
st.sidebar.title("About")
st.sidebar.info(
    """
    **This weather data is collected from Visual Crossing ([visualcrossing.com](https://www.visualcrossing.com))** 
    to provide weather forecasts for each ferry departure on the 5km Bell Island - Portugal Cove route near St. John's, Newfoundland and Labrador, Canada. 
    
    Select a Day and Location
    and the weather data will update for each scheduled departure. The app contains weather for 7 days.
    
    **Disclaimer:**
    - Weather data is rounded to the nearest hour and may not be precise or up-to-the-minute.  
    - This is a general guide. Please check the marine forecast below and the NL ferry schedule for updates or changes.
    
    **This is a personal project.** It may contain errors. I may develop it further for accuracy, readability, etc.
    """
)

# Add Useful Links to the sidebar
st.sidebar.title("Useful Links")
st.sidebar.markdown("[Marine Forecast - EastCoast](https://511nl.ca/map#MarineWeather-143)")
st.sidebar.markdown("[511NL - Ferry Updates](https://511nl.ca/list/ferryterminalsforlist) Info about delays and cancellations")
st.sidebar.markdown("[GovNL Official Bell Island - Portugal Cove Schedules](https://www.gov.nl.ca/ti/ferryservices/schedules/a-bipc/)")
st.sidebar.markdown("[Bell Island Ferry Facebook Group](https://www.facebook.com/groups/232199710220394)")
st.sidebar.markdown("[NTV Live Webcam - Bell Island](https://ntvplus.ca/pages/webcam-stphilips-bellisland) View lineup")
st.sidebar.markdown("[Ferry map tracking](https://www.marinetraffic.com/en/ais/home/centerx:-52.901/centery:47.624/zoom:13)")

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
            st.header(f"Ferry Departure Schedule and Weather for {selected_day} at {selected_dock}")
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









