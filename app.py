import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v42.db', check_same_thread=False)
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
    # Default Admin
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
            st.image("logo.png", width=130)
        else:
            st.markdown("### 🔬 [LOGO]")
    with col2:
        st.markdown(f"""
            <div style="text-align: left;">
                <h1 style="color: #1E88E5; margin-bottom: 0;">{LAB_NAME}</h1>
                <p style="color: #333; font-weight: bold; margin-top: 5px; font-size: 1.1em;">
                    {LAB_ADDRESS}<br>
                    📱 Tel: {LAB_TEL}
                </p>
            </div>
        """, unsafe_allow_html=True)
    st.write("---")

# --- PDF GENERATOR (LOGO & ADDRESS INCLUDED) ---
def create_lab_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
    pdf.add_page()
    
    # Logo in PDF
    if os.path.exists("logo.png"):
        pdf.image("logo.png", 10, 8, 30)
    
    # Header Details
    pdf.set_font("Arial", 'B', 16)
    pdf.set_x(45)
    pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.set_x(45)
    pdf.cell(0, 5, LAB_ADDRESS, ln=True)
    pdf.set_x(45)
    pdf.cell(0, 5, f"Tel: {LAB_TEL}", ln=True)
    
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Information
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Ref No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.cell(100, 7, f"Doctor: {bill_row['doctor']}")
    pdf.ln(10)

    if is_report:
        # Report Style
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "LABORATORY TEST REPORT", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(80, 8, "Test Parameter", 1); pdf.cell(40, 8, "Result", 1); pdf.cell(70, 8, "Reference Range", 1, ln=True)
        pdf.set_font("Arial", '', 10)
        for param, val in results_dict.items():
            pdf.cell(80, 8, str(param), 1); pdf.cell(40, 8, str(val), 1); pdf.cell(70, 8, "Normal", 1, ln=True)
        pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 5, f"Authorized by: {auth_user}", ln=True, align='R')
    else:
        # Billing Style
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "OFFICIAL INVOICE", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 10, "Test Description", 1); pdf.cell(50, 10, "Price (LKR)", 1, ln=True, align='R')
        pdf.set_font("Arial", '', 10)
        for t in bill_row['tests'].split(", "):
            pdf.cell(140, 8, t, 1); pdf.cell(50, 8, "-", 1, ln=True, align='R')
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 8, "Gross Total:", align='R'); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
        pdf.cell(140, 8, "Discount:", align='R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(140, 10, "NET PAYABLE (LKR):", align='R'); pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')

    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login_panel"):
            st.markdown("<h3 style='text-align:center;'>🔑 System Login</h3>", unsafe_allow_html=True)
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Username, Password or Role Selection")

# 2. MAIN SYSTEM CONTENT
else:
    # Sidebar
    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    st.sidebar.info(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN MODULE ---
    if st.session_state.user_role == "Admin":
        ui_header()
        st.title("🛡️ Administration Dashboard")
        admin_menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "Financial Reports"])
        
        if admin_menu == "User Management":
            st.subheader("Manage System Access")
            with st.form("u_form"):
                nu = st.text_input("Username"); np = st.text_input("Password"); nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Create/Update User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("Success!"); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif admin_menu == "Doctor Management":
            st.subheader("Manage Referral Doctors")
            with st.form("d_form"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Save Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))

        elif admin_menu == "Test Management":
            st.subheader("Manage Tests & Pricing")
            with st.form("t_form"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

        elif admin_menu == "Financial Reports":
            st.subheader("📊 Sales Analysis")
            bills = pd.read_sql_query("SELECT * FROM billing", conn)
            st.dataframe(bills, use_container_width=True)
            st.metric("Total Laboratory Income", f"LKR {bills['final_amount'].sum():,.2f}")

    # --- BILLING MODULE ---
    elif st.session_state.user_role == "Billing":
        ui_header()
        t1, t2 = st.tabs(["New Registration", "Saved Invoices"])
        with t1:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Full Name")
                ay = c1.number_input("Age (Y)", 0, 120, 0); am = c2.number_input("Age (M)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile No")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)
            
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            t_opts = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", t_opts)
            
            gross = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            st.write("---")
            fa, fb, fc = st.columns(3)
            fa.metric("Gross Amount", f"LKR {gross:,.2f}")
            disc = fb.number_input("Discount (LKR)", 0.0)
            net = gross - disc
            fc.markdown(f"<div style='background-color:#e3f2fd; padding:15px; border-radius:10px; border-left: 5px solid #1E88E5;'><p style='margin:0; font-weight:bold;'>NET PAYABLE</p><h2 style='margin:0; color:#0D47A1;'>LKR {net:,.2f}</h2></div>", unsafe_allow_html=True)

            if st.button("SAVE AND GENERATE BILL", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, sal, p_name, ay, am, p_gen, p_mob, p_doc, tnames, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success(f"Invoice Saved! Ref: {ref}"); st.rerun()

        with t2:
            hist = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in hist.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']} ({row['date']})"):
                    st.write(f"Tests: {row['tests']} | Final Price: LKR {row['final_amount']:,.2f}")
                    pdf_b = create_lab_pdf(row, is_report=False)
                    st.download_button("📥 Download Invoice PDF", pdf_b, f"Bill_{row['ref_no']}.pdf", key=f"bill_{row['id']}")

    # --- TECHNICIAN MODULE ---
    elif st.session_state.user_role == "Technician":
        ui_header()
        st.title("🔬 Technician Portal")
        pending = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        for i, row in pending.iterrows():
            with st.expander(f"📝 Result Entry: {row['ref_no']} - {row['name']}"):
                tests = row['tests'].split(", "); res_data = {}
                with st.form(f"tech_f_{row['ref_no']}"):
                    cols = st.columns(3)
                    for idx, t in enumerate(tests):
                        res_data[t] = cols[idx%3].text_input(t)
                    if st.form_submit_button("Authorize Report"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today())))
                        conn.commit(); st.success(f"Report Authorized for {row['name']}!"); st.rerun()

    # --- SATELLITE MODULE ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Authorized Reports - Download & Print")
        query = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
        auths = pd.read_sql_query(query, conn)
        for i, row in auths.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**Patient Name:** {row['name']} | **Ref:** {row['ref_no']} | **Auth by:** {row['authorized_by']}")
                pdf_r = create_lab_pdf(row, json.loads(row['data']), row['authorized_by'], is_report=True)
                c2.download_button("📥 Print Report", pdf_r, f"Report_{row['ref_no']}.pdf", key=f"sat_{row['ref_no']}")

conn.close()
