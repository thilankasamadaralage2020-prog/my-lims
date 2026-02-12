import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_system_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- LAB DETAILS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- FBC PARAMETERS ---
FBC_FIELDS = [
    {"label": "Total White Cell Count (WBC)", "unit": "10^3/uL", "range": "4.0 - 11.0"},
    {"label": "Neutrophils", "unit": "%", "range": "40 - 75"},
    {"label": "Lymphocytes", "unit": "%", "range": "20 - 45"},
    {"label": "Monocytes", "unit": "%", "range": "02 - 10"},
    {"label": "Eosinophils", "unit": "%", "range": "01 - 06"},
    {"label": "Basophils", "unit": "%", "range": "00 - 01"},
    {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": "11.5 - 16.5"},
    {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL", "range": "3.8 - 5.8"},
    {"label": "HCT / PCV", "unit": "%", "range": "37 - 47"},
    {"label": "MCV", "unit": "fL", "range": "80 - 95"},
    {"label": "Platelet Count", "unit": "10^3/uL", "range": "150 - 450"}
]

# --- UI HEADER ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
    with col2:
        st.markdown(f"""
            <div style="text-align: left;">
                <h1 style="color: #1E88E5; margin-bottom: 0;">{LAB_NAME}</h1>
                <p style="color: #333; font-weight: bold; margin-top: 5px;">
                    {LAB_ADDRESS}<br>📱 Tel: {LAB_TEL}
                </p>
            </div>
        """, unsafe_allow_html=True)
    st.write("---")

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 25)
    
    pdf.set_font("Arial", 'B', 16); pdf.set_x(40); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 10); pdf.set_x(40); pdf.cell(0, 5, LAB_ADDRESS, ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Ref: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(10)

    if is_report:
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, "LABORATORY TEST REPORT (FBC)", ln=True, align='C'); pdf.ln(5)
        pdf.cell(70, 8, "Parameter", 1); pdf.cell(30, 8, "Result", 1); pdf.cell(40, 8, "Unit", 1); pdf.cell(50, 8, "Reference Range", 1, ln=True)
        pdf.set_font("Arial", '', 10)
        for field in FBC_FIELDS:
            val = results_dict.get(field['label'], "")
            pdf.cell(70, 8, field['label'], 1); pdf.cell(30, 8, str(val), 1); pdf.cell(40, 8, field['unit'], 1); pdf.cell(50, 8, field['range'], 1, ln=True)
        pdf.ln(10); pdf.cell(0, 10, f"Authorized by: {auth_user}", ln=True, align='R')
    else:
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
        pdf.cell(140, 8, "Test Name", 1); pdf.cell(50, 8, "Amount (LKR)", 1, ln=True, align='R')
        pdf.set_font("Arial", '', 10)
        pdf.cell(140, 8, bill_row['tests'], 1); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 1, ln=True, align='R')
        pdf.ln(5); pdf.set_font("Arial", 'B', 10)
        pdf.cell(140, 8, "Net Amount:", align='R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", ln=True, align='R')

    return pdf.output(dest='S').encode('latin-1')

# --- APP START ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login"):
            st.subheader("🔑 System Login")
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Login")
else:
    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        ui_header()
        st.title("🛡️ Admin Dashboard")
        menu = st.sidebar.selectbox("Admin Menu", ["Users", "Doctors", "Tests", "Reports"])
        if menu == "Users":
            with st.form("u"):
                un = st.text_input("Username"); pw = st.text_input("Password")
                rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Save"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT username, role FROM users", conn))
        elif menu == "Doctors":
            with st.form("d"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
        elif menu == "Tests":
            with st.form("t"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price")
                if st.form_submit_button("Save"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))
        elif menu == "Reports":
            df = pd.read_sql_query("SELECT * FROM billing", conn)
            st.dataframe(df); st.metric("Total Sales", f"LKR {df['final_amount'].sum():,.2f}")

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        ui_header()
        t1, t2 = st.tabs(["Billing", "History"])
        with t1:
            with st.container(border=True):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Name")
                ay = c1.number_input("Age (Y)", 0, 120); am = c2.number_input("Age (M)", 0, 11)
                p_gen = c1.selectbox("Gender", ["Male", "Female"]); p_mob = c2.text_input("Mobile")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", [f"{r['test_name']} - {r['price']}" for i, r in tests_db.iterrows()])
            
            gross = sum([float(s.split(" - ")[-1]) for s in sel])
            disc = st.number_input("Discount", 0.0); net = gross - disc
            st.write(f"### Net: LKR {net:,.2f}")
            if st.button("Save Bill"):
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                t_names = ", ".join([s.split(" - ")[0] for s in sel])
                c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (ref, sal, p_name, ay, am, p_gen, p_mob, p_doc, t_names, gross, disc, net, str(date.today()), st.session_state.username, "Active"))
                conn.commit(); st.success("Saved!"); st.rerun()
        with t2:
            hist = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            for i, r in hist.iterrows():
                with st.expander(f"{r['ref_no']} - {r['name']}"):
                    st.download_button("Print Bill", create_pdf(r), f"{r['ref_no']}.pdf", key=f"b_{r['id']}")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        ui_header()
        st.subheader("🔬 FBC Result Entry")
        pending = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        for i, row in pending.iterrows():
            with st.expander(f"📝 {row['ref_no']} - {row['name']}"):
                with st.form(f"f_{row['ref_no']}"):
                    res_in = {}
                    for field in FBC_FIELDS:
                        c1, c2, c3 = st.columns([3, 1, 2])
                        res_in[field['label']] = c1.text_input(field['label'])
                        c2.write(f"\n{field['unit']}")
                        c3.caption(f"Range: {field['range']}")
                    if st.form_submit_button("Authorize"):
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)", (row['ref_no'], json.dumps(res_in), st.session_state.username, str(date.today())))
                        conn.commit(); st.success("Authorized!"); st.rerun()

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        ui_header()
        st.subheader("📡 Reports")
        q = "SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref"
        auths = pd.read_sql_query(q, conn)
        for i, r in auths.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{r['name']}** ({r['ref_no']}) - Auth by: {r['authorized_by']}")
                c2.download_button("Print", create_pdf(r, json.loads(r['data']), r['authorized_by'], True), f"R_{r['ref_no']}.pdf", key=f"s_{r['id']}")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
