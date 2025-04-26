import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import os

# Load API key from Streamlit secrets
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
try:
    schedule_df = pd.read_csv("flanders-veteran_spring2025.csv")
    st.write("Current schedule: flanders-veteran_spring2025")
except FileNotFoundError:
    st.error("CSV file 'flanders-veteran_spring2025' not found.")
    st.stop()


def fetch_weather(location, date_str):
    url = f"{BASE_URL}/{location}/{date_str}?unitGroup=metric&key={API_KEY}&include=hours"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch weather data: {response.status_code}")
        return None


def round_schedule_time(schedule_time):
    try:
        schedule_dt = datetime.strptime(schedule_time, "%I:%M %p")
    except ValueError:
        return schedule_time
    if schedule_dt.minute >= 30:
        rounded_dt = schedule_dt + timedelta(minutes=(60 - schedule_dt.minute))
    else:
        rounded_dt = schedule_dt - timedelta(minutes=schedule_dt.minute)
    return rounded_dt.strftime("%I:%M %p")


def get_cardinal_direction(degrees):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    idx = round(degrees / 22.5) % 16
    return directions[idx]


def display_wind_message(weather_data, day_label):
    relevant_hours = [
        hour for hour in weather_data["days"][0]["hours"]
        if 5 <= datetime.strptime(hour["datetime"], "%H:%M:%S").hour <= 23
    ]
    if relevant_hours:
        max_gust = max(relevant_hours, key=lambda x: x.get("windgust", 0))
        gust_speed = max_gust.get("windgust", 0)
        gust_time = datetime.strptime(max_gust["datetime"], "%H:%M:%S").strftime("%I:%M %p")

        if gust_speed >= 80:
            st.warning(f"{day_label}: 💨⚠️ WARNING: Very strong winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
        elif 50 <= gust_speed < 80:
            st.info(f"{day_label}: 💨 Strong winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
        elif 30 <= gust_speed < 50:
            st.info(f"{day_label}: Moderate winds forecast. Gusts: {gust_speed} km/h at {gust_time}.")
    else:
        st.info(f"{day_label}: No significant wind data available between 5 AM and 11 PM.")


# Set Newfoundland timezone
newfoundland_tz = pytz.timezone("America/St_Johns")

# Current date and time in Newfoundland timezone
current_datetime = datetime.now(newfoundland_tz)
st.write(f"**Current Date and Time:** {current_datetime.strftime('%A, %b %d, %Y %I:%M %p')}")

# Sidebar
st.sidebar.title("About")
st.sidebar.info(
    """
    **Weather from Visual Crossing ([visualcrossing.com](https://www.visualcrossing.com))**
    for the 5km Bell Island - Portugal Cove ferry route.

    Select a day and location to update the schedule and weather.

    **Disclaimer:**
    - Weather rounded to nearest hour.
    - General guide only. Confirm with official sources.
    """
)

st.sidebar.title("Useful Links")
st.sidebar.markdown("[Marine Forecast - EastCoast](https://weather.gc.ca/marine/forecast_e.html?mapID=14&siteID=04100)")
st.sidebar.markdown("[511NL - Ferry Updates](https://511nl.ca/list/ferryterminalsforlist)")
st.sidebar.markdown("[Bell Island - Portugal Cove Schedules](https://www.gov.nl.ca/ti/ferryservices/schedules/a-bipc/)")
st.sidebar.markdown("[Bell Island Ferry Facebook Group](https://www.facebook.com/groups/232199710220394)")
st.sidebar.markdown("[NTV Live Webcam - Bell Island](https://ntvplus.ca/pages/webcam-stphilips-bellisland)")
st.sidebar.markdown("[Ferry map tracking](https://www.marinetraffic.com/en/ais/home/centerx:-52.901/centery:47.624/zoom:13)")

# Dropdowns for day and location
days = [(current_datetime + timedelta(days=i)).strftime("%A, %b %d") for i in range(7)]
selected_day = st.selectbox("Select a day:", days)
selected_day_name = (current_datetime + timedelta(days=days.index(selected_day))).strftime("%A")
selected_date = (current_datetime + timedelta(days=days.index(selected_day))).strftime("%Y-%m-%d")

selected_dock = st.selectbox("Select Ferry Dock", LOCATIONS.keys())

if selected_dock:
    def is_day_in_range(day_field, selected_day):
        if day_field == "Monday to Friday":
            return selected_day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        return day_field == selected_day

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

            selected_base_date = current_datetime + timedelta(days=days.index(selected_day))
            current_selected_datetime = datetime.combine(
                selected_base_date.date(),
                current_datetime.time()
            ).replace(tzinfo=newfoundland_tz)

            departure_times_dt = []
            for _, row in filtered_schedule.iterrows():
                original_time = row["Time"]
                try:
                    dep_time = datetime.strptime(original_time, "%I:%M %p")
                    dep_time = dep_time.replace(
                        year=selected_base_date.year,
                        month=selected_base_date.month,
                        day=selected_base_date.day,
                        tzinfo=newfoundland_tz
                    )
                    departure_times_dt.append((dep_time, original_time, row["Ferry"]))
                except Exception as e:
                    st.error(f"Error parsing time {original_time}: {e}")

            future_departures = [(dep_time, t, ferry) for dep_time, t, ferry in departure_times_dt if dep_time > current_selected_datetime]
            next_departure_time = min(future_departures, default=(None, None, None))[0]

            for dep_time, original_time, ferry_name in departure_times_dt:
                label = f"{original_time} ({ferry_name})"
                if dep_time < current_selected_datetime:
                    label = f"**:red[*Departed*]** {label}"
                elif dep_time == next_departure_time:
                    label = f"**:green[*Next Departure*]** {label}"

                rounded_time = round_schedule_time(original_time)
                matched_hour = next((hour for hour in weather_data["days"][0]["hours"]
                                    if datetime.strptime(hour["datetime"], "%H:%M:%S").strftime("%I:%M %p") == rounded_time), None)
                if matched_hour:
                    st.write(
                        f"{label}: {matched_hour.get('temp', 'N/A')}°C, {matched_hour.get('conditions', 'N/A')}, "
                        f"Wind {get_cardinal_direction(matched_hour.get('winddir', 0))}: {matched_hour.get('windspeed', 'N/A')} km/h, "
                        f"Gusts: {matched_hour.get('windgust', 'N/A')} km/h"
                    )
                else:
                    st.write(f"{label}: Weather data not available.")




