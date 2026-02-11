import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v15_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
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
    ref = f"LC/{now.strftime('%d/%m/%y')}/{count:02d}"
    return ref

# --- SAFE PDF VIEW LINK ---
def get_pdf_download_link(ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.image("logo.png", 10, 8, 30)
    except:
        pass 

    pdf.set_font("Arial", 'B', 18)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 5, "In front of hospital, Kotuwegoda, Katuwana", ln=True, align='C')
    pdf.cell(200, 5, "Tel: 0773326715", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.cell(200, 2, "--------------------------------------------------------------------------------", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 10, f"Ref No: {ref_no}")
    pdf.cell(100, 10, f"Date: {date.today()}", ln=True, align='R')
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 10, f"Patient Name: {salute} {name}", ln=True)
    pdf.cell(100, 10, f"Age: {age}Y | Gender: {gender}")
    pdf.cell(100, 10, f"Mobile: {mobile}", ln=True, align='R')
    pdf.cell(200, 10, f"Referral Doctor: {doctor}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(200, 10, "Tests / Services Selected:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, tests)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(160, 10, "Full Amount (LKR):", align='R')
    pdf.cell(30, 10, f"{total:,.2f}", ln=True, align='R')
    pdf.cell(160, 10, "Discount (LKR):", align='R')
    pdf.cell(30, 10, f"{discount:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(160, 10, "Final Amount (LKR):", align='R', fill=True)
    pdf.cell(30, 10, f"{final:,.2f}", ln=True, align='R', fill=True)
    
    binary_pdf = pdf.output(dest='S').encode('latin-1')
    base64_pdf = base64.b64encode(binary_pdf).decode('utf-8')
    href = f'<a href="data:application/pdf;base64,{base64_pdf}" target="_blank" style="text-decoration: none; background-color: #28a745; color: white; padding: 12px 24px; border-radius: 5px; font-weight: bold; display: inline-block;">📄 View & Print Invoice (New Tab)</a>'
    return href

# --- UI SETTINGS ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔬 LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing"])
            if st.form_submit_button("Login", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Access Denied!")

else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD (නිවැරදි කරන ලද කොටස) ---
    if st.session_state.user_role == "Admin":
        menu = ["Test Management", "User Management", "Doctor Management", "Sales Reports"]
        choice = st.sidebar.selectbox("Admin Menu", menu)
        
        if choice == "Test Management":
            st.subheader("🧪 Manage Tests")
            with st.form("t_form"):
                tn = st.text_input("Test Name")
                tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp))
                    conn.commit()
                    st.success("Test Saved!")
                    st.rerun()
            
            st.write("### Current Tests")
            t_data = pd.read_sql_query("SELECT * FROM tests", conn)
            for i, r in t_data.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(r['test_name'])
                c2.write(f"LKR {r['price']:,.2f}")
                if c3.button("Delete", key=f"dt_{r['test_name']}"):
                    c.execute("DELETE FROM tests WHERE test_name=?", (r['test_name'],))
                    conn.commit()
                    st.rerun()

        elif choice == "User Management":
            st.subheader("👥 System User Management")
            with st.form("u_form"):
                nu = st.text_input("New Username")
                np = st.text_input("New Password")
                nr = st.selectbox("Assign Role", ["Admin", "Billing"])
                if st.form_submit_button("Create User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr))
                    conn.commit()
                    st.success("User Added!")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        elif choice == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Doctors")
            with st.form("d_form"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,))
                    conn.commit()
                    st.success("Doctor Added!")
            
            st.write("### Registered Doctors")
            d_data = pd.read_sql_query("SELECT * FROM doctors", conn)
            for i, r in d_data.iterrows():
                c1, c2 = st.columns([4, 1])
                c1.write(r['doc_name'])
                if c2.button("Delete", key=f"dd_{r['id']}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (r['id'],))
                    conn.commit()
                    st.rerun()

        elif choice == "Sales Reports":
            st.subheader("📊 Daily Sales Overview")
            d_filter = st.date_input("Select Date", date.today())
            sales_df = pd.read_sql_query(f"SELECT ref_no, name, final_amount, bill_user FROM billing WHERE date='{d_filter}'", conn)
            st.dataframe(sales_df, use_container_width=True)
            st.metric("Total Income", f"LKR {sales_df['final_amount'].sum():,.2f}")

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Bill", "📂 Saved Bills"])
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Rev"])
                p_name = st.text_input("Full Name")
            with col2:
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with col3:
                p_mobile = st.text_input("Mobile")
                docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

            st.markdown("---")
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", test_opt)
            
            full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            discount = st.number_input("Discount (LKR)", 0.0)
            final_amt = full_amt - discount
            st.markdown(f"### Total: **LKR {final_amt:,.2f}**")

            if st.button("Save & Generate Bill", use_container_width=True):
                if p_name and selected:
                    ref = generate_ref_no()
                    test_list = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, test_list, full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success(f"Success! Ref: {ref}")
                    pdf_link = get_pdf_download_link(ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, test_list, full_amt, discount, final_amt)
                    st.markdown(pdf_link, unsafe_allow_html=True)

        with tab2:
            st.subheader("Saved Bills")
            st.dataframe(pd.read_sql_query("SELECT ref_no, name, tests, final_amount, date FROM billing ORDER BY id DESC", conn), use_container_width=True)

conn.close()
