import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v49.db', check_same_thread=False)
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

# --- DYNAMIC RANGES ---
def get_fbc_structure(age_y, gender):
    components = ["Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"]
    units = {"Total White Cell Count (WBC)": "10^3/uL", "Neutrophils": "%", "Lymphocytes": "%", "Monocytes": "%", "Eosinophils": "%", "Basophils": "%", "Hemoglobin (Hb)": "g/dL", "Red Blood Cell (RBC)": "10^6/uL", "HCT / PCV": "%", "MCV": "fL", "MCH": "pg", "MCHC": "g/dL", "RDW": "%", "Platelet Count": "10^3/uL"}
    
    if age_y < 5:
        fmt = "BABY FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "5.0-15.0", "Hemoglobin (Hb)": "10.5-14.0", "Red Blood Cell (RBC)": "3.8-5.2", "MCV": "75-90", "MCH": "24-30", "MCHC": "32-36", "RDW": "11.5-15.0", "Platelet Count": "150-450"}
    elif gender == "Male":
        fmt = "ADULT MALE FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "4.0-11.0", "Hemoglobin (Hb)": "13.5-17.5", "Red Blood Cell (RBC)": "4.5-5.5", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "Platelet Count": "150-410"}
    else:
        fmt = "ADULT FEMALE FBC FORMAT"
        ranges = {"Total White Cell Count (WBC)": "4.0-11.0", "Hemoglobin (Hb)": "12.0-15.5", "Red Blood Cell (RBC)": "3.8-4.8", "MCV": "80-100", "MCH": "27-32", "MCHC": "32-36", "RDW": "11.5-14.5", "Platelet Count": "150-410"}

    return [{"label": c, "unit": units[c], "range": ranges.get(c, "Standard")} for c in components], fmt

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 25)
    pdf.set_font("Arial", 'B', 14); pdf.set_x(40); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 9); pdf.set_x(40); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']} ({bill_row['age_y']}Y {bill_row['age_m']}M)")
    pdf.cell(90, 7, f"Ref: {bill_row['ref_no']}", ln=True, align='R')
    pdf.ln(5)

    if is_report:
        pdf.set_font("Arial", 'B', 11); pdf.cell(70, 8, "Parameter", 1); pdf.cell(30, 8, "Result", 1, 0, 'C'); pdf.cell(30, 8, "Unit", 1, 0, 'C'); pdf.cell(60, 8, "Ref Range", 1, 1, 'C')
        pdf.set_font("Arial", '', 10)
        for k, v in results_dict.items():
            f_struct, _ = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
            p_data = next((i for i in f_struct if i["label"] == k), {"unit":"", "range":""})
            pdf.cell(70, 8, k, 1); pdf.cell(30, 8, str(v), 1, 0, 'C'); pdf.cell(30, 8, p_data['unit'], 1, 0, 'C'); pdf.cell(60, 8, p_data['range'], 1, 1, 'C')
        pdf.ln(10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
    else:
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", 0, 1, 'C')
        pdf.cell(140, 8, "Service", 1); pdf.cell(50, 8, "Amount", 1, 1, 'R')
        pdf.set_font("Arial", '', 10); pdf.cell(140, 8, bill_row['tests'], 1); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 1, 1, 'R')
        pdf.cell(140, 8, "Discount", 1); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 1, 1, 'R')
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Net Amount", 1); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 1, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(layout="wide", page_title="Life Care Laboratory")

def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=110)
    with col2: st.markdown(f"### {LAB_NAME}\n{LAB_ADDRESS} | {LAB_TEL}")
    st.write("---")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1, 1])[1]:
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
        ui_header()
        st.subheader("🛡️ Administration Dashboard")
        m = st.sidebar.selectbox("Admin Menu", ["User Accounts", "Doctors", "Tests"])
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
        ui_header()
        st.subheader("📝 Patient Billing")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            pname = c2.text_input("Patient Name")
            ay = c1.number_input("Age (Y)", 0, 120); am = c2.number_input("Age (M)", 0, 11)
            gen = c1.selectbox("Gender", ["Male", "Female"]); mob = c2.text_input("Mobile")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            pdoc = st.selectbox("Doctor", ["Self"] + docs)
            t_db = pd.read_sql_query("SELECT * FROM tests", conn)
            sel = st.multiselect("Select Tests", [f"{r['test_name']} - {r['price']}" for _, r in t_db.iterrows()])
            
            # --- Auto Calculation ---
            total = sum([float(s.split(" - ")[-1]) for s in sel])
            disc = st.number_input("Discount (LKR)", 0.0, step=1.0)
            final_amt = total - disc
            st.markdown(f"#### Gross: LKR {total:,.2f} | **Net Payable: LKR {final_amt:,.2f}**")

            if st.button("SAVE BILL", use_container_width=True):
                if pname and sel:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    tn_str = ", ".join([s.split(" - ")[0] for s in sel])
                    c.execute('''INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) 
                                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (ref, sal, pname, ay, am, gen, mob, pdoc, tn_str, total, disc, final_amt, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.session_state.last_ref = ref
                    st.success(f"Saved Successfully: {ref}")

        # Streamlit Error Fix: Download button should be outside st.form or conditional containers
        if 'last_ref' in st.session_state:
            bill_row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.last_ref}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD LAST BILL", create_pdf(bill_row), f"Bill_{st.session_state.last_ref}.pdf", use_container_width=True)

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        ui_header()
        st.subheader("🔬 FBC Result Entry Panel")
        pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
        if pending.empty: st.info("No active records.")
        for _, row in pending.iterrows():
            with st.expander(f"📦 {row['ref_no']} - {row['name']} (Age: {row['age_y']}Y)"):
                f_struct, fmt = get_fbc_structure(row['age_y'], row['gender'])
                st.caption(f"Applied Format: **{fmt}**")
                with st.form(f"res_{row['ref_no']}"):
                    results = {}
                    for item in f_struct:
                        col1, col2, col3 = st.columns([3, 1, 2])
                        results[item['label']] = col1.text_input(item['label'], key=f"in_{row['ref_no']}_{item['label']}")
                        col2.write(f"\n{item['unit']}")
                        col3.info(f"Ref: {item['range']}")
                    if st.form_submit_button("Authorize & Save"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", (row['ref_no'], json.dumps(results), st.session_state.username, str(date.today()), fmt))
                        conn.commit(); st.success("Authorized!"); st.rerun()

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Print Reports")
        reps = pd.read_sql_query("SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC", conn)
        for _, r in reps.iterrows():
            with st.container(border=True):
                st.write(f"**{r['name']}** ({r['ref_no']})")
                st.download_button("Print PDF", create_pdf(r, json.loads(r['data']), r['authorized_by'], True), f"Report_{r['ref_no']}.pdf", key=f"s_{r['ref_no']}")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

conn.close()
