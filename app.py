
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from rapidfuzz import fuzz

# ================= PAGE CONFIG =================

st.set_page_config(
    page_title="DataGuard | Duplicate Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB = "/content/duplicate_framework.db"

# ================= CUSTOM DESIGN =================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #F5F7FC;
}

[data-testid="stSidebar"] {
    background: #111827;
}

[data-testid="stSidebar"] * {
    color: #E5E7EB !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] label {
    background: #1F2937;
    border-radius: 9px;
    padding: 10px;
    margin-bottom: 5px;
}

.main-title {
    font-size: 30px;
    font-weight: 800;
    color: #172554;
    margin-bottom: 4px;
}

.subtitle {
    color: #64748B;
    font-size: 14px;
    margin-bottom: 25px;
}

.metric-card {
    background: white;
    border: 1px solid #E5EAF3;
    border-radius: 15px;
    padding: 20px;
    box-shadow: 0 3px 12px rgba(15,23,42,0.04);
    min-height: 125px;
}

.metric-label {
    color: #64748B;
    font-size: 13px;
    font-weight: 600;
}

.metric-value {
    color: #172554;
    font-size: 30px;
    font-weight: 800;
    margin-top: 10px;
}

.metric-icon {
    font-size: 22px;
}

.section-heading {
    color: #172554;
    font-size: 20px;
    font-weight: 700;
    margin-top: 15px;
    margin-bottom: 12px;
}

.info-panel {
    background: #EEF2FF;
    border-left: 4px solid #6366F1;
    border-radius: 8px;
    padding: 15px;
    color: #3730A3;
}

div.stButton > button {
    background: #5145CD;
    color: white;
    border: none;
    border-radius: 9px;
    font-weight: 600;
    padding: 10px 20px;
}

div.stButton > button:hover {
    background: #4338CA;
    color: white;
    border: none;
}

[data-testid="stFileUploader"] {
    background: white;
    border: 1px dashed #A5B4FC;
    border-radius: 12px;
    padding: 12px;
}

[data-testid="stMetric"] {
    background: white;
    border: 1px solid #E5EAF3;
    border-radius: 12px;
    padding: 15px;
}

hr {
    border-color: #E2E8F0;
}
</style>
""", unsafe_allow_html=True)


# ================= DATABASE =================

def setup_database():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            total_records INTEGER,
            exact_duplicates INTEGER,
            fuzzy_duplicates INTEGER,
            cleaned_records INTEGER,
            processed_at TEXT
        )
    """)

    conn.commit()
    conn.close()


setup_database()


# ================= HELPER FUNCTIONS =================

def normalize(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def detect_exact_duplicates(df, columns):

    normalized = df[columns].copy()

    for col in columns:
        normalized[col] = normalized[col].apply(normalize)

    duplicate_mask = normalized.duplicated(keep="first")

    duplicate_indices = list(df.index[duplicate_mask])
    clean_indices = list(df.index[~duplicate_mask])

    return duplicate_indices, clean_indices


def calculate_similarity(row1, row2, columns):

    scores = []

    for col in columns:

        a = normalize(row1[col])
        b = normalize(row2[col])

        if not a and not b:
            continue

        scores.append(fuzz.ratio(a, b))

    return sum(scores) / len(scores) if scores else 0


def detect_fuzzy_duplicates(df, columns, threshold):

    pairs = []
    duplicate_indices = []
    kept_indices = []

    for index in df.index:

        matched = False

        for previous in kept_indices:

            score = calculate_similarity(
                df.loc[index],
                df.loc[previous],
                columns
            )

            if score >= threshold:

                pairs.append({
                    "Duplicate Row": index + 1,
                    "Matched With Row": previous + 1,
                    "Similarity (%)": round(score, 2)
                })

                duplicate_indices.append(index)
                matched = True
                break

        if not matched:
            kept_indices.append(index)

    return pairs, duplicate_indices


def save_history(filename, total, exact, fuzzy, cleaned):

    conn = sqlite3.connect(DB)

    conn.execute("""
        INSERT INTO history
        (filename, total_records, exact_duplicates,
         fuzzy_duplicates, cleaned_records, processed_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        filename,
        total,
        exact,
        fuzzy,
        cleaned,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_history():

    conn = sqlite3.connect(DB)

    history = pd.read_sql_query(
        "SELECT * FROM history ORDER BY id DESC",
        conn
    )

    conn.close()

    return history


def metric_card(icon, label, value):

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# ================= SIDEBAR =================

st.sidebar.markdown("""
<div style="padding:12px 5px 25px 5px;">
    <div style="font-size:27px;">🔍 <b>DataGuard</b></div>
    <div style="font-size:11px;color:#9CA3AF;">
        DATA QUALITY MANAGEMENT
    </div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "MAIN MENU",
    [
        "Dashboard",
        "Data Cleaning",
        "Processing History",
        "About Project"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**SYSTEM STATUS**")
st.sidebar.success("Application Online")
st.sidebar.caption("Duplicate Detection Framework")


# ================= DASHBOARD =================

if page == "Dashboard":

    history = load_history()

    st.markdown(
        '<div class="main-title">Data Quality Dashboard</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Monitor your dataset, detect duplicates and improve data quality.</div>',
        unsafe_allow_html=True
    )

    total_tasks = len(history)

    exact_total = (
        int(history["exact_duplicates"].sum())
        if not history.empty else 0
    )

    fuzzy_total = (
        int(history["fuzzy_duplicates"].sum())
        if not history.empty else 0
    )

    total_duplicates = exact_total + fuzzy_total

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("📁", "Processing Tasks", total_tasks)

    with c2:
        metric_card("🔁", "Exact Duplicates", exact_total)

    with c3:
        metric_card("🔎", "Fuzzy Matches", fuzzy_total)

    with c4:
        metric_card("🗄️", "Database", "Connected")

    st.markdown('<div class="section-heading">Project Overview</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="info-panel">
        <b>Welcome to DataGuard!</b><br>
        This application uses exact matching and fuzzy matching
        techniques to identify duplicate records and improve
        dataset quality.
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-heading">Detection Summary</div>',
                unsafe_allow_html=True)

    chart_data = pd.DataFrame({
        "Detection Type": ["Exact Duplicates", "Fuzzy Matches"],
        "Records": [exact_total, fuzzy_total]
    }).set_index("Detection Type")

    st.bar_chart(chart_data)

    st.markdown('<div class="section-heading">Recent Activities</div>',
                unsafe_allow_html=True)

    if history.empty:
        st.info("No processing activity yet. Start by uploading a dataset.")
    else:
        st.dataframe(
            history.head(5),
            use_container_width=True,
            hide_index=True
        )


# ================= DATA CLEANING =================

elif page == "Data Cleaning":

    st.markdown(
        '<div class="main-title">Dataset Cleaning</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Upload, analyze and clean your records using intelligent duplicate detection.</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Upload your dataset",
        type=["csv", "xlsx", "xls"],
        help="Supported formats: CSV and Excel"
    )

    if uploaded_file:

        try:

            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # New upload resets old displayed results
            if st.session_state.get("current_filename") != uploaded_file.name:
                st.session_state["current_filename"] = uploaded_file.name
                st.session_state.pop("result", None)

            st.success("Dataset uploaded successfully!")

            st.markdown(
                '<div class="section-heading">Dataset Information</div>',
                unsafe_allow_html=True
            )

            a, b, c = st.columns(3)

            a.metric("Total Records", len(df))
            b.metric("Total Columns", len(df.columns))
            c.metric("Missing Values", int(df.isnull().sum().sum()))

            with st.expander("Preview Uploaded Dataset", expanded=True):
                st.dataframe(
                    df.head(10),
                    use_container_width=True
                )

            columns = list(df.columns)

            st.markdown("---")
            st.markdown(
                '<div class="section-heading">1. Exact Duplicate Detection</div>',
                unsafe_allow_html=True
            )

            exact_columns = st.multiselect(
                "Choose columns for exact matching",
                columns,
                default=columns
            )

            st.caption(
                "Exact matching identifies records whose selected values match exactly."
            )

            st.markdown(
                '<div class="section-heading">2. Fuzzy Duplicate Detection</div>',
                unsafe_allow_html=True
            )

            default_fuzzy = (
                ["Name"] if "Name" in columns else columns[:1]
            )

            fuzzy_columns = st.multiselect(
                "Choose columns for fuzzy matching",
                columns,
                default=default_fuzzy
            )

            threshold = st.slider(
                "Similarity Threshold",
                min_value=50,
                max_value=100,
                value=85,
                help="A higher threshold requires a closer match."
            )

            remove_fuzzy = st.checkbox(
                "Remove fuzzy duplicate records from the final dataset",
                value=False
            )

            st.markdown("---")

            if st.button(
                "🚀 Start Duplicate Detection",
                type="primary",
                use_container_width=True
            ):

                if not exact_columns or not fuzzy_columns:
                    st.error("Please select columns for both detection methods.")

                else:

                    with st.spinner("Analyzing records..."):

                        exact_indices, clean_indices = (
                            detect_exact_duplicates(df, exact_columns)
                        )

                        exact_clean_df = df.loc[clean_indices].copy()

                        fuzzy_pairs, fuzzy_indices = (
                            detect_fuzzy_duplicates(
                                exact_clean_df,
                                fuzzy_columns,
                                threshold
                            )
                        )

                        if remove_fuzzy:
                            cleaned_df = exact_clean_df.drop(
                                index=fuzzy_indices
                            ).copy()
                        else:
                            cleaned_df = exact_clean_df.copy()

                        save_history(
                            uploaded_file.name,
                            len(df),
                            len(exact_indices),
                            len(fuzzy_pairs),
                            len(cleaned_df)
                        )

                        st.session_state["result"] = {
                            "original": df.copy(),
                            "cleaned": cleaned_df.copy(),
                            "exact": len(exact_indices),
                            "fuzzy": len(fuzzy_pairs),
                            "pairs": fuzzy_pairs,
                            "removed_fuzzy": remove_fuzzy
                        }

                    st.success("Duplicate detection completed successfully!")

            # DISPLAY RESULTS

            if "result" in st.session_state:

                result = st.session_state["result"]

                original = result["original"]
                cleaned = result["cleaned"]

                st.markdown("---")
                st.markdown(
                    '<div class="section-heading">3. Detection Results</div>',
                    unsafe_allow_html=True
                )

                r1, r2, r3, r4 = st.columns(4)

                r1.metric("Original Records", len(original))
                r2.metric("Exact Duplicates", result["exact"])
                r3.metric("Fuzzy Matches", result["fuzzy"])
                r4.metric("Final Records", len(cleaned))

                st.markdown(
                    '<div class="section-heading">Record Comparison</div>',
                    unsafe_allow_html=True
                )

                comparison = pd.DataFrame({
                    "Category": [
                        "Exact Duplicates",
                        "Fuzzy Matches",
                        "Final Records"
                    ],
                    "Records": [
                        result["exact"],
                        result["fuzzy"],
                        len(cleaned)
                    ]
                }).set_index("Category")

                st.bar_chart(comparison)

                st.markdown(
                    '<div class="section-heading">Fuzzy Match Details</div>',
                    unsafe_allow_html=True
                )

                if result["pairs"]:
                    st.dataframe(
                        pd.DataFrame(result["pairs"]),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No fuzzy duplicate matches found.")

                st.markdown(
                    '<div class="section-heading">Cleaned Dataset</div>',
                    unsafe_allow_html=True
                )

                st.dataframe(
                    cleaned.head(20),
                    use_container_width=True
                )

                csv_data = cleaned.to_csv(
                    index=False
                ).encode("utf-8")

                report = pd.DataFrame({
                    "Metric": [
                        "Original Records",
                        "Exact Duplicates",
                        "Fuzzy Matches",
                        "Cleaned Records"
                    ],
                    "Count": [
                        len(original),
                        result["exact"],
                        result["fuzzy"],
                        len(cleaned)
                    ]
                })

                d1, d2 = st.columns(2)

                with d1:
                    st.download_button(
                        "⬇️ Download Cleaned Dataset",
                        data=csv_data,
                        file_name="cleaned_dataset.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                with d2:
                    st.download_button(
                        "⬇️ Download Detection Report",
                        data=report.to_csv(index=False).encode("utf-8"),
                        file_name="duplicate_report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

                if result["removed_fuzzy"]:
                    st.caption(
                        "Fuzzy matches were excluded from the final dataset."
                    )
                else:
                    st.caption(
                        "Fuzzy matches were reported but retained in the final dataset."
                    )

        except Exception as e:
            st.error(f"Dataset processing error: {e}")


# ================= PROCESSING HISTORY =================

elif page == "Processing History":

    st.markdown(
        '<div class="main-title">Processing History</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">View previously processed datasets and detection reports.</div>',
        unsafe_allow_html=True
    )

    history = load_history()

    if history.empty:
        st.info("No processing history available yet.")

    else:

        c1, c2 = st.columns(2)

        c1.metric("Total Processing Tasks", len(history))

        c2.metric(
            "Total Records Analyzed",
            int(history["total_records"].sum())
        )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇️ Download Processing History",
            data=history.to_csv(index=False).encode("utf-8"),
            file_name="processing_history.csv",
            mime="text/csv"
        )


# ================= ABOUT PROJECT =================

elif page == "About Project":

    st.markdown(
        '<div class="main-title">About The Project</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">Understanding the framework and its technologies.</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    ### 🔍 Automated Duplicate Record Detection and Removal Framework

    This project is designed to identify duplicate and similar records
    in datasets and improve overall data quality.

    ### Project Objectives

    - Identify exact duplicate records.
    - Identify similar records using fuzzy matching.
    - Remove unwanted duplicate records.
    - Generate cleaned datasets and detection reports.
    - Maintain processing history using SQLite.

    ### Detection Techniques

    **1. Exact Matching**

    Compares selected column values and identifies records
    that contain identical values.

    **2. Fuzzy Matching**

    Uses text similarity to identify records that are similar
    even when their spelling is slightly different.

    ### Technology Stack

    | Technology | Purpose |
    |---|---|
    | Python | Main programming language |
    | Pandas | Dataset processing |
    | RapidFuzz | Fuzzy text matching |
    | Streamlit | Web application |
    | SQLite | Processing history storage |
    | CSV / Excel | Dataset formats |

    ### Application Workflow

    Upload Dataset → Preview Records → Exact Matching →
    Fuzzy Matching → Review Results → Download Cleaned Dataset
    """)

    st.success("DataGuard - Duplicate Detection Framework")
