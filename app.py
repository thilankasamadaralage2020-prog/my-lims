import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v37.db', check_same_thread=False)
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

# --- UI LOGO & HEADER ---
def ui_header():
    st.markdown("""
        <div style="text-align: center; background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 2px solid #1E88E5; margin-bottom: 25px;">
            <h1 style="color: #1E88E5; margin-bottom: 0;">🔬 LIFE CARE LABORATORY</h1>
            <p style="color: #333; font-weight: bold; margin-top: 5px;">NO 10, MAIN STREET, LOCATION CITY<br>Tel: 011 2XXXXXX / 071 XXXXXXX</p>
        </div>
    """, unsafe_allow_html=True)

# --- BILL PDF GENERATOR ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(0, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "N0 10, Main Street, Location, City | Tel: 011 2XXXXXX", ln=True, align='C')
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Ref: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 10, "Description", border=1); pdf.cell(50, 10, "Amount (LKR)", border=1, ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    for t in bill_row['tests'].split(", "):
        pdf.cell(140, 8, t, border=1); pdf.cell(50, 8, "-", border=1, ln=True, align='R')
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Gross Total:", align='R'); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "Discount:", align='R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "NET AMOUNT:", align='R'); pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login"):
            st.subheader("🔑 Secure Login")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Reception"])
            if st.form_submit_button("SYSTEM LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Credentials")

# 2. SYSTEM CONTENT
else:
    st.sidebar.markdown(f"### 👤 {st.session_state.username}")
    st.sidebar.text(f"Access Level: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN MODULE ---
    if st.session_state.user_role == "Admin":
        st.title("🛡️ Administrator Portal")
        # Sidebar Menu for Admin
        admin_menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "Financial Reports"])
        
        if admin_menu == "User Management":
            st.subheader("Manage System Users")
            with st.form("u_add"):
                nu = st.text_input("Username"); np = st.text_input("Password"); nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Reception"])
                if st.form_submit_button("Add New User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif admin_menu == "Doctor Management":
            st.subheader("Manage Referral Doctors")
            with st.form("d_add"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Save Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT id, doc_name FROM doctors", conn))

        elif admin_menu == "Test Management":
            st.subheader("Manage Laboratory Tests")
            with st.form("t_add"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

        elif admin_menu == "Financial Reports":
            st.subheader("📊 Sales & Billing History")
            bills_df = pd.read_sql_query("SELECT ref_no, name, tests, total, discount, final_amount, date FROM billing ORDER BY id DESC", conn)
            st.dataframe(bills_df, use_container_width=True)
            st.write(f"**Total Revenue: LKR {bills_df['final_amount'].sum():,.2f}**")

    # --- BILLING & RECEPTION MODULE ---
    elif st.session_state.user_role in ["Billing", "Reception"]:
        ui_header()
        tab_new, tab_saved = st.tabs(["New Registration", "Saved Invoices"])
        
        with tab_new:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                salute = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Full Name")
                ay = c1.number_input("Age (Y)", 0, 120, 0); am = c2.number_input("Age (M)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile No")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)

            # Financial Section
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            t_opts = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Lab Tests", t_opts)
            
            gross = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            
            st.markdown("---")
            fa, fb, fc = st.columns(3)
            fa.metric("Gross Amount", f"LKR {gross:,.2f}")
            disc = fb.number_input("Discount (LKR)", min_value=0.0, step=50.0)
            net = gross - disc
            fc.markdown(f"<div style='background-color:#e8f5e9; padding:15px; border-radius:10px; border-left: 5px solid green;'><p style='margin:0;'>NET PAYABLE</p><h2 style='margin:0; color:green;'>LKR {net:,.2f}</h2></div>", unsafe_allow_html=True)

            if st.button("SAVE AND GENERATE BILL", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, tnames, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success(f"Bill Saved: {ref}"); st.rerun()

        with tab_saved:
            st.subheader("Invoice History")
            history = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in history.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']} ({row['date']})"):
                    st.write(f"Tests: {row['tests']} | Doctor: {row['doctor']}")
                    st.write(f"**Final Amount: LKR {row['final_amount']:,.2f}**")
                    pdf_file = create_bill_pdf(row)
                    st.download_button("📥 Download Invoice PDF", pdf_file, f"Bill_{row['ref_no']}.pdf", "application/pdf", key=f"bill_{row['id']}")

    # --- TECHNICIAN MODULE ---
    elif st.session_state.user_role == "Technician":
        st.header("🔬 Lab Technician - Report Entry")
        st.info("Pending FBC and other reports will be displayed here.")

conn.close()
