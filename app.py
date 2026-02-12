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

# --- LAB SETTINGS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

def show_logo(width=200):
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=width)
    else:
        st.title("LIFE CARE LABORATORY")

# --- eGFR CALCULATION (CKD-EPI 2021) ---
def calculate_egfr(scr, age, gender):
    kappa = 0.9 if gender == "Male" else 0.7
    alpha = -0.411 if gender == "Male" else -0.329
    multiplier = 1.0 if gender == "Male" else 1.012
    egfr = 142 * (min(scr / kappa, 1) ** alpha) * (max(scr / kappa, 1) ** -1.200) * (0.9938 ** age) * multiplier
    return round(egfr, 2)

# --- PDF GENERATOR (A4 MULTI-PAGE) ---
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
            
            pdf.set_font("Arial", '', 10); curr_y = pdf.get_y()
            pdf.text(12, curr_y + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
            pdf.text(12, curr_y + 12, f"Age / Gender : {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
            pdf.text(12, curr_y + 19, f"Ref. Doctor   : {bill_row['doctor']}")
            pdf.text(130, curr_y + 5, f"Reference No  : {bill_row['ref_no']}")
            pdf.text(130, curr_y + 12, f"Billing Date   : {bill_row['date']}")
            if is_report: pdf.text(130, curr_y + 19, f"Reported Date : {date.today()}")
            pdf.set_y(curr_y + 25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

            if is_report:
                if fmt == "Serum Creatinine":
                    pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "BIOCHEMISTRY REPORT", ln=True, align='C'); pdf.ln(5)
                    pdf.set_font("Arial", 'B', 10); pdf.cell(80, 9, "  Test Description", 0, 0, 'L'); pdf.cell(40, 9, "Result", 0, 0, 'C'); pdf.cell(30, 9, "Unit", 0, 0, 'C'); pdf.cell(40, 9, "Ref. Range", 0, 1, 'C')
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
                    res = results_dict.get("Serum Creatinine", {})
                    cre_ref = "0.90 - 1.30" if bill_row['gender'] == "Male" else "0.65 - 1.10"
                    pdf.cell(80, 7, "  Serum Creatinine", 0); pdf.cell(40, 7, str(res.get("val", "")), 0, 0, 'C'); pdf.cell(30, 7, "mg/dL", 0, 0, 'C'); pdf.cell(40, 7, cre_ref, 0, 1, 'C')
                    if res.get("egfr"):
                        pdf.cell(80, 7, "  eGFR (CKD-EPI 2021)", 0); pdf.cell(40, 7, str(res.get("egfr")), 0, 0, 'C'); pdf.cell(30, 7, "mL/min/1.73m2", 0, 0, 'C'); pdf.cell(40, 7, "> 60", 0, 1, 'C')
                        pdf.ln(5); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 6, "CKD Stages:", ln=True)
                        pdf.set_font("Arial", '', 8); pdf.rect(10, pdf.get_y(), 190, 25)
                        pdf.multi_cell(186, 4, "G1: >90 (Normal) | G2: 60-89 (Mild) | G3a: 45-59 (Mild-Mod) | G3b: 30-44 (Mod-Sev) | G4: 15-29 (Severe) | G5: <15 (Failure)")
                
                pdf.set_y(250); pdf.line(10, 250, 200, 250); pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
            else:
                pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
                pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 0); pdf.cell(50, 8, "Amount (LKR)", 0, 1, 'R')
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
                pdf.cell(140, 8, bill_row['tests'], 0); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 0, 1, 'R')
                pdf.cell(140, 8, "Net Amount", 0, 0, 'R'); pdf.set_font("Arial", 'B', 10); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 0, 1, 'R')

        return pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e: return f"Error: {e}".encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None

# --- LOGIN PAGE (RESTORED) ---
if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        show_logo(250)
        st.subheader("Login to Life Care")
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Select Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                res = c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r)).fetchone()
                if res:
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else:
                    st.error("Invalid Credentials. Please check Username, Password and Role.")
else:
    # --- ADMIN ROLE ---
    if st.session_state.user_role == "Admin":
        st.sidebar.subheader("Admin Menu")
        choice = st.sidebar.radio("Navigate", ["Users", "Doctors", "Tests"])
        if choice == "Users":
            with st.form("u_add"):
                un = st.text_input("New Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Create User"): 
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.write("### Manage Users")
            u_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            for i, r in u_df.iterrows():
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"**{r['username']}**"); c2.write(r['role'])
                if r['username'] != 'admin' and c3.button("🗑️ Delete", key=f"d_{r['username']}"):
                    c.execute("DELETE FROM users WHERE username=?", (r['username'],)); conn.commit(); st.rerun()
        elif choice == "Doctors":
            dn = st.text_input("Doctor Name")
            if st.button("Add"): c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
        elif choice == "Tests":
            tn = st.text_input("Test Name"); tp = st.number_input("Price")
            if st.button("Save"): c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ROLE ---
    elif st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["New Bill", "Saved Bills"])
        with t1:
            with st.form("billing_form"):
                col1, col2 = st.columns(2)
                sal = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); name = col2.text_input("Patient Name")
                age_y = col1.number_input("Age (Y)", 0); gen = col2.selectbox("Gender", ["Male", "Female"])
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                pdoc = st.selectbox("Doctor", ["Self"]+docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", tests_db['test_name'].tolist())
                total = sum(tests_db[tests_db['test_name'].isin(sel)]['price'])
                disc = st.number_input("Discount", 0.0); final = total - disc
                if st.form_submit_button("SAVE BILL"):
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, name, age_y, 0, gen, pdoc, ", ".join(sel), total, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success(f"Saved: {ref}")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC LIMIT 15", conn)
            for _, b in bills.iterrows():
                with st.container(border=True):
                    cl1, cl2 = st.columns([4, 1])
                    cl1.write(f"**{b['name']}** | {b['ref_no']} | {b['tests']}")
                    cl2.download_button("Download Bill", create_pdf(b), f"Bill_{b['ref_no']}.pdf", key=f"b_{b['ref_no']}")

    # --- TECHNICIAN ROLE ---
    elif st.session_state.user_role == "Technician":
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            billed_list = row['tests'].split(", ")
            results_data = {}
            with st.form("ws"):
                st.write(f"### Worksheet: {row['name']} ({row['ref_no']})")
                for t in billed_list:
                    st.markdown(f"**Test: {t}**")
                    if "CREATININE" in t.upper():
                        val = st.text_input("Serum Creatinine (mg/dL)", key=f"v_{t}")
                        if val:
                            egfr = calculate_egfr(float(val), row['age_y'], row['gender'])
                            results_data["Serum Creatinine"] = {"val": val, "egfr": egfr}
                            st.info(f"eGFR (CKD-EPI): {egfr}")
                    else:
                        res = st.text_input("Result", key=f"v_{t}")
                        results_data[t] = {"val": res}
                if st.form_submit_button("AUTHORIZE ALL REPORTS"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(results_data), st.session_state.username, str(date.today()), json.dumps(billed_list), ""))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                    conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending", "Completed"])
            with t1:
                pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
                for _, r in pending.iterrows():
                    if st.button(f"{r['name']} - {r['tests']} ({r['ref_no']})", use_container_width=True):
                        st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                done = pd.read_sql_query("SELECT b.*, r.data, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed' ORDER BY b.id DESC", conn)
                for _, r in done.iterrows():
                    with st.container(border=True):
                        cl1, cl2 = st.columns([4, 1])
                        cl1.write(f"**{r['name']}** | {r['tests']}")
                        cl2.download_button("Download A4", create_pdf(r, json.loads(r['data']), st.session_state.username, True, "", json.loads(r['format_used'])), f"Report_{r['ref_no']}.pdf")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

conn.close()
