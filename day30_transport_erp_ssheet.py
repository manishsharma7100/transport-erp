import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
import json

# ------------------ ML MODEL TRAINING ------------------
km_train = np.array([[50], [60], [80], [100], [120]])
cost_train = np.array([750, 900, 1200, 1500, 1800])
model = LinearRegression()
model.fit(km_train, cost_train)

# ------------------ GOOGLE SHEET SETUP ------------------
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

# Ensure header exists
try:
    if sheet.row_count == 0 or sheet.row_values(1) == []:
        sheet.append_row(["Date", "Driver", "Vehicle", "From", "To", "KM", "Cost", "Trip Type"])
except:
    pass

# ------------------ STREAMLIT LAYOUT ------------------
st.set_page_config(page_title="Transport ERP", layout="wide")
st.title("🚛 Transport ERP System")
menu = st.sidebar.radio("📂 Navigate", ["Trip Entry", "Trip Table", "Analytics", "Admin Tools"])

# ------------------ TRIP ENTRY ------------------
if menu == "Trip Entry":
    st.subheader("📝 Enter a New Trip")

    driver = st.text_input("Driver Name")
    vehicle = st.text_input("Vehicle Number")
    from_city = st.text_input("From City")
    to_city = st.text_input("To City")
    km = st.number_input("Distance in KM", min_value=0.0, step=1.0)

    if st.button("Save Trip"):
        if driver and vehicle and from_city and to_city and km > 0:
            trip_type = "LONG TRIP" if km >= 300 else "SHORT TRIP"
            predicted_cost = model.predict([[km]])[0]

            trip_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                driver, vehicle, from_city, to_city, km,
                round(predicted_cost), trip_type
            ]

            try:
                sheet.append_row(trip_row)
                st.success("✅ Trip saved with AI prediction!")
            except Exception as e:
                st.error(f"❌ Failed to save trip: {e}")
        else:
            st.error("Please fill all fields.")

# ------------------ TRIP TABLE ------------------
elif menu == "Trip Table":
    st.subheader("📋 View and Filter Trips")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df["KM"] = pd.to_numeric(df["KM"], errors="coerce")
        if "Cost" in df.columns:
            df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce")

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

        if "Cost" in filtered_df.columns:
            st.metric("Total Predicted Revenue", f"₹{filtered_df['Cost'].sum():,.0f}")

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered CSV", data=csv, file_name="filtered_trips.csv", mime="text/csv")
    else:
        st.warning("No data found.")

# ------------------ ANALYTICS ------------------
elif menu == "Analytics":
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
    else:
        st.warning("No data to analyze.")

# ------------------ ADMIN TOOLS ------------------
elif menu == "Admin Tools":
    st.subheader("🛠️ Admin Panel – Manage Trips")
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        st.dataframe(df)
        row_to_delete = st.number_input("Enter row number to delete", min_value=0, max_value=len(df)-1, step=1)
        if st.button("Delete Selected Row"):
            sheet.delete_rows(row_to_delete + 2)
            st.success(f"Deleted row {row_to_delete}")

        if st.button("🗑️ Clear All Trips"):
            sheet.clear()
            sheet.append_row(["Date", "Driver", "Vehicle", "From", "To", "KM", "Cost", "Trip Type"])
            st.success("All trips cleared.")
    else:
        st.warning("No trip data available.")
