import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v51.db', check_same_thread=False)
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

LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- REFERENCE RANGES (CLEANED) ---
def get_fbc_structure(age_y, gender):
    components = [
        "Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", 
        "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", 
        "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"
    ]
    
    units = {
        "Total White Cell Count (WBC)": "10^3/uL", "Neutrophils": "%", "Lymphocytes": "%", 
        "Monocytes": "%", "Eosinophils": "%", "Basophils": "%", "Hemoglobin (Hb)": "g/dL",
        "Red Blood Cell (RBC)": "10^6/uL", "HCT / PCV": "%", "MCV": "fL", 
        "MCH": "pg", "MCHC": "g/dL", "RDW": "%", "Platelet Count": "10^3/uL"
    }

    # Reference Ranges without "Ref:" or "Standard" labels
    if age_y < 5:
        ranges = {
            "Total White Cell Count (WBC)": "5.0 - 15.0", "Neutrophils": "25 - 45", "Lymphocytes": "45 - 65",
            "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "10.5 - 14.0", 
            "Red Blood Cell (RBC)": "3.8 - 5.2", "HCT / PCV": "32 - 42", "MCV": "75 - 90", "MCH": "24 - 30", 
            "MCHC": "32 - 36", "RDW": "11.5 - 15.0", "Platelet Count": "150 - 450"
        }
    elif gender == "Male":
        ranges = {
            "Total White Cell Count (WBC)": "4.0 - 11.0", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45",
            "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "13.5 - 17.5", 
            "Red Blood Cell (RBC)": "4.5 - 5.5", "HCT / PCV": "40 - 52", "MCV": "80 - 100", "MCH": "27 - 32", 
            "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"
        }
    else:
        ranges = {
            "Total White Cell Count (WBC)": "4.0 - 11.0", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45",
            "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "12.0 - 15.5", 
            "Red Blood Cell (RBC)": "3.8 - 4.8", "HCT / PCV": "36 - 47", "MCV": "80 - 100", "MCH": "27 - 32", 
            "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"
        }

    return [{"label": c, "unit": units[c], "range": ranges.get(c, "See Lab Note")} for c in components]

# --- PDF REPORT GENERATOR ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 12, 10, 30)
    
    # Header
    pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Data (Structured Left and Right)
    pdf.set_font("Arial", '', 10)
    curr_y = pdf.get_y()
    # Left Side
    pdf.text(12, curr_y + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
    pdf.text(12, curr_y + 12, f"Age / Gender : {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.text(12, curr_y + 19, f"Ref. Doctor   : {bill_row['doctor']}")
    # Right Side
    pdf.text(130, curr_y + 5, f"Reference No  : {bill_row['ref_no']}")
    pdf.text(130, curr_y + 12, f"Billing Date   : {bill_row['date']}")
    if is_report:
        pdf.text(130, curr_y + 19, f"Reported Date : {date.today()}")
    
    pdf.set_y(curr_y + 25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

    if is_report:
        # Bold Heading - Font size increased by 2 (14)
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(5)
        
        # Table
        pdf.set_font("Arial", 'B', 10); pdf.set_fill_color(245, 245, 245)
        pdf.cell(70, 9, "  Component", 1, 0, 'L', True); pdf.cell(30, 9, "Result", 1, 0, 'C', True)
        pdf.cell(30, 9, "Unit", 1, 0, 'C', True); pdf.cell(60, 9, "Reference Range", 1, 1, 'C', True)
        
        pdf.set_font("Arial", '', 10)
        fbc_data = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
        for item in fbc_data:
            res_val = results_dict.get(item['label'], "")
            pdf.cell(70, 8, f"  {item['label']}", 1); pdf.cell(30, 8, str(res_val), 1, 0, 'C')
            pdf.cell(30, 8, item['unit'], 1, 0, 'C'); pdf.cell(60, 8, item['range'], 1, 1, 'C')
        
        pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
    else:
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 1); pdf.cell(50, 8, "Amount (LKR)", 1, 1, 'R')
        pdf.set_font("Arial", '', 10); pdf.cell(140, 8, bill_row['tests'], 1); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 1, 1, 'R')
        pdf.cell(140, 8, "Discount", 1, 0, 'R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 1, 1, 'R')
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Net Amount", 1, 0, 'R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP UI ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        if os.path.exists("logo.png"): st.image("logo.png", width=150)
        else: st.title("LIFE CARE")
        # Corrected Login Form (No DeltaGenerator error)
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                user = c.fetchone()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = r
                    st.session_state.username = u
                    st.rerun()
                else: st.error("Invalid Username or Password")
else:
    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        st.sidebar.title(f"Admin: {st.session_state.username}")
        choice = st.sidebar.radio("Navigation", ["User Management", "Doctor Management", "Test Settings"])
        if choice == "User Management":
            st.subheader("👥 Manage Users")
            with st.form("add_user"):
                new_u = st.text_input("New Username"); new_p = st.text_input("New Password"); new_r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Create Account"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (new_u, new_p, new_r)); conn.commit(); st.success("User Added")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)
        elif choice == "Doctor Management":
            with st.form("add_doc"):
                d_name = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (d_name,)); conn.commit(); st.success("Doctor Added")
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
        elif choice == "Test Settings":
            with st.form("add_test"):
                t_name = st.text_input("Test Name"); t_price = st.number_input("Price (LKR)")
                if st.form_submit_button("Add Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_name, t_price)); conn.commit(); st.success("Test Added")
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📑 New Patient Registration")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            pname = c2.text_input("Patient Name")
            ay = c1.number_input("Age (Years)", 0, 120); am = c2.number_input("Age (Months)", 0, 11)
            gen = c1.selectbox("Gender", ["Male", "Female"]); mob = c2.text_input("Mobile No")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            pdoc = st.selectbox("Referral Doctor", ["Self"] + docs)
            tests_list = pd.read_sql_query("SELECT * FROM tests", conn)
            selected = st.multiselect("Select Tests", [f"{r['test_name']} - {r['price']}" for _, r in tests_list.iterrows()])
            
            # Real-time Discount Calculation
            total_gross = sum([float(s.split(" - ")[-1]) for s in selected])
            discount_val = st.number_input("Discount (LKR)", 0.0)
            net_total = total_gross - discount_val
            st.markdown(f"### Total: LKR {net_total:,.2f}")

            if st.button("SAVE & GENERATE INVOICE", use_container_width=True):
                if pname and selected:
                    ref_id = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tnames = ", ".join([s.split(" - ")[0] for s in selected])
                    c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (ref_id, sal, pname, ay, am, gen, mob, pdoc, tnames, total_gross, discount_val, net_total, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.session_state.last_ref = ref_id
                    st.success(f"Success! Ref: {ref_id}")

        if 'last_ref' in st.session_state:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.last_ref}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD INVOICE", create_pdf(row), f"Bill_{row['ref_no']}.pdf", use_container_width=True)

    # --- TECHNICIAN DASHBOARD ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 FBC Result Entry Panel")
        pending_bills = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
        if pending_bills.empty: st.info("No pending reports.")
        for _, row in pending_bills.iterrows():
            with st.expander(f"📝 {row['ref_no']} - {row['name']}"):
                fbc_struct = get_fbc_structure(row['age_y'], row['gender'])
                with st.form(f"form_{row['ref_no']}"):
                    results = {}
                    for item in fbc_struct:
                        col1, col2, col3 = st.columns([3, 1, 2])
                        results[item['label']] = col1.text_input(item['label'], key=f"inp_{row['ref_no']}_{item['label']}")
                        col2.write(f"\n{item['unit']}")
                        col3.caption(f"Range: {item['range']}") # No "Ref:" label
                    if st.form_submit_button("SAVE & AUTHORIZE REPORT"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", (row['ref_no'], json.dumps(results), st.session_state.username, str(date.today()), "FBC"))
                        conn.commit()
                        st.success("Authorized!")
                        # Directly offer download
                        st.session_state.last_rep = row['ref_no']
                        st.rerun()
        
        if 'last_rep' in st.session_state:
            r_data = pd.read_sql_query(f"SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.ref_no='{st.session_state.last_rep}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD REPORT", create_pdf(r_data, json.loads(r_data['data']), r_data['authorized_by'], True), f"Report_{r_data['ref_no']}.pdf", use_container_width=True)

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("📡 Finalized Reports")
        all_reps = pd.read_sql_query("SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC", conn)
        for _, r in all_reps.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                col1.write(f"**{r['name']}** ({r['ref_no']}) | Auth by: {r['authorized_by']}")
                col2.download_button("Print", create_pdf(r, json.loads(r['data']), r['authorized_by'], True), f"Rep_{r['ref_no']}.pdf", key=f"s_{r['ref_no']}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
