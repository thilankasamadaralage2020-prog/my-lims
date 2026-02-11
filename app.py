import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v33.db', check_same_thread=False)
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

# --- BILL PDF GENERATOR ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 5, "N0 10, Main Street, Location | Tel: 0112XXXXXX", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "PATIENT INVOICE", ln=True, border='B')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(100, 7, f"Ref No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.cell(100, 7, f"Age: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(100, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Test Description", border=1)
    pdf.cell(50, 8, "Amount (LKR)", border=1, ln=True, align='R')
    
    pdf.set_font("Arial", '', 10)
    for test in bill_row['tests'].split(", "):
        pdf.cell(140, 8, test, border=1)
        pdf.cell(50, 8, "-", border=1, ln=True, align='R')
        
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Total Amount:", align='R')
    pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "Discount:", align='R')
    pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Final Amount (LKR):", align='R')
    pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
    with st.form("login_box"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
        if st.form_submit_button("LOGIN", use_container_width=True):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else: st.error("Access Denied")
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        st.header("⚙️ Admin Dashboard")
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management", "View Saved Bills"])
        
        if menu == "User Management":
            st.subheader("👥 User Management")
            with st.form("admin_u"):
                un = st.text_input("New Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            
            st.write("Current Users:")
            users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            for i, row in users_df.iterrows():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(row['username']); c2.write(row['role'])
                if row['username'] != st.session_state.username:
                    if c3.button("🗑️", key=f"u_{row['username']}"):
                        c.execute("DELETE FROM users WHERE username=?", (row['username'],)); conn.commit(); st.rerun()

        elif menu == "Doctor Management":
            st.subheader("👨‍⚕️ Doctor Management")
            with st.form("admin_d"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            
            docs_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            for i, row in docs_df.iterrows():
                c1, c2 = st.columns([5, 1])
                c1.write(row['doc_name'])
                if c2.button("🗑️", key=f"d_{row['id']}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (row['id'],)); conn.commit(); st.rerun()

        elif menu == "Test Management":
            st.subheader("🧪 Test Management")
            with st.form("admin_t"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            
            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            for i, row in tests_df.iterrows():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(row['test_name']); c2.write(f"LKR {row['price']:,.2f}")
                if c3.button("🗑️", key=f"t_{row['test_name']}"):
                    c.execute("DELETE FROM tests WHERE test_name=?", (row['test_name'],)); conn.commit(); st.rerun()

        elif menu == "View Saved Bills":
            st.subheader("📂 All Saved Bills")
            all_bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            st.dataframe(all_bills)

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        st.header("📝 Billing Department")
        tab1, tab2 = st.tabs(["New Registration", "Saved Bills"])
        
        with tab1:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                salute = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Name")
                ay = c1.number_input("Age (Y)", 0, 120, 0); am = c2.number_input("Age (M)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)

            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            t_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", t_opt)
            
            total = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            disc = st.number_input("Discount", 0.0); final = total - disc
            st.success(f"Final Amount: LKR {final:,.2f}")

            if st.button("Save Bill", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    t_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, t_names, total, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.balloons(); st.rerun()

        with tab2:
            st.subheader("Saved Bills")
            saved_bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in saved_bills.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']}"):
                    st.write(f"Tests: {row['tests']}")
                    pdf_data = create_bill_pdf(row)
                    st.download_button("📥 Download PDF", pdf_data, f"Bill_{row['ref_no']}.pdf", "application/pdf", key=f"bill_{row['id']}")

conn.close()
