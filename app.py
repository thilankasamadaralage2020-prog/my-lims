import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# 1. දත්ත ගබඩාව සැකසීම (Backend)
def init_db():
    conn = sqlite3.connect('lims_database.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS samples
                 (sample_id TEXT PRIMARY KEY,
                  patient_name TEXT,
                  test_type TEXT,
                  received_date TEXT,
                  status TEXT,
                  results TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# 2. වෙබ් අඩවියේ පෙනුම සැකසීම (Frontend)
st.set_page_config(page_title="Smart LIMS Portal", layout="wide")

st.title("🔬 Laboratory Information Management System")
st.markdown("---")

# Sidebar මෙනුව
menu = ["🏠 Dashboard", "📝 Register Sample", "🧪 Update Results", "📊 Inventory"]
choice = st.sidebar.selectbox("Main Menu", menu)

# --- DASHBOARD ---
if choice == "🏠 Dashboard":
    st.subheader("Laboratory Data Overview")
    df = pd.read_sql_query("SELECT * FROM samples", conn)
    if df.empty:
        st.info("No samples registered yet.")
    else:
        st.dataframe(df, use_container_width=True)

# --- REGISTER SAMPLE ---
elif choice == "📝 Register Sample":
    st.subheader("New Sample Registration")
    with st.form("reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            s_id = st.text_input("Sample ID (e.g., S-101)")
            s_patient = st.text_input("Patient/Source Name")
        with col2:
            s_test = st.selectbox("Test Type", ["Blood Test", "Urine Analysis", "PCR", "Biochemistry"])
            s_date = st.date_input("Date Received", date.today())
       
        submit = st.form_submit_button("Register Sample")
       
        if submit:
            if s_id and s_patient:
                try:
                    c.execute("INSERT INTO samples (sample_id, patient_name, test_type, received_date, status, results) VALUES (?,?,?,?,?,?)",
                              (s_id, s_patient, s_test, str(s_date),
