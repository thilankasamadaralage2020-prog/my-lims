import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v45.db', check_same_thread=False)
    c = conn.cursor()
    # පරණ table එක තිබේ නම් එය ඉවත් කර අලුතින් නිවැරදිව සෑදීම (OperationalError මගහරවා ගැනීමට)
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

# --- FBC DYNAMIC LOGIC ---
def get_fbc_structure(age_y, gender):
    # සියලුම FBC පරාමිතීන් (MCH, MCHC, RDW ඇතුළුව)
    params = [
        {"label": "Total White Cell Count (WBC)", "unit": "10^3/uL"},
        {"label": "Neutrophils", "unit": "%"},
        {"label": "Lymphocytes", "unit": "%"},
        {"label": "Monocytes", "unit": "%"},
        {"label": "Eosinophils", "unit": "%"},
        {"label": "Basophils", "unit": "%"},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL"},
        {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL"},
        {"label": "HCT / PCV", "unit": "%"},
        {"label": "MCV", "unit": "fL"},
        {"label": "MCH", "unit": "pg"},
        {"label": "MCHC", "unit": "g/dL"},
        {"label": "RDW", "unit": "%"},
        {"label": "Platelet Count", "unit": "10^3/uL"}
    ]

    # වයස සහ Gender අනුව Reference Ranges වෙනස් කිරීම
    if age_y < 5:
        fmt = "FBC BABY FORMAT"
        ranges = {"WBC": "5.0-15.0", "Hb": "10.5-14.0", "RBC": "3.8-5.2", "MCV": "75-90", "MCH": "24-30", "MCHC": "32-36", "RDW": "11.5-15.0", "PLT": "150-450", "Other": "Adult levels"}
    elif gender == "Male":
        fmt = "FBC ADULT MALE FORMAT"
        ranges = {"WBC": "4.0-11.0", "Hb": "13.5-17.5", "RBC": "4.5-5.5", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "PLT": "150-410", "Other": "Standard"}
    else:
        fmt = "FBC ADULT FEMALE FORMAT"
        ranges = {"WBC": "4.0-11.0", "Hb": "12.0-15.5", "RBC": "3.8-4.8", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "PLT": "150-410", "Other": "Standard"}

    # Range එක සෙවීමේ Logic එක
    for p in params:
        key = p['label'].split(" (")[0].split(" /")[0] # Short key extraction
        p['range'] = ranges.get(key, ranges.get("Other", "As per Lab"))
    
    return params, fmt

# --- UI HEADER ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
    with col2:
        st.markdown(f"### {LAB_NAME}\n{LAB_ADDRESS} | Tel: {LAB_TEL}")
    st.write("---")

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login_form"):
            st.subheader("🔑 System Login")
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Username or Password")
else:
    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        ui_header()
        st.title("🛡️ Admin Dashboard")
        admin_menu = st.sidebar.selectbox("Menu", ["Users", "Doctors", "Tests", "Reports"])
        if admin_menu == "Users":
            with st.form("u_add"):
                nu = st.text_input("Username"); np = st.text_input("Password"); nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Save"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))
        elif admin_menu == "Tests":
            with st.form("t_add"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price")
                if st.form_submit_button("Add Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        ui_header()
        st.subheader("📝 Patient Registration")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            sal = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            pname = col2.text_input("Patient Name")
            ay = col1.number_input("Age (Years)", 0, 120)
            am = col2.number_input("Age (Months)", 0, 11)
            gen = col1.selectbox("Gender", ["Male", "Female"])
            mob = col2.text_input("Mobile No")
            doc = st.selectbox("Referring Doctor", ["Self"] + [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()])
            
        tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
        sel_tests = st.multiselect("Select Tests", [f"{r['test_name']} - LKR {r['price']}" for i, r in tests_db.iterrows()])
        
        gross = sum([float(s.split(" - LKR ")[-1]) for s in sel_tests])
        disc = st.number_input("Discount (LKR)", 0.0)
        net = gross - disc
        st.write(f"### Final Payable: LKR {net:,.2f}")
        
        if st.button("Save & Print Bill", use_container_width=True):
            if pname and sel_tests:
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                tnames = ", ".join([s.split(" - LKR")[0] for s in sel_tests])
                # මෙහිදී column 15 ම නිවැරදිව ඇතුළත් කර ඇත
                c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (ref, sal, pname, ay, am, gen, mob, doc, tnames, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success(f"Bill Saved Successfully! Ref: {ref}")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        ui_header()
        st.subheader("🔬 FBC Result Entry Panel")
        # Billing table එකෙන් දත්ත තිබේදැයි පරීක්ෂා කිරීම
        pending_bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        
        if pending_bills.empty:
            st.info("No pending bills found.")
        else:
            for i, row in pending_bills.iterrows():
                # බිල් අංකය සමඟ රෝගියාගේ නම සහ වයස පෙන්වීම
                label = f"📝 {row['ref_no']} - {row['name']} (Age: {row['age_y']}Y {row['age_m']}M)"
                with st.expander(label):
                    # FBC format එක තෝරා ගැනීම
                    fbc_params, format_name = get_fbc_structure(row['age_y'], row['gender'])
                    st.caption(f"Applied Format: **{format_name}** | Gender: {row['gender']}")
                    
                    with st.form(f"fbc_entry_{row['ref_no']}"):
                        res_data = {}
                        for p in fbc_params:
                            c1, c2, c3 = st.columns([3, 1, 2])
                            res_data[p['label']] = c1.text_input(p['label'], key=f"{row['ref_no']}_{p['label']}")
                            c2.write(f"\n{p['unit']}")
                            c3.info(f"Ref: {p['range']}")
                        
                        if st.form_submit_button("Authorize & Save Result", use_container_width=True):
                            c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", 
                                      (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today()), format_name))
                            conn.commit()
                            st.success("Report Authorized!")
                            st.rerun()

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Authorized Reports")
        query = "SELECT b.*, r.data, r.authorized_by, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
        reports = pd.read_sql_query(query, conn)
        for i, row in reports.iterrows():
            with st.container(border=True):
                st.write(f"**{row['name']}** ({row['ref_no']}) - {row['format_used']}")
                st.button("Print Report", key=f"print_{row['ref_no']}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
