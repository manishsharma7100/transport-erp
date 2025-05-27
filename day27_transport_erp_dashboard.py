import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Transport ERP", layout="wide")
st.title("🚛 Transport ERP System")

# Sidebar Navigation
menu = st.sidebar.radio(
    "📂 Navigate",
    ["Trip Entry", "Trip Table", "Analytics", "Admin Tools"]
)

file_path = "trip_log.csv"

# -------------------- TRIP ENTRY --------------------
if menu == "Trip Entry":
    st.subheader("📝 Enter a New Trip")

    driver = st.text_input("Driver Name")
    vehicle = st.text_input("Vehicle Number")
    from_city = st.text_input("From City")
    to_city = st.text_input("To City")
    km = st.number_input("Distance in KM", min_value=0.0, step=1.0)

    if st.button("Save Trip"):
        if driver and vehicle and from_city and to_city and km > 0:
            trip = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Driver": driver,
                "Vehicle": vehicle,
                "From": from_city,
                "To": to_city,
                "KM": km
            }

            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df = pd.concat([df, pd.DataFrame([trip])], ignore_index=True)
            else:
                df = pd.DataFrame([trip])

            df.to_csv(file_path, index=False)
            st.success("Trip saved successfully!")
        else:
            st.error("Please fill all fields.")

# -------------------- TRIP TABLE --------------------
elif menu == "Trip Table":
    st.subheader("📋 View and Filter Trips")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)

        driver_filter = st.selectbox("Filter by Driver", options=["All"] + sorted(df["Driver"].unique().tolist()))
        from_filter = st.selectbox("Filter by From City", options=["All"] + sorted(df["From"].unique().tolist()))

        filtered_df = df.copy()

        if driver_filter != "All":
            filtered_df = filtered_df[filtered_df["Driver"] == driver_filter]

        if from_filter != "All":
            filtered_df = filtered_df[filtered_df["From"] == from_filter]

        st.dataframe(filtered_df)

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Filtered CSV", data=csv, file_name="filtered_trips.csv", mime="text/csv")

    else:
        st.warning("No trip_log.csv found.")

# -------------------- ANALYTICS --------------------
elif menu == "Analytics":
    st.subheader("📊 Trip Analytics Dashboard")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)

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
        st.warning("No data found.")

# -------------------- ADMIN TOOLS --------------------
elif menu == "Admin Tools":
    st.subheader("🛠️ Admin Panel – Manage Trips")
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        st.dataframe(df)

        row_to_delete = st.number_input("Enter row number to delete", min_value=0, max_value=len(df)-1, step=1)
        if st.button("Delete Selected Row"):
            df = df.drop(index=row_to_delete).reset_index(drop=True)
            df.to_csv(file_path, index=False)
            st.success(f"Deleted row {row_to_delete}")

        if st.button("🗑️ Clear All Trips"):
            df = pd.DataFrame(columns=["Date", "Driver", "Vehicle", "From", "To", "KM"])
            df.to_csv(file_path, index=False)
            st.success("All trips cleared.")
    else:
        st.warning("No trip data available.")
