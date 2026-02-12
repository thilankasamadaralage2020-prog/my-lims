import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v38.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LAB DETAILS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- UI LOGO & HEADER ---
def ui_header():
    st.markdown(f"""
        <div style="text-align: center; background-color: #ffffff; padding: 25px; border-radius: 15px; border: 3px solid #1E88E5; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <h1 style="color: #1E88E5; margin-bottom: 0;">🔬 {LAB_NAME}</h1>
            <p style="color: #333; font-weight: bold; margin-top: 5px; line-height: 1.5;">
                {LAB_ADDRESS}<br>
                📱 Tel: {LAB_TEL}
            </p>
        </div>
        <br>
    """, unsafe_allow_html=True)

# --- BILL PDF GENERATOR ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(30, 136, 229)
    pdf.cell(0, 10, LAB_NAME.upper(), ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, LAB_ADDRESS, ln=True, align='C')
    pdf.cell(0, 5, f"Tel: {LAB_TEL}", ln=True, align='C')
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Info
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Invoice: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)
    
    # Table
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 10, "Test Description", border=1); pdf.cell(50, 10, "Amount (LKR)", border=1, ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    for t in bill_row['tests'].split(", "):
        pdf.cell(140, 8, t, border=1); pdf.cell(50, 8, "-", border=1, ln=True, align='R')
    
    # Total
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Gross Total:", align='R'); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "Discount:", align='R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "NET AMOUNT (LKR):", align='R'); pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    
    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("secure_login"):
            st.markdown("<h3 style='text-align:center;'>🔑 Login Panel</h3>", unsafe_allow_html=True)
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            # Reception ඉවත් කර Satellite එක් කර ඇත
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("SYSTEM LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Access Denied: Invalid Credentials")

# 2. SYSTEM CONTENT
else:
    st.sidebar.markdown(f"<h2 style='color:#1E88E5;'>🔬 Life Care</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"**User:** {st.session_state.username}\n\n**Role:** {st.session_state.user_role}")
    if st.sidebar.button("System Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        st.title("🛡️ Admin Dashboard")
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "Financial Reports"])
        
        if menu == "User Management":
            with st.form("u_add"):
                nu = st.text_input("Username"); np = st.text_input("Password")
                nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("User Updated"); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif menu == "Doctor Management":
            st.subheader("Manage Doctors")
            with st.form("d_add"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))

        elif menu == "Test Management":
            st.subheader("Manage Tests & Prices")
            with st.form("t_add"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price", min_value=0.0)
                if st.form_submit_button("Save"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

        elif menu == "Financial Reports":
            st.subheader("📊 Sales History")
            bills = pd.read_sql_query("SELECT ref_no, name, total, discount, final_amount, date FROM billing", conn)
            st.dataframe(bills, use_container_width=True)
            st.metric("Total Income", f"LKR {bills['final_amount'].sum():,.2f}")

    # --- BILLING / SATELLITE ---
    elif st.session_state.user_role in ["Billing", "Satellite"]:
        ui_header()
        t1, t2 = st.tabs(["📝 Billing", "📂 Saved Bills"])
        
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
            st.write("---")
            fa, fb, fc = st.columns(3)
            fa.metric("Gross Total", f"LKR {gross:,.2f}")
            disc = fb.number_input("Discount (LKR)", 0.0)
            net = gross - disc
            fc.markdown(f"<div style='background-color:#e3f2fd; padding:15px; border-radius:10px; border-left: 5px solid #1E88E5;'><p style='margin:0; color:#1E88E5; font-weight:bold;'>NET PAYABLE</p><h2 style='margin:0; color:#0D47A1;'>LKR {net:,.2f}</h2></div>", unsafe_allow_html=True)

            if st.button("SAVE BILL", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, sal, p_name, ay, am, p_gen, p_mob, p_doc, tnames, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success(f"Saved: {ref}"); st.rerun()

        with t2:
            history = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in history.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']}"):
                    st.write(f"Tests: {row['tests']} | **Final: LKR {row['final_amount']:,.2f}**")
                    pdf = create_bill_pdf(row)
                    st.download_button("📥 Download PDF", pdf, f"Bill_{row['ref_no']}.pdf", key=f"d_{row['id']}")

conn.close()
