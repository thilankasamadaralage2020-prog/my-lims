import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v35.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Default Admin එකතු කිරීම
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- BILL PDF GENERATOR WITH LOGO & ADDRESS ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    
    # Logo එකක් ලෙස Placeholder එකක් (ඔබට 'logo.png' තිබේ නම් pdf.image('logo.png', 10, 8, 33) ලෙස එක් කළ හැක)
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(0, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "N0 10, Main Street, Location, City", ln=True, align='C')
    pdf.cell(0, 5, "Tel: 011 2XXXXXX / 071 XXXXXXX", ln=True, align='C')
    pdf.cell(0, 5, "Email: lifecarelab@gmail.com", ln=True, align='C')
    pdf.ln(5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # බෙදුම් රේඛාව
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "OFFICIAL PATIENT INVOICE", ln=True, align='C')
    pdf.ln(5)
    
    # රෝගී විස්තර
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Patient Name: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(100, 7, f"Invoice No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.cell(100, 7, f"Age/Gender: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(100, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.cell(100, 7, f"Referral: {bill_row['doctor']}")
    pdf.cell(100, 7, f"Billed By: {bill_row['bill_user']}", ln=True, align='R')
    pdf.ln(10)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 10, "Description of Test", border=1)
    pdf.cell(50, 10, "Amount (LKR)", border=1, ln=True, align='R')
    
    # Tests
    pdf.set_font("Arial", '', 10)
    test_list = bill_row['tests'].split(", ")
    for test in test_list:
        pdf.cell(140, 8, test, border=1)
        pdf.cell(50, 8, "-", border=1, ln=True, align='R')
        
    pdf.ln(5)
    
    # මුදල් විස්තර
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Gross Total:", align='R')
    pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "Discount Given:", align='R')
    pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(140, 10, "NET AMOUNT (LKR):", align='R')
    pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    
    pdf.ln(20)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 10, "Thank you for choosing Life Care Laboratory. This is a computer generated invoice.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

# Logo for Login Page (Placeholder Image)
def show_logo():
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🔬 LIFE CARE LABORATORY</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Quality Health Care Through Accurate Diagnostics</p>", unsafe_allow_html=True)
    st.write("---")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    show_logo()
    with st.container():
        left, mid, right = st.columns([1, 2, 1])
        with mid:
            with st.form("login_form"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                # User roles 4 ක් (Admin, Billing, Technician, Reception)
                r = st.selectbox("Select User Role", ["Admin", "Billing", "Technician", "Reception"])
                if st.form_submit_button("SYSTEM LOGIN", use_container_width=True):
                    c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                    if c.fetchone():
                        st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                        st.rerun()
                    else:
                        st.error("Access Denied: Invalid Credentials")

# 2. LOGGED IN SYSTEM
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.info(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("System Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN MANAGEMENT ---
    if st.session_state.user_role == "Admin":
        st.header("⚙️ Admin Control Panel")
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "Financial Reports"])
        
        if menu == "User Management":
            st.subheader("System User Roles")
            with st.form("add_user"):
                nu = st.text_input("Username")
                np = st.text_input("Password")
                nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Reception"])
                if st.form_submit_button("Create Account"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr))
                    conn.commit(); st.success("User Added!"); st.rerun()

        elif menu == "Test Management":
            st.subheader("Manage Lab Tests & Prices")
            with st.form("add_test"):
                tn = st.text_input("Test Name")
                tp = st.number_input("Test Price (LKR)", min_value=0.0)
                if st.form_submit_button("Add to Menu"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp))
                    conn.commit(); st.rerun()
            # පවතින tests පෙන්වීම
            test_list = pd.read_sql_query("SELECT * FROM tests", conn)
            st.table(test_list)

        elif menu == "Doctor Management":
            st.subheader("Manage Referral Doctors")
            with st.form("add_doc"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Save Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,))
                    conn.commit(); st.rerun()

    # --- BILLING & RECEPTION ---
    elif st.session_state.user_role in ["Billing", "Reception"]:
        st.header("📝 Registration & Billing Department")
        tab_reg, tab_history = st.tabs(["New Patient Registration", "Saved Invoices"])
        
        with tab_reg:
            with st.container(border=True):
                st.write("### Patient Information")
                c1, c2 = st.columns(2)
                salute = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Full Name")
                ay = c1.number_input("Age (Years)", 0, 120, 0)
                am = c2.number_input("Age (Months)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"])
                p_mob = c2.text_input("Mobile Number")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

            st.write("### Test Selection & Payment")
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            test_options = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected_tests = st.multiselect("Search and Select Tests", test_options)
            
            # ගණනය කිරීම් (Calculation Section)
            full_bill = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected_tests])
            
            # මුදල් විස්තර පෙන්වන කොටස
            st.write("---")
            col_a, col_b, col_c = st.columns(3)
            col_a.markdown(f"**Gross Amount:** \n### LKR {full_bill:,.2f}")
            discount_val = col_b.number_input("Enter Discount (LKR)", min_value=0.0, step=10.0)
            final_bill = full_bill - discount_val
            col_c.markdown(f"**Net Amount:** \n### <span style='color:green;'>LKR {final_bill:,.2f}</span>", unsafe_allow_html=True)

            if st.button("SAVE AND GENERATE BILL", use_container_width=True):
                if p_name and selected_tests:
                    ref_id = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    test_names = ", ".join([s.split(" - LKR")[0] for s in selected_tests])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref_id, salute, p_name, ay, am, p_gen, p_mob, p_doc, test_names, full_bill, discount_val, final_bill, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success(f"Invoice Saved Successfully! Ref: {ref_id}")
                    st.balloons()
                else:
                    st.error("Please fill Name and Select Tests!")

        with tab_history:
            st.subheader("📂 Saved Invoice History")
            hist = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in hist.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']} ({row['date']})"):
                    st.write(f"**Mobile:** {row['mobile']} | **Doctor:** {row['doctor']}")
                    st.write(f"**Tests:** {row['tests']}")
                    st.markdown(f"**Total Paid: LKR {row['final_amount']:,.2f}**")
                    
                    # PDF Download
                    pdf_file = create_bill_pdf(row)
                    st.download_button(
                        label="📥 Download Invoice PDF",
                        data=pdf_file,
                        file_name=f"Invoice_{row['ref_no']}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['id']}"
                    )

    # --- TECHNICIAN SECTION ---
    elif st.session_state.user_role == "Technician":
        st.header("🔬 Technician Portal - Report Entry")
        st.info("Pending reports will appear here.")
        # FBC Logic and Ranges go here...

conn.close()
