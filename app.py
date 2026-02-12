import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v41.db', check_same_thread=False)
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

# --- LAB DETAILS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- UI HEADER WITH LOGO ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
    with col2:
        st.markdown(f"""
            <div style="text-align: left;">
                <h1 style="color: #1E88E5; margin-bottom: 0;">{LAB_NAME}</h1>
                <p style="color: #333; font-weight: bold; margin-top: 5px;">
                    {LAB_ADDRESS}<br>
                    📱 Tel: {LAB_TEL}
                </p>
            </div>
        """, unsafe_allow_html=True)
    st.write("---")

# --- REPORT PDF GENERATOR ---
def create_report_pdf(bill_row, results_dict, auth_user):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 25)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.set_x(40); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 9); pdf.set_x(40); pdf.cell(0, 5, LAB_ADDRESS, ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Ref: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, "LABORATORY TEST REPORT", ln=True, align='C'); pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, "Test Parameter", 1); pdf.cell(40, 8, "Result", 1); pdf.cell(70, 8, "Reference Range", 1, ln=True)
    
    pdf.set_font("Arial", '', 10)
    for param, val in results_dict.items():
        pdf.cell(80, 8, str(param), 1); pdf.cell(40, 8, str(val), 1); pdf.cell(70, 8, "Normal", 1, ln=True)
        
    pdf.ln(20); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 5, f"Authorized by: {auth_user}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login_form"):
            st.subheader("🔑 Secure Access")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Username or Password")

# 2. LOGGED IN SYSTEM
else:
    st.sidebar.markdown(f"### Welcome, {st.session_state.username}")
    st.sidebar.text(f"Access Level: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        st.title("🛡️ Administration Dashboard")
        admin_menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "Financial Reports"])
        
        if admin_menu == "User Management":
            st.subheader("User Accounts")
            with st.form("u_add"):
                nu = st.text_input("New Username"); np = st.text_input("Password"); nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Save User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("User Added/Updated"); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif admin_menu == "Doctor Management":
            st.subheader("Referral Doctors")
            with st.form("d_add"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))

        elif admin_menu == "Test Management":
            st.subheader("Manage Lab Tests")
            with st.form("t_add"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price (LKR)", 0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

        elif admin_menu == "Financial Reports":
            st.subheader("📊 Sales Summary")
            all_bills = pd.read_sql_query("SELECT * FROM billing", conn)
            st.dataframe(all_bills)
            st.metric("Total Income", f"LKR {all_bills['final_amount'].sum():,.2f}")

    # --- BILLING PORTAL ---
    elif st.session_state.user_role == "Billing":
        ui_header()
        t1, t2 = st.tabs(["New Registration", "Saved Bills"])
        with t1:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Name")
                ay = c1.number_input("Age (Y)", 0, 120, 0); am = c2.number_input("Age (M)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)
            
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            t_opts = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", t_opts)
            gross = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            disc = st.number_input("Discount", 0.0); net = gross - disc
            st.write(f"### Net Amount: LKR {net:,.2f}")
            if st.button("Save Bill"):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, sal, p_name, ay, am, p_gen, p_mob, p_doc, tnames, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success("Bill Saved!"); st.rerun()

    # --- TECHNICIAN PORTAL ---
    elif st.session_state.user_role == "Technician":
        st.title("🔬 Technician Portal")
        pending = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        for i, row in pending.iterrows():
            with st.expander(f"📝 {row['ref_no']} - {row['name']}"):
                tests = row['tests'].split(", "); res_data = {}
                with st.form(f"f_{row['ref_no']}"):
                    cols = st.columns(3)
                    for idx, t in enumerate(tests):
                        res_data[t] = cols[idx%3].text_input(t)
                    if st.form_submit_button("Authorize Report"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today())))
                        conn.commit(); st.success("Authorized!")

    # --- SATELLITE PORTAL ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Authorized Reports")
        query = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref"
        auths = pd.read_sql_query(query, conn)
        for i, row in auths.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{row['name']}** ({row['ref_no']}) - Authorized by {row['authorized_by']}")
                pdf = create_report_pdf(row, json.loads(row['data']), row['authorized_by'])
                c2.download_button("📥 Print", pdf, f"Report_{row['ref_no']}.pdf", key=f"s_{row['ref_no']}")

conn.close()
