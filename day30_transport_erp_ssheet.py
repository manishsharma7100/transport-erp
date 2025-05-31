import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import numpy as np
import joblib
import os
import requests


# ---------------- GOOGLE SHEET SETUP ----------------

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gspread"], scope
)

client = gspread.authorize(creds)
sheet = client.open("transport_trip_log").sheet1

# Ensure header row exists
try:
    if sheet.row_count == 0 or sheet.row_values(1) == []:
        sheet.append_row(["Date", "Driver", "Vehicle", "From", "To", "KM", "Cost", "Trip Type"])
except:
    pass

#new addtiion in google sheet setup 

def train_model_from_sheet(sheet):
   

    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty and "KM" in df.columns and "Cost" in df.columns:
        df = df.dropna(subset=["KM", "Cost"])
        df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")

        km = df[["KM"]].values
        cost = df["Cost"].values

        model = LinearRegression()
        model.fit(km, cost)

        joblib.dump(model, "trip_cost_model.pkl")
        return model
    else:
        return None


#Google Maps setup

def get_distance_from_google_maps(origin, destination):
    try:
        api_key = st.secrets["maps_api_key"]
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origin,
            "destinations": destination,
            "key": api_key,
            "units": "metric"
        }
        response = requests.get(url, params=params)
        data = response.json()

        if data["status"] == "OK":
            distance_text = data["rows"][0]["elements"][0]["distance"]["text"]
            distance_km = float(distance_text.replace(" km", "").replace(",", ""))
            return distance_km
        else:
            return None
    except Exception as e:
        st.warning(f"Google Maps error: {e}")
        return None


# ---------------- MODEL TRAINING ----------------
MODEL_PATH = "trip_cost_model.pkl"

def train_model_from_sheet(sheet):
    try:
        records = sheet.get_all_records()
        if not records:
            st.warning("⚠️ No data found in sheet to train.")
            return None

        df = pd.DataFrame(records)

        if "KM" not in df.columns or "Cost" not in df.columns:
            st.error("❌ Columns 'KM' and 'Cost' are missing in sheet.")
            return None

        df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
        df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
        df.dropna(subset=["KM", "Cost"], inplace=True)

        X = df[["KM"]]
        y = df["Cost"]

        trained_model = LinearRegression()
        trained_model.fit(X, y)
        joblib.dump(trained_model, MODEL_PATH)

        return trained_model

    except Exception as e:
        st.error(f"❌ Training failed: {e}")
        return None

# Try loading the model
model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as e:
        st.warning(f"⚠️ Failed to load model from file: {e}")

if model is None:
    model = train_model_from_sheet(sheet)

# ---------------- STREAMLIT APP START ----------------
st.set_page_config(page_title="Transport ERP", layout="wide")
st.title("🚛 Transport ERP System")

menu = st.sidebar.radio("📂 Navigate", ["Trip Entry", "Trip Table", "Analytics", "Admin Tools"])

# Add rest of your Streamlit app here...
# This block sets up Sheet + AI Model with error handling and retraining ability.



# -------------------- TRIP ENTRY --------------------
if menu == "Trip Entry":
    st.subheader("📝 Enter a New Trip")

    driver = st.text_input("Driver Name")
    vehicle = st.text_input("Vehicle Number")
    from_city = st.text_input("From City")
    to_city = st.text_input("To City")

    # Fetch distance using Google Maps API
    distance_km = None
    if from_city and to_city:
        from urllib.parse import quote
        import requests

        api_key = st.secrets["AIzaSyBVTGnsJ5U-uKtMLPozXK2mwC1DRkCn7iY"]
        origins = quote(from_city)
        destinations = quote(to_city)
        url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origins}&destinations={destinations}&key={AIzaSyBVTGnsJ5U-uKtMLPozXK2mwC1DRkCn7iY}"

        try:
            response = requests.get(url)
            data = response.json()
            if data["rows"][0]["elements"][0]["status"] == "OK":
                meters = data["rows"][0]["elements"][0]["distance"]["value"]
                distance_km = round(meters / 1000, 2)
                st.success(f"📍 Distance fetched: {distance_km} km")
            else:
                st.warning("⚠️ Google API could not find a valid route.")
        except Exception as e:
            st.error(f"❌ Error fetching distance: {e}")

    if st.button("Save Trip"):
        if driver and vehicle and from_city and to_city and distance_km:
            trip_type = "LONG TRIP" if distance_km >= 300 else "SHORT TRIP"
            predicted_cost = model.predict([[distance_km]])[0]

            trip_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                driver,
                vehicle,
                from_city,
                to_city,
                distance_km,
                round(predicted_cost),
                trip_type
            ]

            try:
                sheet.append_row(trip_row)
                st.success("✅ Trip saved with AI cost prediction!")
            except Exception as e:
                st.error(f"❌ Failed to save trip: {e}")
        else:
            st.error("Please complete all fields and ensure distance is fetched.")
# -------------------- TRIP TABLE --------------------

elif menu == "Trip Table":
    st.subheader("📋 View and Filter Trips")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        # Convert KM and Cost to numbers if needed
        df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
        if "Cost" in df.columns:
            df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")

        # Trip Type filter (if present)
        if "Trip Type" in df.columns:
            trip_type_filter = st.selectbox("Filter by Trip Type", options=["All"] + sorted(df["Trip Type"].unique()))
        else:
            trip_type_filter = "All"

        driver_filter = st.selectbox("Filter by Driver", options=["All"] + sorted(df["Driver"].unique()))
        from_filter = st.selectbox("Filter by From City", options=["All"] + sorted(df["From"].unique()))

        filtered_df = df.copy()
        if trip_type_filter != "All":
            filtered_df = filtered_df[filtered_df["Trip Type"] == trip_type_filter]
        if driver_filter != "All":
            filtered_df = filtered_df[filtered_df["Driver"] == driver_filter]
        if from_filter != "All":
            filtered_df = filtered_df[filtered_df["From"] == from_filter]

        st.dataframe(filtered_df)

        # Show revenue only if 'Cost' exists
        if "Cost" in filtered_df.columns:
            st.metric("Total Predicted Revenue", f"₹{filtered_df['Cost'].sum():,.0f}")

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered CSV", data=csv, file_name="filtered_trips.csv", mime="text/csv")
    else:
        st.warning("No data found.")


# ---------------- ANALYTICS ----------------
if menu == "Analytics":
    st.subheader("📊 Trip Analytics Dashboard")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Trips", len(df))
        col2.metric("Total KM", f"{df['KM'].sum():.0f} km")
        col3.metric("Drivers", df["Driver"].nunique())

        st.markdown("---")
        st.subheader("Trips per Driver")
        st.bar_chart(df["Driver"].value_counts())

        st.subheader("KM per Driver (Pie)")
        fig, ax = plt.subplots()
        df.groupby("Driver")["KM"].sum().plot.pie(autopct="%1.1f%%", ax=ax)
        st.pyplot(fig)

        # ---------- COST PREDICTION VS ACTUAL ----------
        st.subheader("📉 Actual vs Predicted Trip Cost")
        try:
            df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
            df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")
            df = df.dropna(subset=["KM", "Cost"])

            df["Predicted"] = model.predict(df[["KM"]])

            st.line_chart(df[["Cost", "Predicted"]])

            df["Error"] = df["Cost"] - df["Predicted"]
            st.dataframe(df[["KM", "Cost", "Predicted", "Error"]])

        except Exception as e:
            st.warning(f"Could not generate prediction graph: {e}")

    else:
        st.warning("No data to analyze.")

# The rest of your app (Trip Entry, Trip Table, Admin Tools) continues here...


# -------------------- ADMIN TOOLS --------------------
elif menu == "Admin Tools":
    st.subheader("🛠️ Admin Panel – Manage Trips")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        st.dataframe(df)
        row_to_delete = st.number_input("Enter row number to delete", min_value=0, max_value=len(df)-1, step=1)
        if st.button("Delete Selected Row"):
            sheet.delete_rows(row_to_delete + 2)  # +2 accounts for header and 0-index
            st.success(f"Deleted row {row_to_delete}")

        if st.button("🗑️ Clear All Trips"):
            sheet.clear()
            sheet.append_row(["Date", "Driver", "Vehicle", "From", "To", "KM"])
            st.success("All trips cleared.")
    else:
        st.warning("No trip data available.")

    st.markdown("---")
    st.markdown("### 🔁 Retrain AI Model")
    if st.button("Retrain from Sheet Data"):
        new_model = train_model_from_sheet(sheet)
        if new_model:
            model = new_model
            st.success("✅ Model retrained successfully and saved!")
        else:
            st.error("❌ Failed to retrain. Please ensure KM and Cost data exist.")


