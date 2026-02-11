import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v7_final.db', check_same_thread=False)
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

# --- PDF GENERATION FUNCTION ---
def create_pdf(bill_id, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 10, "--------------------------------------------------------------------------------", ln=True, align='C')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"Ref No: LC-{bill_id}")
    pdf.cell(100, 10, f"Date: {date.today()}", ln=True, align='R')
    
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 10, f"Patient Name: {salute} {name}", ln=True)
    pdf.cell(100, 10, f"Age: {age} | Gender: {gender}")
    pdf.cell(100, 10, f"Mobile: {mobile}", ln=True, align='R')
    pdf.cell(200, 10, f"Referral Doctor: {doctor}", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Tests / Services Selected:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 10, tests)
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(150, 10, "Full Amount:", align='R')
    pdf.cell(40, 10, f"LKR {total:,.2f}", ln=True, align='R')
    pdf.cell(150, 10, "Discount:", align='R')
    pdf.cell(40, 10, f"LKR {discount:,.2f}", ln=True, align='R')
    pdf.set_text_color(0, 128, 0)
    pdf.cell(150, 10, "Final Amount:", align='R')
    pdf.cell(40, 10, f"LKR {final:,.2f}", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI SETTINGS ---
st.set_page_config(page_title="LIMS v7 - PDF & Billing", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN & DASHBOARD LOGIC ---
if not st.session_state.logged_in:
    # (Login code same as before...)
    st.title("🔬 LIMS LOGIN")
    with st.form("login"):
        u, p, r = st.text_input("User"), st.text_input("Pass", type="password"), st.selectbox("Role", ["Admin", "Billing"])
        if st.form_submit_button("Login"):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- BILLING INTERFACE ---
    if st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Registration", "📂 Saved Bills"])

        with tab1:
            # Registration fields (Salute, Name, Age, Gender, Mobile, Doctor, Tests)
            c1, c2, c3 = st.columns(3)
            with c1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Full Name")
            with c2:
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with c3:
                p_mobile = st.text_input("Mobile Number")
                docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_df.iterrows()]
            selected = st.multiselect("Select Tests", test_opt)
            
            full_amt = 0.0
            test_names = []
            for s in selected:
                name_only = s.split(" - LKR")[0]
                price = tests_df[tests_df['test_name'] == name_only]['price'].values[0]
                full_amt += price
                test_names.append(name_only)

            st.write(f"**Full Amount: LKR {full_amt:,.2f}**")
            discount = st.number_input("Discount", 0.0, full_amt)
            final_amt = full_amt - discount
            st.success(f"**Final Amount: LKR {final_amt:,.2f}**")

            if st.button("Save & Generate Bill"):
                if p_name and test_names:
                    c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(test_names), full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    bill_id = c.lastrowid
                    st.success(f"Bill Saved! Ref No: LC-{bill_id}")
                    
                    # PDF Download Button
                    pdf_bytes = create_pdf(bill_id, salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(test_names), full_amt, discount, final_amt)
                    st.download_button(label="📥 Download PDF Bill", data=pdf_bytes, file_name=f"LC-{bill_id}.pdf", mime="application/pdf")
                else: st.error("Incomplete data!")

        with tab2:
            st.subheader("📂 All Saved Bills")
            all_bills = pd.read_sql_query("SELECT id, salute, name, mobile, tests, final_amount, date FROM billing ORDER BY id DESC", conn)
            # Reference number LC ලෙස පෙන්වීමට වෙනස් කිරීම
            all_bills.insert(0, 'Ref No', all_bills['id'].apply(lambda x: f"LC-{x}"))
            st.dataframe(all_bills.drop(columns=['id']), use_container_width=True)

    # --- ADMIN (Doctor & Test Management) ---
    elif st.session_state.user_role == "Admin":
        # (Admin logic for Doctor/Test Management same as before...)
        pass

conn.close()
