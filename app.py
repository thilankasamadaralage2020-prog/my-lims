import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json
import math

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v65.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT, format_used TEXT, comment TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- CONSTANTS & STRUCTURES ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

def get_fbc_structure(age_y, gender):
    components = ["Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"]
    return components

UFR_FIELDS = ["Colour", "Appearance", "Specific Gravity", "PH", "Urine sugar", "Ketone bodies", "Bilirubin", "Urobilinogen", "Pus cells", "Red cells", "Epithelial cells", "Casts", "Crystals"]

# --- eGFR CALCULATION (CKD-EPI 2021) ---
def calculate_egfr(scr, age, gender):
    kappa = 0.9 if gender == "Male" else 0.7
    alpha = -0.411 if gender == "Male" else -0.329
    multiplier = 1.0 if gender == "Male" else 1.012
    egfr = 142 * (min(scr / kappa, 1) ** alpha) * (max(scr / kappa, 1) ** -1.200) * (0.9938 ** age) * multiplier
    return round(egfr, 2)

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False, comment="", format_list=None):
    try:
        pdf = FPDF()
        formats = format_list if format_list else ["General"]
        for fmt in formats:
            pdf.add_page()
            if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 12, 10, 30)
            pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
            pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
            pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
            # Patient Info
            pdf.set_font("Arial", '', 10); curr_y = pdf.get_y()
            pdf.text(12, curr_y + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
            pdf.text(12, curr_y + 12, f"Age / Gender : {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
            pdf.text(12, curr_y + 19, f"Ref. Doctor   : {bill_row['doctor']}")
            pdf.text(130, curr_y + 5, f"Reference No  : {bill_row['ref_no']}")
            pdf.text(130, curr_y + 12, f"Billing Date   : {bill_row['date']}")
            pdf.set_y(curr_y + 25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)
            # Report Data Content (General)
            if is_report:
                pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, f"TEST REPORT: {fmt}", ln=True, align='C'); pdf.ln(5)
                # (Report generation logic remains the same for A4)
            else:
                pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
                pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 0); pdf.cell(50, 8, "Amount (LKR)", 0, 1, 'R')
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
                pdf.cell(140, 8, bill_row['tests'], 0); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 0, 1, 'R')
                pdf.cell(140, 8, f"Discount: ", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 0, 1, 'R')
                pdf.set_font("Arial", 'B', 11); pdf.cell(140, 8, "Final Amount: ", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 0, 1, 'R')
        return pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e: return f"Error: {e}".encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None

if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=250)
        st.subheader("Login to Life Care")
        with st.form("login_form"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                res = c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r)).fetchone()
                if res: st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
                else: st.error("Invalid Login")
else:
    # --- BILLING ROLE ---
    if st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["New Bill", "Saved Bills"])
        with t1:
            with st.form("billing_form"):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); name = c2.text_input("Patient Name")
                age_y = c1.number_input("Age (Y)", 0); gen = c2.selectbox("Gender", ["Male", "Female"])
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                pdoc = st.selectbox("Doctor", ["Self"]+docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Select Tests", tests_db['test_name'].tolist())
                
                # Calculation Display
                total = sum(tests_db[tests_db['test_name'].isin(sel)]['price'])
                st.write(f"**Gross Amount: LKR {total:,.2f}**")
                disc = st.number_input("Discount (LKR)", 0.0)
                final = total - disc
                st.markdown(f"### Final Amount: LKR {final:,.2f}")
                
                if st.form_submit_button("SAVE BILL"):
                    if name and sel:
                        ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                        c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, name, age_y, 0, gen, pdoc, ", ".join(sel), total, disc, final, str(date.today()), st.session_state.username, "Active"))
                        conn.commit(); st.success(f"Saved: {ref}")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC LIMIT 15", conn)
            for _, b in bills.iterrows():
                with st.container(border=True):
                    cl1, cl2 = st.columns([4, 1]); cl1.write(f"**{b['name']}** | {b['ref_no']} | {b['tests']}"); cl2.download_button("Print Bill", create_pdf(b), f"Bill_{b['ref_no']}.pdf", key=f"b_{b['ref_no']}")

    # --- TECHNICIAN ROLE (FULL WORKSHEET) ---
    elif st.session_state.user_role == "Technician":
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            billed_list = row['tests'].split(", ")
            results_data = {}
            with st.form("full_worksheet"):
                st.subheader(f"Full Worksheet: {row['name']} ({row['ref_no']})")
                for test in billed_list:
                    st.info(f"Test Component: {test}")
                    if "FBC" in test.upper() or "FULL BLOOD COUNT" in test.upper():
                        for f in get_fbc_structure(row['age_y'], row['gender']):
                            results_data[f] = st.text_input(f, key=f"fbc_{f}")
                    elif "UFR" in test.upper() or "URINE" in test.upper():
                        for u in UFR_FIELDS:
                            results_data[u] = st.text_input(u, key=f"ufr_{u}")
                    elif "CREATININE" in test.upper():
                        cre_v = st.text_input("Serum Creatinine (mg/dL)", key="cre_val")
                        if cre_v:
                            egfr = calculate_egfr(float(cre_v), row['age_y'], row['gender'])
                            results_data["Serum Creatinine"] = {"val": cre_v, "egfr": egfr}
                            st.write(f"Auto-calculated eGFR: {egfr}")
                    else:
                        results_data[test] = st.text_input("Result Value", key=f"gen_{test}")
                
                if st.form_submit_button("AUTHORIZE ALL REPORTS"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(results_data), st.session_state.username, str(date.today()), json.dumps(billed_list), ""))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],)); conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
            st.write("### Pending Workload")
            for _, r in pending.iterrows():
                if st.button(f"LOAD WORKSHEET: {r['name']} ({r['tests']})", key=r['ref_no'], use_container_width=True):
                    st.session_state.editing_ref = r['ref_no']; st.rerun()

    # --- ADMIN ROLE (USER DELETE RESTORED) ---
    elif st.session_state.user_role == "Admin":
        choice = st.sidebar.radio("Go to", ["Users", "Doctors", "Tests"])
        if choice == "Users":
            st.write("### Manage Users")
            u_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            for i, r in u_df.iterrows():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{r['username']}**"); c2.write(r['role'])
                if r['username'] != 'admin' and c3.button("🗑️", key=f"del_{r['username']}"):
                    c.execute("DELETE FROM users WHERE username=?", (r['username'],)); conn.commit(); st.rerun()

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
conn.close()
