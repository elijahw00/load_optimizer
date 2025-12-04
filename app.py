# app.py
# Web app to upload a CSV, set constraints, see optimized plan,
# download the plan as CSV, and (optionally) see pickups/dropoffs on a map.

import io
import pandas as pd
import streamlit as st

from load_optimizer.models import Job, ProblemConfig
from load_optimizer.optimizer import optimize_jobs


st.set_page_config(page_title="Truck Load Optimizer", layout="wide")


def jobs_from_dataframe(df):
    jobs = []
    for _, row in df.iterrows():
        job = Job(
            id=str(row["id"]),
            revenue=float(row["revenue"]),
            loaded_miles=float(row["loaded_miles"]),
            deadhead_miles=float(row["deadhead_miles"]),
            hours=float(row["hours"]),
            pallets=float(row["pallets"]),
            pickup_city=str(row.get("pickup_city", "")),
            dropoff_city=str(row.get("dropoff_city", "")),
            date=str(row.get("date", "")),
            notes=str(row.get("notes", ""))
        )
        jobs.append(job)
    return jobs


st.title("Truck Load Optimizer")
st.write("Upload a CSV of possible jobs, set your limits, and get the best combination.")

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

# Sidebar core settings
st.sidebar.header("Core Settings")

max_hours = st.sidebar.number_input("Max driving hours", value=11.0)
max_pallets = st.sidebar.number_input("Max pallets", value=6.0)
fuel_cost = st.sidebar.number_input("Fuel cost per mile", value=0.70)
driver_cost = st.sidebar.number_input("Driver cost per hour", value=25.0)

st.sidebar.header("Optional Constraints (leave off to ignore)")
use_max_deadhead = st.sidebar.checkbox("Limit total deadhead miles?")
max_deadhead = None
if use_max_deadhead:
    max_deadhead = st.sidebar.number_input("Max deadhead miles", value=100.0)

use_max_total_miles = st.sidebar.checkbox("Limit total miles?")
max_total_miles = None
if use_max_total_miles:
    max_total_miles = st.sidebar.number_input(
        "Max total miles (loaded + deadhead)", value=400.0
    )

use_min_profit = st.sidebar.checkbox("Require minimum profit per job?")
min_profit_per_job = None
if use_min_profit:
    min_profit_per_job = st.sidebar.number_input("Min profit per job", value=300.0)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    st.subheader("Uploaded Jobs")
    st.dataframe(df)

    # -----------------------------
    # Filters based on city and date
    # -----------------------------
    st.sidebar.header("Filters")

    if "pickup_city" in df.columns:
        pickup_cities = sorted(df["pickup_city"].dropna().unique())
        include_pickup = st.sidebar.multiselect(
            "Only include pickup cities (leave empty for all):",
            pickup_cities
        )
    else:
        include_pickup = []

    if "dropoff_city" in df.columns:
        dropoff_cities = sorted(df["dropoff_city"].dropna().unique())
        exclude_dropoff = st.sidebar.multiselect(
            "Exclude dropoff cities:",
            dropoff_cities
        )
    else:
        exclude_dropoff = []

    exclude_weekends = False
    if "date" in df.columns:
        exclude_weekends = st.sidebar.checkbox("Exclude weekend jobs?")

    # Apply filters to the dataframe
    filtered_df = df.copy()

    # Include only certain pickup cities (if user selected any)
    if len(include_pickup) > 0 and "pickup_city" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["pickup_city"].isin(include_pickup)]

    # Exclude certain dropoff cities
    if len(exclude_dropoff) > 0 and "dropoff_city" in filtered_df.columns:
        filtered_df = filtered_df[~filtered_df["dropoff_city"].isin(exclude_dropoff)]

    # Remove weekend jobs based on date column
    if exclude_weekends and "date" in filtered_df.columns:
        try:
            dates = pd.to_datetime(filtered_df["date"], errors="coerce")
            # weekday() 0–4 are Mon–Fri, 5–6 are Sat–Sun
            filtered_df = filtered_df[dates.dt.weekday < 5]
        except Exception:
            pass  # if date parsing fails, just don't filter

    if len(filtered_df) == 0:
        st.warning("No jobs left after applying filters.")
    else:
        st.subheader("Jobs After Filters")
        st.dataframe(filtered_df)

        jobs = jobs_from_dataframe(filtered_df)

        cfg = ProblemConfig(
            max_hours=max_hours,
            max_pallets=max_pallets,
            fuel_cost_per_mile=fuel_cost,
            driver_cost_per_hour=driver_cost
        )

        if st.button("Optimize"):
            result = optimize_jobs(
                jobs,
                cfg,
                max_deadhead=max_deadhead,
                max_total_miles=max_total_miles,
                min_profit_per_job=min_profit_per_job
            )

            st.subheader("Optimization Result")
            st.write("Status:", result["status"])
            st.write("Total Profit:", round(result["total_profit"], 2))
            st.write("Total Hours:", result["total_hours"])
            st.write("Total Pallets:", result["total_pallets"])

            # Build dataframe of chosen jobs
            chosen_rows = []
            total_miles = 0.0

            for job in result["chosen_jobs"]:
                profit = result["all_profits"][job.id]
                job_miles = job.loaded_miles + job.deadhead_miles
                total_miles += job_miles

                chosen_rows.append({
                    "id": job.id,
                    "pickup_city": job.pickup_city,
                    "dropoff_city": job.dropoff_city,
                    "date": job.date,
                    "revenue": job.revenue,
                    "loaded_miles": job.loaded_miles,
                    "deadhead_miles": job.deadhead_miles,
                    "hours": job.hours,
                    "pallets": job.pallets,
                    "profit": round(profit, 2),
                    "total_miles_for_job": job_miles
                })

            if len(chosen_rows) > 0:
                chosen_df = pd.DataFrame(chosen_rows)
                st.subheader("Chosen Jobs")
                st.dataframe(chosen_df)

                # Summary metrics
                total_profit = result["total_profit"]
                if result["total_hours"] > 0:
                    profit_per_hour = total_profit / result["total_hours"]
                else:
                    profit_per_hour = 0

                if total_miles > 0:
                    profit_per_mile = total_profit / total_miles
                else:
                    profit_per_mile = 0

                st.markdown(
                    f"**Total miles:** {round(total_miles, 2)}  |  "
                    f"**Profit per hour:** {round(profit_per_hour, 2)}  |  "
                    f"**Profit per mile:** {round(profit_per_mile, 2)}"
                )

                # --------------------------------
                # A. Download optimized plan as CSV
                # --------------------------------
                download_df = chosen_df.copy()
                # Add a total row at the bottom
                total_row = {
                    "id": "TOTAL",
                    "pickup_city": "",
                    "dropoff_city": "",
                    "date": "",
                    "revenue": "",
                    "loaded_miles": "",
                    "deadhead_miles": "",
                    "hours": result["total_hours"],
                    "pallets": result["total_pallets"],
                    "profit": round(total_profit, 2),
                    "total_miles_for_job": round(total_miles, 2)
                }
                download_df = pd.concat(
                    [download_df, pd.DataFrame([total_row])],
                    ignore_index=True
                )

                csv_buffer = io.StringIO()
                download_df.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="Download optimized plan as CSV",
                    data=csv_buffer.getvalue(),
                    file_name="optimized_plan.csv",
                    mime="text/csv"
                )

                # ---------------------------
                # B. Map of pickup/dropoffs
                # ---------------------------
                # Map only works if the CSV has coordinate columns:
                #   pickup_lat, pickup_lon, dropoff_lat, dropoff_lon
                if ("pickup_lat" in filtered_df.columns and
                        "pickup_lon" in filtered_df.columns and
                        "dropoff_lat" in filtered_df.columns and
                        "dropoff_lon" in filtered_df.columns):

                    map_rows = []
                    # Use only the rows corresponding to chosen jobs
                    chosen_ids = list(chosen_df["id"].unique())
                    coord_df = filtered_df[filtered_df["id"].astype(str).isin(chosen_ids)]

                    for _, row in coord_df.iterrows():
                        # pickup point
                        map_rows.append({
                            "lat": float(row["pickup_lat"]),
                            "lon": float(row["pickup_lon"]),
                            "type": "pickup"
                        })
                        # dropoff point
                        map_rows.append({
                            "lat": float(row["dropoff_lat"]),
                            "lon": float(row["dropoff_lon"]),
                            "type": "dropoff"
                        })

                    if len(map_rows) > 0:
                        map_df = pd.DataFrame(map_rows)
                        st.subheader("Pickup and Dropoff Locations")
                        st.map(map_df[["lat", "lon"]])
                else:
                    st.info(
                        "Add 'pickup_lat', 'pickup_lon', 'dropoff_lat', 'dropoff_lon' "
                        "columns to your CSV to see a map of locations."
                    )
            else:
                st.write("No jobs selected under these constraints.")
else:
    st.info("Upload a CSV file to begin.")
