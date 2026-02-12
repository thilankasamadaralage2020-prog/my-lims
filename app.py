import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_ultimate_v46.db', check_same_thread=False)
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

# --- FBC DYNAMIC LOGIC ---
def get_fbc_structure(age_y, gender):
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

    if age_y < 5:
        fmt = "FBC BABY FORMAT"
        ranges = {"WBC": "5.0-15.0", "Hb": "10.5-14.0", "RBC": "3.8-5.2", "MCV": "75-90", "MCH": "24-30", "MCHC": "32-36", "RDW": "11.5-15.0", "PLT": "150-450", "Other": "Baby Norms"}
    elif gender == "Male":
        fmt = "FBC ADULT MALE FORMAT"
        ranges = {"WBC": "4.0-11.0", "Hb": "13.5-17.5", "RBC": "4.5-5.5", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "PLT": "150-410", "Other": "Standard"}
    else:
        fmt = "FBC ADULT FEMALE FORMAT"
        ranges = {"WBC": "4.0-11.0", "Hb": "12.0-15.5", "RBC": "3.8-4.8", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "PLT": "150-410", "Other": "Standard"}

    for p in params:
        key = p['label'].split(" (")[0].split(" /")[0]
        p['range'] = ranges.get(key, ranges.get("Other", "Standard"))
    
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
    # --- SIDEBAR ---
    st.sidebar.title(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        ui_header()
        st.title("🛡️ Administration Dashboard")
        menu = st.sidebar.selectbox("Admin Menu", ["User Accounts", "Doctor Management", "Test Management", "Financial Reports"])
        
        if menu == "User Accounts":
            with st.form("u_add"):
                un = st.text_input("Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Save User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))
            
        elif menu == "Doctor Management":
            st.subheader("Manage Referral Doctors")
            with st.form("doc_add"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
            
        elif menu == "Test Management":
            with st.form("t_add"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price")
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        ui_header()
        st.subheader("📝 New Registration")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            sal = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            pname = col2.text_input("Patient Name")
            ay = col1.number_input("Age (Years)", 0, 120)
            am = col2.number_input("Age (Months)", 0, 11)
            gen = col1.selectbox("Gender", ["Male", "Female"])
            mob = col2.text_input("Mobile")
            doc_list = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            p_doc = st.selectbox("Referring Doctor", ["Self"] + doc_list)
            
        tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
        sel = st.multiselect("Tests", [f"{r['test_name']} - {r['price']}" for i, r in tests_db.iterrows()])
        
        gross = sum([float(s.split(" - ")[-1]) for s in sel])
        disc = st.number_input("Discount", 0.0); net = gross - disc
        st.write(f"### Net Amount: LKR {net:,.2f}")
        
        if st.button("Save & Print Bill"):
            ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
            tn = ", ".join([s.split(" - ")[0] for s in sel])
            c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (ref, sal, pname, ay, am, gen, mob, p_doc, tn, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
            conn.commit(); st.success(f"Saved! Ref: {ref}")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        ui_header()
        st.subheader("🔬 FBC Result Entry Panel")
        pending = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        for i, row in pending.iterrows():
            with st.expander(f"📝 {row['ref_no']} - {row['name']} (Age: {row['age_y']}Y {row['age_m']}M)"):
                fbc_p, fmt = get_fbc_structure(row['age_y'], row['gender'])
                st.caption(f"Target Format: **{fmt}**")
                with st.form(f"fbc_f_{row['ref_no']}"):
                    res_dict = {}
                    for p in fbc_p:
                        c1, c2, c3 = st.columns([3, 1, 2])
                        res_dict[p['label']] = c1.text_input(p['label'], key=f"{row['ref_no']}_{p['label']}")
                        c2.write(f"\n{p['unit']}")
                        c3.info(f"Ref: {p['range']}")
                    if st.form_submit_button("Authorize & Save"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", 
                                  (row['ref_no'], json.dumps(res_dict), st.session_state.username, str(date.today()), fmt))
                        conn.commit(); st.success("Authorized!"); st.rerun()

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Download Reports")
        q = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
        reps = pd.read_sql_query(q, conn)
        for i, row in reps.iterrows():
            with st.container(border=True):
                st.write(f"**{row['name']}** ({row['ref_no']}) | Auth by: {row['authorized_by']}")
                st.button("Print PDF", key=f"p_{row['ref_no']}")

conn.close()
