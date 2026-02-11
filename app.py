import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v8_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- PDF GENERATION ---
def create_pdf(bill_id, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, "--------------------------------------------------------", ln=True, align='C')
    pdf.ln(5)
    pdf.cell(100, 10, f"Ref No: LC-{bill_id}")
    pdf.cell(100, 10, f"Date: {date.today()}", ln=True, align='R')
    pdf.cell(200, 10, f"Patient: {salute} {name} ({age}Y/{gender})", ln=True)
    pdf.cell(200, 10, f"Mobile: {mobile} | Doctor: {doctor}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Tests:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 10, tests)
    pdf.ln(10)
    pdf.cell(150, 10, "Full Amount:", align='R')
    pdf.cell(40, 10, f"LKR {total:,.2f}", ln=True, align='R')
    pdf.cell(150, 10, "Discount:", align='R')
    pdf.cell(40, 10, f"LKR {discount:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(150, 10, "Final Amount:", align='R')
    pdf.cell(40, 10, f"LKR {final:,.2f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- UI SETTINGS ---
st.set_page_config(page_title="LIMS v8 - Admin Dashboard Fixed", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔬 LIMS LOGIN")
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
        if st.form_submit_button("Login"):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else: st.error("Invalid Login Details")
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN INTERFACE (FIXED) ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Doctor Management", "Test Management", "Sales Reports"]
        choice = st.sidebar.selectbox("Admin Menu", menu)

        if choice == "User Management":
            st.subheader("👥 System User Control")
            with st.form("add_user"):
                nu, np = st.text_input("New Username"), st.text_input("New Password")
                nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr))
                    conn.commit()
                    st.success("User added!")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        elif choice == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Doctors")
            dn = st.text_input("Doctor Name")
            if st.button("Add Doctor"):
                c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,))
                conn.commit()
                st.success("Doctor saved")
            st.dataframe(pd.read_sql_query("SELECT id, doc_name FROM doctors", conn), use_container_width=True)

        elif choice == "Test Management":
            st.subheader("🧪 Manage Tests & Prices")
            tn = st.text_input("Test Name")
            tp = st.number_input("Price (LKR)")
            if st.button("Save Test"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp))
                conn.commit()
                st.success("Test saved")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

        elif choice == "Sales Reports":
            st.subheader("📊 Business Overview")
            d = st.date_input("Filter by Date", date.today())
            df = pd.read_sql_query(f"SELECT * FROM billing WHERE date='{d}'", conn)
            st.dataframe(df)
            st.metric("Total Sale for Today", f"LKR {df['final_amount'].sum():,.2f}")

    # --- BILLING INTERFACE ---
    elif st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Bill", "📂 Saved Bills"])
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                salute = st.selectbox("Salute", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Name")
                p_age = st.number_input("Age", 0, 120)
            with col2:
                p_gender = st.selectbox("Gender", ["Male", "Female"])
                p_mobile = st.text_input("Mobile")
                docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Doctor", ["Self"] + docs)
            
            st.markdown("---")
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", test_opt)
            
            full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            discount = st.number_input("Discount", 0.0)
            final_amt = full_amt - discount
            st.write(f"### Total: LKR {final_amt:,.2f}")

            if st.button("Generate Bill"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected), full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                bid = c.lastrowid
                pdf_b = create_pdf(bid, salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected), full_amt, discount, final_amt)
                st.download_button("📥 Download PDF", pdf_b, file_name=f"LC-{bid}.pdf")

        with tab2:
            st.subheader("Saved Bills")
            all_b = pd.read_sql_query("SELECT id, name, final_amount, date FROM billing ORDER BY id DESC", conn)
            all_b.insert(0, 'Ref No', all_b['id'].apply(lambda x: f"LC-{x}"))
            st.dataframe(all_b.drop(columns=['id']), use_container_width=True)

conn.close()
