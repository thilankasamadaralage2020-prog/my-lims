import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v19.db', check_same_thread=False)
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

def generate_ref_no():
    today_str = str(date.today())
    c.execute("SELECT COUNT(*) FROM billing WHERE date = ?", (today_str,))
    count = c.fetchone()[0] + 1
    now = datetime.now()
    return f"LC/{now.strftime('%d/%m/%y')}/{count:02d}"

# --- PDF GENERATION (DOWNLOAD VERSION) ---
def create_pdf_bytes(ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
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
    pdf.cell(200, 10, "Tests / Services Selected:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, tests)
    pdf.ln(10)
    
    pdf.cell(160, 10, "Full Amount (LKR):", align='R'); pdf.cell(30, 10, f"{total:,.2f}", ln=True, align='R')
    pdf.cell(160, 10, "Discount (LKR):", align='R'); pdf.cell(30, 10, f"{discount:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 12); pdf.set_fill_color(240, 240, 240)
    pdf.cell(160, 10, "Final Amount (LKR):", align='R', fill=True); pdf.cell(30, 10, f"{final:,.2f}", ln=True, align='R', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.info("Logo Space")
        st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Login")
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.user_role == "Admin":
        menu = st.sidebar.selectbox("Admin Menu", ["Test Management", "User Management", "Doctor Management"])
        if menu == "User Management":
            st.subheader("👥 Manage Users")
            with st.form("u"):
                nu, np = st.text_input("User"), st.text_input("Pass")
                nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Create"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("Created")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)
        # (Other Admin options here...)

    elif st.session_state.user_role == "Billing":
        st.subheader("📝 New Bill Registration")
        c1, c2, c3 = st.columns(3)
        with c1: salute = st.selectbox("Salute", ["Mr", "Mrs", "Miss", "Rev"]); p_name = st.text_input("Name")
        with c2: p_age = st.number_input("Age", 0, 120); p_gender = st.selectbox("Gender", ["Male", "Female"])
        with c3: p_mob = st.text_input("Mobile"); docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist(); p_doc = st.selectbox("Doctor", ["Self"] + docs)

        st.write("---")
        tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
        test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
        selected = st.multiselect("Select Tests (Keyboard Arrow + Enter)", test_opt)
        
        full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
        discount = st.number_input("Discount (LKR)", 0.0)
        final_amt = full_amt - discount
        
        st.metric("Final Amount", f"LKR {final_amt:,.2f}")

        if st.button("Generate & Save Bill", use_container_width=True):
            if p_name and selected:
                ref = generate_ref_no()
                test_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                c.execute("INSERT INTO billing (ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (ref, salute, p_name, p_age, p_gender, p_mob, p_doc, test_names, full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success(f"Bill Saved: {ref}")
                
                # --- NEW DOWNLOAD BUTTON (FIXES BLANK PAGE ISSUE) ---
                pdf_data = create_pdf_bytes(ref, salute, p_name, p_age, p_gender, p_mob, p_doc, test_names, full_amt, discount, final_amt)
                st.download_button(
                    label="📥 Click Here to Download & Print Bill",
                    data=pdf_data,
                    file_name=f"Invoice_{ref.replace('/', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else: st.error("Please fill details")

conn.close()
