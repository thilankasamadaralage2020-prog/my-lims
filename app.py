import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v44.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT, format_used TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LAB DETAILS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- DYNAMIC FBC RANGES ---
def get_fbc_structure(age_y, gender):
    # Common Parameters
    base = [
        {"label": "Total White Cell Count (WBC)", "unit": "10^3/uL"},
        {"label": "Neutrophils", "unit": "%"},
        {"label": "Lymphocytes", "unit": "%"},
        {"label": "Monocytes", "unit": "%"},
        {"label": "Eosinophils", "unit": "%"},
        {"label": "Basophils", "unit": "%"},
        {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL"},
        {"label": "MCV", "unit": "fL"},
        {"label": "MCH", "unit": "pg"},
        {"label": "MCHC", "unit": "g/dL"},
        {"label": "RDW", "unit": "%"},
        {"label": "Platelet Count", "unit": "10^3/uL"}
    ]

    if age_y < 5:
        format_name = "BABY FORMAT"
        ranges = {
            "WBC": "5.0 - 15.0", "Hb": "10.5 - 14.0", "RBC": "3.8 - 5.2", 
            "MCV": "75 - 90", "MCH": "24 - 30", "MCHC": "32 - 36", "RDW": "11.5 - 15.0", "PLT": "150 - 450"
        }
    elif gender == "Male":
        format_name = "ADULT MALE FORMAT"
        ranges = {
            "WBC": "4.0 - 11.0", "Hb": "13.5 - 17.5", "RBC": "4.5 - 5.5", 
            "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "PLT": "150 - 410"
        }
    else:
        format_name = "ADULT FEMALE FORMAT"
        ranges = {
            "WBC": "4.0 - 11.0", "Hb": "12.0 - 15.5", "RBC": "3.8 - 4.8", 
            "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "PLT": "150 - 410"
        }

    # Assign Hemoglobin and append to list
    hb_range = ranges["Hb"]
    final_structure = [{"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": hb_range}] + [
        {**f, "range": ranges.get(f['label'].split(" (")[0], "As per standards")} for f in base
    ]
    return final_structure, format_name

# --- UI HEADER ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
    with col2:
        st.markdown(f"### {LAB_NAME}\n{LAB_ADDRESS} | Tel: {LAB_TEL}")
    st.write("---")

# --- TECHNICIAN MODULE ---
def technician_portal():
    st.subheader("🔬 FBC Result Entry Panel")
    pending = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
    
    for i, row in pending.iterrows():
        # රෝගියාගේ නම සමඟ වයස දර්ශනය කිරීම
        patient_display = f"{row['name']} ({row['age_y']}Y {row['age_m']}M)"
        with st.expander(f"📝 {row['ref_no']} - {patient_display}"):
            fbc_structure, fmt = get_fbc_structure(row['age_y'], row['gender'])
            st.info(f"Loading Format: **{fmt}**")
            
            with st.form(f"fbc_v4_{row['ref_no']}"):
                res_in = {}
                for field in fbc_structure:
                    c1, c2, c3 = st.columns([3, 1, 2])
                    res_in[field['label']] = c1.text_input(field['label'])
                    c2.write(f"\n{field['unit']}")
                    c3.caption(f"Ref Range: {field['range']}")
                
                if st.form_submit_button("Authorize & Save"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", 
                              (row['ref_no'], json.dumps(res_in), st.session_state.username, str(date.today()), fmt))
                    conn.commit()
                    st.success("Authorized Successfully!")
                    st.rerun()

# --- BILLING MODULE ---
def billing_portal():
    ui_header()
    st.subheader("📝 New Registration")
    with st.form("billing_form"):
        col1, col2 = st.columns(2)
        salute = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
        p_name = col2.text_input("Patient Name")
        age_y = col1.number_input("Age (Years)", 0, 120)
        age_m = col2.number_input("Age (Months)", 0, 11)
        gender = col1.selectbox("Gender", ["Male", "Female"])
        mobile = col2.text_input("Mobile")
        
        # SQL Fix: Ensure number of columns matches number of '?'
        if st.form_submit_button("Save & Print"):
            ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
            c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (ref, salute, p_name, age_y, age_m, gender, mobile, "Self", "FBC", 400.0, 50.0, 350.0, str(date.today()), st.session_state.username, "Active"))
            conn.commit()
            st.success(f"Bill Saved: {ref}")

# --- MAIN APP LOGIC ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Login")
else:
    if st.session_state.user_role == "Technician":
        technician_portal()
    elif st.session_state.user_role == "Billing":
        billing_portal()
    elif st.session_state.user_role == "Admin":
        st.write("Admin Dashboard Active")
    elif st.session_state.user_role == "Satellite":
        st.write("Satellite Dashboard Active")
    
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
