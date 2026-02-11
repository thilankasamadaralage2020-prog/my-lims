import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_v18_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Default Admin Account
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- REFERENCE NUMBER GENERATOR ---
def generate_ref_no():
    today_str = str(date.today())
    c.execute("SELECT COUNT(*) FROM billing WHERE date = ?", (today_str,))
    count = c.fetchone()[0] + 1
    now = datetime.now()
    return f"LC/{now.strftime('%d/%m/%y')}/{count:02d}"

# --- PDF GENERATION FUNCTION ---
def get_pdf_link(ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo.png", 10, 8, 33)
    except: pass 
    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 5, "In front of hospital, Kotuwegoda, Katuwana", ln=True, align='C')
    pdf.cell(200, 5, "Tel: 0773326715", ln=True, align='C')
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.cell(200, 2, "-"*80, ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, f"Ref No: {ref_no}")
    pdf.cell(100, 10, f"Date: {date.today()}", ln=True, align='R')
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, f"Patient Name: {salute} {name}", ln=True)
    pdf.cell(200, 8, f"Age/Gender: {age}Y / {gender}", ln=True)
    pdf.cell(200, 8, f"Mobile: {mobile}", ln=True)
    pdf.cell(200, 8, f"Referral Doctor: {doctor}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(200, 10, "Tests / Services:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, tests)
    pdf.ln(10)
    pdf.cell(160, 10, "Full Amount (LKR):", align='R'); pdf.cell(30, 10, f"{total:,.2f}", ln=True, align='R')
    pdf.cell(160, 10, "Discount (LKR):", align='R'); pdf.cell(30, 10, f"{discount:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(240, 240, 240)
    pdf.cell(160, 10, "Final Amount (LKR):", align='R', fill=True); pdf.cell(30, 10, f"{final:,.2f}", ln=True, align='R', fill=True)
    
    binary_pdf = pdf.output(dest='S').encode('latin-1')
    b64 = base64.b64encode(binary_pdf).decode('utf-8')
    return f'<a href="data:application/pdf;base64,{b64}" target="_blank" style="text-decoration:none; background-color:#28a745; color:white; padding:12px 24px; border-radius:5px; font-weight:bold; display:inline-block; width:100%; text-align:center;">📄 View & Print Invoice (New Tab)</a>'

# --- UI SETTINGS ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # --- LOGO ON LOGIN PAGE ---
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.info("Logo space (Upload logo.png to GitHub)")
        
        st.markdown("<h2 style='text-align: center; color: #2E86C1;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            # All 4 Roles Added Here
            r = st.selectbox("Login Role", ["Admin", "Billing", "Technician", "Satellite"])
            
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else:
                    st.error("Invalid Login Details")

else:
    # --- SIDEBAR ---
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.write(f"**Role:** {st.session_state.user_role}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        choice = st.sidebar.selectbox("Admin Menu", ["Test Management", "User Management", "Doctor Management", "Sales Reports"])
        
        if choice == "Test Management":
            st.subheader("🧪 Manage Laboratory Tests")
            with st.form("t_form"):
                tn = st.text_input("Test Name")
                tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            
            st.write("---")
            t_data = pd.read_sql_query("SELECT * FROM tests", conn)
            for i, row in t_data.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(row['test_name'])
                c2.write(f"LKR {row['price']:,.2f}")
                if c3.button("Delete", key=f"del_{row['test_name']}"):
                    c.execute("DELETE FROM tests WHERE test_name=?", (row['test_name'],)); conn.commit(); st.rerun()

        elif choice == "User Management":
            st.subheader("👥 System User Management")
            with st.form("u_form"):
                nu = st.text_input("New Username")
                np = st.text_input("New Password")
                nr = st.selectbox("Assign Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Create User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("User Created Successfully")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        elif choice == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Referral Doctors")
            with st.form("d_form"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT doc_name FROM doctors", conn), use_container_width=True)

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Registration", "📂 Saved Bills"])
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Rev"])
                p_name = st.text_input("Patient Full Name")
            with col2:
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with col3:
                p_mobile = st.text_input("Mobile Number")
                docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

            st.markdown("---")
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            # Arrow key navigation enabled
            selected = st.multiselect("Select Tests (Use Arrow keys + Enter)", test_opt)
            
            # CALCULATIONS
            full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            
            st.markdown("### Payment Summary")
            ca, cb, cc = st.columns(3)
            with ca: st.info(f"Full Amount: LKR {full_amt:,.2f}")
            with cb: discount = st.number_input("Discount (LKR)", min_value=0.0)
            with cc: 
                final_amt = full_amt - discount
                st.success(f"Final Amount: LKR {final_amt:,.2f}")

            if st.button("Generate & Save Invoice", use_container_width=True):
                if p_name and selected:
                    ref = generate_ref_no()
                    test_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, test_names, full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.markdown(get_pdf_link(ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, test_names, full_amt, discount, final_amt), unsafe_allow_html=True)
                else:
                    st.error("Please fill patient details and select tests.")

        with tab2:
            st.subheader("History of Bills")
            st.dataframe(pd.read_sql_query("SELECT ref_no, name, tests, final_amount, date FROM billing ORDER BY id DESC", conn), use_container_width=True)

    # --- TECHNICIAN DASHBOARD ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 Technician Laboratory Workspace")
        st.info("The system is ready for Report Entry Module.")

    # --- SATELLITE DASHBOARD ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("🛰️ Satellite Center Portal")
        st.info("Access restricted to center-specific data.")

conn.close()
