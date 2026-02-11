import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v36.db', check_same_thread=False)
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

# --- REFERENCE RANGES LOGIC ---
def get_full_fbc_ranges(age_y, gender):
    if age_y < 5:
        return {"type": "BABY", "wbc": "5,000-13,000", "rbc": "4.0-5.2", "hb": "11.5-15.5", "hct": "35.0-45.0", "mcv": "75.0-87.0", "mch": "25.0-31.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}
    elif gender == "Female":
        return {"type": "FEMALE", "wbc": "4,000-11,000", "rbc": "3.9-4.5", "hb": "11.5-16.5", "hct": "36.0-46.0", "mcv": "80.0-95.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}
    else:
        return {"type": "MALE", "wbc": "4,000-11,000", "rbc": "4.5-5.6", "hb": "13.0-17.0", "hct": "40.0-50.0", "mcv": "82.0-98.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}

# --- PDF GENERATOR (LOGO & ADDRESS INCLUDED) ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    
    # Header Area
    pdf.set_font("Arial", 'B', 20)
    pdf.set_text_color(30, 136, 229)
    pdf.cell(0, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "N0 10, Main Street, Location, City", ln=True, align='C')
    pdf.cell(0, 5, "Tel: 011 2XXXXXX / 071 XXXXXXX", ln=True, align='C')
    pdf.cell(0, 5, "Email: lifecarelab@gmail.com", ln=True, align='C')
    pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(10)
    
    # Patient Data Table
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Invoice: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)
    
    # Financials
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
    pdf.cell(140, 10, "NET PAYABLE (LKR):", align='R'); pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    
    return pdf.output(dest='S').encode('latin-1')

# --- UI LOGO FUNCTION ---
def ui_logo():
    st.markdown("""
        <div style="text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="color: #1E88E5; margin-bottom: 0;">🔬 LIFE CARE LABORATORY</h1>
            <p style="color: #555; font-size: 1.2em;">Accuracy . Reliability . Care</p>
        </div>
    """, unsafe_allow_html=True)

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    ui_logo()
    with st.columns([1, 1.5, 1])[1]:
        with st.form("login_form"):
            st.subheader("System Access")
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            # User roles 4 ක්
            r = st.selectbox("Select User Role", ["Admin", "Billing", "Technician", "Reception"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid credentials!")

# 2. LOGGED IN SYSTEM
else:
    st.sidebar.markdown(f"### Welcome, \n **{st.session_state.username}**")
    st.sidebar.text(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("System Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        st.title("Admin Control Panel")
        menu = st.sidebar.selectbox("Navigation", ["Users", "Doctors", "Tests", "Reports"])
        
        if menu == "Users":
            with st.form("u"):
                un = st.text_input("Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Reception"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif menu == "Tests":
            with st.form("t"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price", 0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING / RECEPTION ---
    elif st.session_state.user_role in ["Billing", "Reception"]:
        ui_logo()
        tab1, tab2 = st.tabs(["New Registration", "Saved Bills"])
        
        with tab1:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                salute = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Name")
                ay = c1.number_input("Age (Y)", 0, 120, 0); am = c2.number_input("Age (M)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)

            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            t_list = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", t_list)
            
            # FINANCIAL CALCULATIONS
            total_bill = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            
            st.write("---")
            col_full, col_disc, col_net = st.columns(3)
            col_full.metric("Full Amount", f"LKR {total_bill:,.2f}")
            disc_amt = col_disc.number_input("Discount (LKR)", min_value=0.0, step=10.0)
            net_amt = total_bill - disc_amt
            col_net.markdown(f"<div style='background-color:#d4edda; padding:10px; border-radius:5px;'><h3 style='margin:0; color:#155724;'>Net: LKR {net_amt:,.2f}</h3></div>", unsafe_allow_html=True)

            if st.button("SAVE BILL", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - LKR")[0] for s in selected])
                    c.execute("INSERT INTO billing VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, tnames, total_bill, disc_amt, net_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success("Saved!"); st.rerun()

        with tab2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, row in bills.iterrows():
                with st.expander(f"📄 {row['ref_no']} - {row['name']}"):
                    st.write(f"Tests: {row['tests']} | **Final: LKR {row['final_amount']:,.2f}**")
                    pdf = create_bill_pdf(row)
                    st.download_button("📥 Download PDF", pdf, f"Bill_{row['ref_no']}.pdf", "application/pdf", key=f"d_{row['id']}")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        st.header("🔬 Laboratory Technician Portal")
        # Technician logic...

conn.close()
