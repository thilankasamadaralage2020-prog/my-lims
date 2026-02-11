import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# 1. දත්ත ගබඩාව සැකසීම
def init_db():
    conn = sqlite3.connect('lab_data.db', check_same_thread=False)
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

# 2. UI සැකසීම
st.set_page_config(page_title="Smart LIMS", layout="wide")
st.title("🔬 Laboratory Information Management System")

menu = ["🏠 Dashboard", "📝 Register Sample", "🧪 Update Results"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "🏠 Dashboard":
    st.subheader("Lab Overview")
    df = pd.read_sql_query("SELECT * FROM samples", conn)
    st.dataframe(df, use_container_width=True)

elif choice == "📝 Register Sample":
    st.subheader("New Registration")
    with st.form("reg_form"):
        s_id = st.text_input("Sample ID")
        s_patient = st.text_input("Patient Name")
        s_test = st.selectbox("Test Type", ["Blood", "Urine", "PCR"])
        s_date = st.date_input("Date", date.today())
        submit = st.form_submit_button("Submit")
        
        if submit:
            # මෙන්න මෙතැන තිබූ වැරැද්ද මම නිවැරදි කළා
            c.execute("INSERT INTO samples VALUES (?,?,?,?,?,?)", 
                      (s_id, s_patient, s_test, str(s_date), "Pending", "N/A"))
            conn.commit()
            st.success("Sample Added!")

elif choice == "🧪 Update Results":
    st.subheader("Update Results")
    s_id_up = st.text_input("Sample ID to Update")
    res = st.text_area("Results")
    if st.button("Save"):
        c.execute("UPDATE samples SET results=?, status=? WHERE sample_id=?", (res, "Completed", s_id_up))
        conn.commit()
        st.success("Updated!")

conn.close()
