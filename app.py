import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v9_ref_logic.db', check_same_thread=False)
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
    # අද දිනට අදාළව දැනට පද්ධතියේ ඇති බිල්පත් ගණන බැලීම
    c.execute("SELECT COUNT(*) FROM billing WHERE date = ?", (today_str,))
    count = c.fetchone()[0] + 1
    
    now = datetime.now()
    # Format: LC/Date/Month/Year(last 2)/Serial
    ref = f"LC/{now.strftime('%d/%m/%y')}/{count:02d}"
    return ref

# --- PDF GENERATION ---
def create_pdf(ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, f"Ref No: {ref_no}")
    pdf.cell(100, 10, f"Date: {date.today()}", ln=True, align='R')
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 10, f"Patient: {salute} {name} ({age}Y/{gender})", ln=True)
    pdf.cell(200, 10, f"Referral Doctor: {doctor}", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(200, 10, "Tests List:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 8, tests)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(160, 10, "Full Amount (LKR):", align='R')
    pdf.cell(30, 10, f"{total:,.2f}", ln=True, align='R')
    pdf.cell(160, 10, "Discount (LKR):", align='R')
    pdf.cell(30, 10, f"{discount:,.2f}", ln=True, align='R')
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(160, 10, "Final Amount (LKR):", align='R', fill=True)
    pdf.cell(30, 10, f"{final:,.2f}", ln=True, align='R', fill=True)
    return pdf.output(dest='S').encode('latin-1')

# --- UI SETTINGS ---
st.set_page_config(page_title="LIMS v9 - Smart Ref & Billing", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 LIMS LOGIN")
    with st.form("login"):
        u = st.text_input("User")
        p = st.text_input("Pass", type="password")
        r = st.selectbox("Role", ["Admin", "Billing"])
        if st.form_submit_button("Login"):
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

    if st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Registration", "📂 Saved Bills"])
        
        with tab1:
            st.subheader("Patient Registration")
            col1, col2, col3 = st.columns(3)
            with col1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Full Name")
            with col2:
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with col3:
                p_mobile = st.text_input("Mobile Number")
                docs = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

            st.markdown("---")
            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_df.iterrows()]
            selected = st.multiselect("Select Tests", test_opt)
            
            # --- CALCULATIONS (නිවැරදි කරන ලදී) ---
            full_amt = 0.0
            test_names = []
            for s in selected:
                name_part = s.split(" - LKR")[0]
                price_part = float(s.split(" - LKR")[-1].replace(',', ''))
                full_amt += price_part
                test_names.append(name_part)

            st.markdown("### Payment Summary")
            calc_col1, calc_col2, calc_col3 = st.columns(3)
            with calc_col1:
                st.info(f"**Full Amount: LKR {full_amt:,.2f}**")
            with calc_col2:
                discount = st.number_input("Discount (LKR)", 0.0, step=10.0)
            with calc_col3:
                final_amt = full_amt - discount
                st.success(f"**Final Amount: LKR {final_amt:,.2f}**")

            if st.button("Confirm & Generate Bill", use_container_width=True):
                if p_name and test_names:
                    new_ref = generate_ref_no()
                    c.execute('''INSERT INTO billing 
                        (ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (new_ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(test_names), full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success(f"Saved! Ref: {new_ref}")
                    
                    pdf_bytes = create_pdf(new_ref, salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(test_names), full_amt, discount, final_amt)
                    st.download_button("📥 Download PDF Bill", pdf_bytes, file_name=f"{new_ref.replace('/','-')}.pdf")
                else: st.error("Please enter name and select tests.")

        with tab2:
            st.subheader("All Saved Bills")
            bills_df = pd.read_sql_query("SELECT ref_no, name, tests, final_amount, date FROM billing ORDER BY id DESC", conn)
            st.dataframe(bills_df, use_container_width=True)

    elif st.session_state.user_role == "Admin":
        # (Admin Code for Doctor/Test Management as before)
        pass

conn.close()
