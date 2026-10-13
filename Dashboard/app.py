
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------
st.set_page_config(
    page_title="DAV Smart Attendance Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Smart Attendance System")
st.markdown("#### Interactive Student Attendance Analytics")
st.divider()

# --------------------------------------------------
# 2. LOCATE AND LOAD THE CSV DATASET
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

POSSIBLE_FILES = [
    BASE_DIR / "Final_AI_Assist_Attendance_DAV_Dataset.csv",
    BASE_DIR.parent / "Final_AI_Assist_Attendance_DAV_Dataset.csv",
    BASE_DIR / "data" / "Final_AI_Assist_Attendance_DAV_Dataset.csv",
]

DATA_FILE = next(
    (file for file in POSSIBLE_FILES if file.is_file()),
    None
)

if DATA_FILE is None:
    st.error("Attendance dataset not found.")
    st.write("Searched these locations:")
    for file in POSSIBLE_FILES:
        st.code(str(file))
    st.info(
        "Place Final_AI_Assist_Attendance_DAV_Dataset.csv "
        "in the Dashboard folder or the main DAV LAB folder."
    )
    st.stop()

try:
    df = pd.read_csv(DATA_FILE)
except Exception as error:
    st.error(f"Could not read the CSV: {error}")
    st.stop()

if df.empty:
    st.warning("The dataset is empty.")
    st.stop()

df.columns = df.columns.astype(str).str.strip()

st.caption(f"Dataset loaded: {DATA_FILE.name}")

# --------------------------------------------------
# 3. VALIDATE ATTENDANCE DATA
# --------------------------------------------------
if "Present_Flag" not in df.columns:
    st.error("Present_Flag column was not found.")
    st.write("Available columns:", df.columns.tolist())
    st.stop()

df["Present_Flag"] = pd.to_numeric(
    df["Present_Flag"], errors="coerce"
)

# Only 1 = present and 0 = absent are valid attendance records
valid_df = df[df["Present_Flag"].isin([0, 1])].copy()

if valid_df.empty:
    st.warning("No valid attendance records were found.")
    st.stop()

valid_df["Present_Flag"] = valid_df["Present_Flag"].astype(int)

# --------------------------------------------------
# 4. SIDEBAR FILTERS
# --------------------------------------------------
st.sidebar.title("🎛️ Dashboard Filters")

filtered_df = valid_df.copy()

search_columns = [
    col for col in filtered_df.columns
    if any(word in col.lower() for word in
           ["student_id", "student id", "student_name",
            "student name", "roll_no", "roll number",
            "roll no", "studentid", "name"])
]

search_text = st.sidebar.text_input(
    "Search student",
    placeholder="Enter student name or ID"
)

if search_text:
    if search_columns:
        mask = pd.Series(False, index=filtered_df.index)

        for col in search_columns:
            mask |= filtered_df[col].astype(str).str.contains(
                search_text, case=False, na=False, regex=False
            )

        filtered_df = filtered_df[mask]
    else:
        st.sidebar.warning(
            "No recognized student name or ID column was found."
        )

# Optional date filter if a date column exists
date_candidates = [
    col for col in filtered_df.columns
    if col.lower() in [
        "date", "attendance_date", "attendance date",
        "session_date", "session date"
    ]
]

if date_candidates:
    date_col = date_candidates[0]
    parsed_dates = pd.to_datetime(
        filtered_df[date_col], errors="coerce"
    )

    if parsed_dates.notna().any():
        filtered_df = filtered_df.copy()
        filtered_df["_Parsed_Date"] = parsed_dates

        available_dates = parsed_dates.dropna()

        min_date = available_dates.min().date()
        max_date = available_dates.max().date()

        date_range = st.sidebar.date_input(
            "Attendance date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range

            filtered_df = filtered_df[
                filtered_df["_Parsed_Date"].dt.date.between(
                    start_date, end_date
                )
            ]

# --------------------------------------------------
# 5. CALCULATE ATTENDANCE METRICS
# --------------------------------------------------
total_records = len(filtered_df)

present_count = int(
    (filtered_df["Present_Flag"] == 1).sum()
)

absent_count = int(
    (filtered_df["Present_Flag"] == 0).sum()
)

attendance_rate = (
    present_count / total_records * 100
    if total_records > 0 else 0
)

if "Late_Flag" in filtered_df.columns:
    late_values = pd.to_numeric(
        filtered_df["Late_Flag"], errors="coerce"
    )
    late_count = int((late_values == 1).sum())
else:
    late_count = None

# --------------------------------------------------
# 6. SUMMARY CARDS
# --------------------------------------------------
st.subheader("📌 Attendance Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Records", f"{total_records:,}")
c2.metric("Present Records", f"{present_count:,}")
c3.metric("Absent Records", f"{absent_count:,}")
c4.metric("Attendance Rate", f"{attendance_rate:.2f}%")

if late_count is not None:
    st.metric("Late Records", f"{late_count:,}")

st.caption(
    "These figures represent attendance records, not necessarily "
    "unique students. Attendance rate = present records / valid "
    "attendance records × 100."
)

st.divider()

# --------------------------------------------------
# 7. PRESENT VS ABSENT CHART
# --------------------------------------------------
st.subheader("📊 Present vs Absent")

status_df = pd.DataFrame({
    "Status": ["Present", "Absent"],
    "Records": [present_count, absent_count]
})

left, right = st.columns(2)

with left:
    fig = px.pie(
        status_df,
        names="Status",
        values="Records",
        hole=0.55,
        title="Attendance Status Distribution"
    )
    fig.update_traces(textinfo="label+percent")
    st.plotly_chart(fig, use_container_width=True)

with right:
    fig = px.bar(
        status_df,
        x="Status",
        y="Records",
        color="Status",
        text="Records",
        title="Attendance Record Counts"
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 8. LATE ARRIVAL ANALYSIS
# --------------------------------------------------
if "Late_Flag" in filtered_df.columns:
    st.subheader("⏰ Late Arrival Analysis")

    late_values = pd.to_numeric(
        filtered_df["Late_Flag"], errors="coerce"
    )

    late_df = pd.DataFrame({
        "Status": ["On Time / Not Late", "Late"],
        "Records": [
            int((late_values == 0).sum()),
            int((late_values == 1).sum())
        ]
    })

    fig = px.bar(
        late_df,
        x="Status",
        y="Records",
        color="Status",
        text="Records",
        title="Late vs Not-Late Records"
    )

    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 9. EXPLORE NUMERIC COLUMNS
# --------------------------------------------------
st.subheader("📈 Explore Dataset")

numeric_columns = filtered_df.select_dtypes(
    include="number"
).columns.tolist()

if numeric_columns:
    selected_column = st.selectbox(
        "Choose a numeric column",
        numeric_columns
    )

    fig = px.histogram(
        filtered_df,
        x=selected_column,
        title=f"Distribution of {selected_column}"
    )

    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# 10. VIEW ATTENDANCE RECORDS
# --------------------------------------------------
st.subheader("👨‍🎓 Attendance Records")

display_df = filtered_df.drop(
    columns=["_Parsed_Date"], errors="ignore"
)

st.dataframe(
    display_df,
    use_container_width=True,
    height=350
)

# --------------------------------------------------
# 11. DOWNLOAD FILTERED DATA
# --------------------------------------------------
st.divider()
st.subheader("⬇️ Download Reports")

csv_data = display_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered Attendance CSV",
    data=csv_data,
    file_name="dav_attendance_report.csv",
    mime="text/csv"
)

st.caption("DAV Lab Project | AI Smart Attendance System")
