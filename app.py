import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v50.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT, format_used TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LAB DETAILS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- DYNAMIC RANGES (Ref & Standard labels removed) ---
def get_fbc_structure(age_y, gender):
    components = ["Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"]
    units = {"Total White Cell Count (WBC)": "10^3/uL", "Neutrophils": "%", "Lymphocytes": "%", "Monocytes": "%", "Eosinophils": "%", "Basophils": "%", "Hemoglobin (Hb)": "g/dL", "Red Blood Cell (RBC)": "10^6/uL", "HCT / PCV": "%", "MCV": "fL", "MCH": "pg", "MCHC": "g/dL", "RDW": "%", "Platelet Count": "10^3/uL"}
    
    if age_y < 5:
        fmt = "BABY FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "5.0 - 15.0", "Neutrophils": "25 - 45", "Lymphocytes": "45 - 65", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "10.5 - 14.0", "Red Blood Cell (RBC)": "3.8 - 5.2", "HCT / PCV": "32 - 42", "MCV": "75 - 90", "MCH": "24 - 30", "MCHC": "32 - 36", "RDW": "11.5 - 15.0", "Platelet Count": "150 - 450"}
    elif gender == "Male":
        fmt = "ADULT MALE FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "4.0 - 11.0", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "13.5 - 17.5", "Red Blood Cell (RBC)": "4.5 - 5.5", "HCT / PCV": "40 - 52", "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"}
    else:
        fmt = "ADULT FEMALE FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "4.0 - 11.0", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "12.0 - 15.5", "Red Blood Cell (RBC)": "3.8 - 4.8", "HCT / PCV": "36 - 47", "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"}

    return [{"label": c, "unit": units[c], "range": ranges.get(c, "As per Lab")} for c in components], fmt

# --- PDF GENERATOR (Advanced Layout) ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 28)
    
    # Header
    pdf.set_font("Arial", 'B', 16); pdf.set_x(42); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 10); pdf.set_x(42); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
    pdf.ln(8); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Info Layout
    pdf.set_font("Arial", '', 10)
    # Left Side
    y_start = pdf.get_y()
    pdf.text(12, y_start + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
    pdf.text(12, y_start + 12, f"Age / Gender  : {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.text(12, y_start + 19, f"Ref. Doctor    : {bill_row['doctor']}")
    # Right Side
    pdf.text(130, y_start + 5, f"Ref. No        : {bill_row['ref_no']}")
    pdf.text(130, y_start + 12, f"Billing Date  : {bill_row['date']}")
    if is_report:
        pdf.text(130, y_start + 19, f"Reported Date : {date.today()}")
    
    pdf.set_y(y_start + 25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

    if is_report:
        # Bold Heading (Font size +2)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(2)
        
        # Table Header
        pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(240, 240, 240)
        pdf.cell(70, 8, "  Parameter", 1, 0, 'L', True); pdf.cell(30, 8, "Result", 1, 0, 'C', True)
        pdf.cell(30, 8, "Unit", 1, 0, 'C', True); pdf.cell(60, 8, "Reference Range", 1, 1, 'C', True)
        
        # Table Body
        pdf.set_font("Arial", '', 10)
        f_struct, _ = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
        for item in f_struct:
            val = results_dict.get(item['label'], "")
            pdf.cell(70, 8, f"  {item['label']}", 1); pdf.cell(30, 8, str(val), 1, 0, 'C')
            pdf.cell(30, 8, item['unit'], 1, 0, 'C'); pdf.cell(60, 8, item['range'], 1, 1, 'C')
            
        pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
    else:
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 1); pdf.cell(50, 8, "Amount (LKR)", 1, 1, 'R')
        pdf.set_font("Arial", '', 10); pdf.cell(140, 8, bill_row['tests'], 1); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 1, 1, 'R')
        pdf.cell(140, 8, "Discount", 1, 0, 'R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 1, 1, 'R')
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Net Amount", 1, 0, 'R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(layout="wide", page_title="Life Care LIMS")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        st.image("logo.png", width=150) if os.path.exists("logo.png") else st.title("LIFE CARE")
        with st.form("login"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone(): st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
                else: st.error("Access Denied")
else:
    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        st.sidebar.title("Admin")
        m = st.sidebar.selectbox("Menu", ["User Accounts", "Doctors", "Tests"])
        if m == "User Accounts":
            with st.form("u"):
                un = st.text_input("Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Add User"): c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))
        elif m == "Doctors":
            with st.form("d"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"): c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
        elif m == "Tests":
            with st.form("t"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price")
                if st.form_submit_button("Save Test"): c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📝 New Billing")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            sal = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            pname = col2.text_input("Patient Name")
            ay = col1.number_input("Age (Y)", 0, 120); am = col2.number_input("Age (M)", 0, 11)
            gen = col1.selectbox("Gender", ["Male", "Female"]); mob = col2.text_input("Mobile")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            pdoc = st.selectbox("Referral Doctor", ["Self"] + docs)
            t_db = pd.read_sql_query("SELECT * FROM tests", conn)
            sel = st.multiselect("Tests", [f"{r['test_name']} - {r['price']}" for _, r in t_db.iterrows()])
            
            # Discount Logic Fix
            total = sum([float(s.split(" - ")[-1]) for s in sel])
            disc = st.number_input("Discount (LKR)", 0.0)
            final = total - disc
            st.info(f"Gross: {total:,.2f} | Discount: {disc:,.2f} | **Final: {final:,.2f}**")

            if st.button("SAVE & GENERATE BILL", use_container_width=True):
                if pname and sel:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tn_str = ", ".join([s.split(" - ")[0] for s in sel])
                    c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (ref, sal, pname, ay, am, gen, mob, pdoc, tn_str, total, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.session_state.last_bill = ref; st.success(f"Bill Saved: {ref}")

        if 'last_bill' in st.session_state:
            bill_row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.last_bill}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD INVOICE", create_pdf(bill_row), f"Invoice_{bill_row['ref_no']}.pdf", use_container_width=True)

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 FBC Result Entry")
        active = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
        for _, row in active.iterrows():
            with st.expander(f"Patient: {row['name']} | Ref: {row['ref_no']}"):
                f_struct, fmt = get_fbc_structure(row['age_y'], row['gender'])
                with st.form(f"form_{row['ref_no']}"):
                    inputs = {}
                    for item in f_struct:
                        c1, c2, c3 = st.columns([3, 1, 2])
                        inputs[item['label']] = c1.text_input(item['label'], key=f"i_{row['ref_no']}_{item['label']}")
                        c2.write(f"\n{item['unit']}")
                        c3.info(item['range']) # Clean Range
                    if st.form_submit_button("AUTHORIZE & SAVE"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", (row['ref_no'], json.dumps(inputs), st.session_state.username, str(date.today()), fmt))
                        conn.commit(); st.success("Authorized!"); st.rerun()

    # --- SATELLITE (REPORT DOWNLOAD) ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("📡 Authorized Reports")
        q = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
        reps = pd.read_sql_query(q, conn)
        for _, r in reps.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{r['name']}** ({r['ref_no']}) - Authorized by {r['authorized_by']}")
                col2.download_button("📥 DOWNLOAD REPORT", create_pdf(r, json.loads(r['data']), r['authorized_by'], True), f"Report_{r['ref_no']}.pdf", key=f"dl_{r['ref_no']}")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

conn.close()
