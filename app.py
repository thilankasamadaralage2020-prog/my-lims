import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v43.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- FBC PARAMETERS DEFINITION ---
FBC_FIELDS = [
    {"label": "WBC (Total White Cell Count)", "unit": "10^3/uL", "range": "4.0 - 11.0"},
    {"label": "Neutrophils", "unit": "%", "range": "40 - 75"},
    {"label": "Lymphocytes", "unit": "%", "range": "20 - 45"},
    {"label": "Monocytes", "unit": "%", "range": "02 - 10"},
    {"label": "Eosinophils", "unit": "%", "range": "01 - 06"},
    {"label": "Basophils", "unit": "%", "range": "00 - 01"},
    {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": "11.5 - 16.5"},
    {"label": "RBC (Red Blood Cell)", "unit": "10^6/uL", "range": "3.8 - 5.8"},
    {"label": "HCT / PCV", "unit": "%", "range": "37 - 47"},
    {"label": "MCV", "unit": "fL", "range": "80 - 95"},
    {"label": "Platelet Count", "unit": "10^3/uL", "range": "150 - 450"}
]

# --- UI HEADER ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=130)
    with col2:
        st.markdown(f"### {LAB_NAME}\n{LAB_ADDRESS} | Tel: {LAB_TEL}")
    st.write("---")

# --- PDF REPORT GENERATOR (ADVANCED TABLE) ---
def create_fbc_report_pdf(bill_row, results_json, auth_user):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 25)
    
    pdf.set_font("Arial", 'B', 16); pdf.set_x(40); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 9); pdf.set_x(40); pdf.cell(0, 5, LAB_ADDRESS, ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Data
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Ref No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "FULL BLOOD COUNT (FBC)", ln=True, align='C'); pdf.ln(5)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
    pdf.cell(70, 10, "Component", 1, 0, 'L', True)
    pdf.cell(35, 10, "Result", 1, 0, 'C', True)
    pdf.cell(35, 10, "Unit", 1, 0, 'C', True)
    pdf.cell(50, 10, "Reference Range", 1, 1, 'C', True)

    # Table Body
    pdf.set_font("Arial", '', 10)
    results = json.loads(results_json)
    for field in FBC_FIELDS:
        res_val = results.get(field['label'], "")
        pdf.cell(70, 8, field['label'], 1)
        pdf.set_font("Arial", 'B', 10); pdf.cell(35, 8, str(res_val), 1, 0, 'C'); pdf.set_font("Arial", '', 10)
        pdf.cell(35, 8, field['unit'], 1, 0, 'C')
        pdf.cell(50, 8, field['range'], 1, 1, 'C')

    pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone(): st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
                else: st.error("Invalid Login")
else:
    # --- TECHNICIAN PORTAL ---
    if st.session_state.user_role == "Technician":
        ui_header()
        st.subheader("🔬 FBC Result Entry Panel")
        pending = pd.read_sql_query("SELECT * FROM billing WHERE tests LIKE '%FBC%' ORDER BY id DESC", conn)
        
        for i, row in pending.iterrows():
            with st.expander(f"🔴 Enter FBC Results for: {row['ref_no']} - {row['name']}"):
                with st.form(f"fbc_form_{row['ref_no']}"):
                    st.markdown("##### Full Blood Count Components")
                    res_input = {}
                    # Components වෙන වෙනම Input Boxes ලෙස පෙන්වීම
                    for field in FBC_FIELDS:
                        c1, c2, c3 = st.columns([3, 1, 2])
                        res_input[field['label']] = c1.text_input(field['label'], placeholder="Enter value")
                        c2.write(f"\n\n {field['unit']}")
                        c3.info(f"Ref: {field['range']}")
                    
                    if st.form_submit_button("Authorize & Save FBC Report"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)", 
                                  (row['ref_no'], json.dumps(res_input), st.session_state.username, str(date.today())))
                        conn.commit(); st.success("FBC Report Authorized!"); st.rerun()

    # --- SATELLITE PORTAL ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Download Authorized Reports")
        query = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
        auths = pd.read_sql_query(query, conn)
        for i, row in auths.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['name']}** - {row['ref_no']} (Auth by: {row['authorized_by']})")
                pdf_r = create_fbc_report_pdf(row, row['data'], row['authorized_by'])
                c2.download_button("📥 Print FBC Report", pdf_r, f"FBC_{row['ref_no']}.pdf", key=f"p_{row['ref_no']}")

    # --- OTHER ROLES (ADMIN/BILLING) ---
    elif st.session_state.user_role in ["Admin", "Billing"]:
        ui_header()
        st.write(f"Dashboard for {st.session_state.user_role} is Active.")
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

conn.close()
