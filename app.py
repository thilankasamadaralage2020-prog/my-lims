import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v56.db', check_same_thread=False)
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
LOGO_PATH = "logo.png"

def show_logo(width=150):
    if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=width)
    else: st.title("LIFE CARE LABORATORY")

def get_fbc_structure(age_y, gender):
    components = ["Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"]
    units = {"Total White Cell Count (WBC)": "cells/cu/mm", "Neutrophils": "%", "Lymphocytes": "%", "Monocytes": "%", "Eosinophils": "%", "Basophils": "%", "Hemoglobin (Hb)": "g/dL", "Red Blood Cell (RBC)": "10^6/uL", "HCT / PCV": "%", "MCV": "fL", "MCH": "pg", "MCHC": "g/dL", "RDW": "%", "Platelet Count": "10^3/uL"}
    if age_y < 5:
        ranges = {"Total White Cell Count (WBC)": "5000 - 13000", "Neutrophils": "25 - 45", "Lymphocytes": "45 - 65", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "10.5 - 14.0", "Red Blood Cell (RBC)": "3.8 - 5.2", "HCT / PCV": "32 - 42", "MCV": "75 - 90", "MCH": "24 - 30", "MCHC": "32 - 36", "RDW": "11.5 - 15.0", "Platelet Count": "150 - 450"}
    else:
        ranges = {"Total White Cell Count (WBC)": "4000 - 11000", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "13.5 - 17.5" if gender == "Male" else "12.0 - 15.5", "Red Blood Cell (RBC)": "4.5 - 5.5" if gender == "Male" else "3.8 - 4.8", "HCT / PCV": "40 - 52" if gender == "Male" else "36 - 47", "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"}
    return [{"label": c, "unit": units[c], "range": ranges.get(c, "")} for c in components]

def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False):
    pdf = FPDF()
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
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10); pdf.cell(70, 9, "  Component", 0, 0, 'L'); pdf.cell(30, 9, "Result", 0, 0, 'C'); pdf.cell(30, 9, "Unit", 0, 0, 'C'); pdf.cell(60, 9, "Reference Range", 0, 1, 'C')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
        pdf.set_font("Arial", '', 10)
        fbc_data = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
        for item in fbc_data:
            res_val = results_dict.get(item['label'], "")
            pdf.cell(70, 7, f"  {item['label']}", 0); pdf.cell(30, 7, str(res_val), 0, 0, 'C'); pdf.cell(30, 7, item['unit'], 0, 0, 'C'); pdf.cell(60, 7, item['range'], 0, 1, 'C')
        pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
    else:
        pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 0); pdf.cell(50, 8, "Amount (LKR)", 0, 1, 'R')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
        pdf.set_font("Arial", '', 10); pdf.cell(140, 8, bill_row['tests'], 0); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 0, 1, 'R')
        pdf.cell(140, 8, "Discount", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 0, 1, 'R')
        pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Net Amount", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 0, 1, 'R')
    return pdf.output(dest='S').encode('latin-1')

st.set_page_config(page_title="Life Care LIMS", layout="wide")
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None

if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        show_logo(width=200)
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password"); r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone(): st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
                else: st.error("Access Denied")
else:
    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        st.sidebar.subheader("Admin Menu")
        choice = st.sidebar.radio("Navigate", ["Users", "Doctors", "Tests"])
        if choice == "Users":
            with st.expander("➕ Add User"):
                with st.form("u"):
                    un = st.text_input("Name"); pw = st.text_input("Pass"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                    if st.form_submit_button("Save"): c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            st.write("---")
            u_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            for i, r in u_df.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**{r['username']}**"); col2.write(r['role'])
                if r['username'] != 'admin' and col3.button("Delete", key=f"d_{r['username']}"):
                    c.execute("DELETE FROM users WHERE username=?", (r['username'],)); conn.commit(); st.rerun()

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        show_logo(width=100); st.subheader("📝 Billing")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); pname = c2.text_input("Name")
            ay = c1.number_input("Age (Y)", 0); am = c2.number_input("Age (M)", 0)
            gen = c1.selectbox("Gender", ["Male", "Female"]); mob = c2.text_input("Mobile")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            pdoc = st.selectbox("Doctor", ["Self"] + docs)
            t_db = pd.read_sql_query("SELECT * FROM tests", conn)
            sel = st.multiselect("Tests", [f"{r['test_name']} - {r['price']}" for _, r in t_db.iterrows()])
            gross = sum([float(s.split(" - ")[-1]) for s in sel]); disc = st.number_input("Discount", 0.0); final = gross - disc
            st.info(f"Total: {final:,.2f}")
            if st.button("SAVE BILL", use_container_width=True):
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"; tn = ", ".join([s.split(" - ")[0] for s in sel])
                c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, pname, ay, am, gen, mob, pdoc, tn, gross, disc, final, str(date.today()), st.session_state.username, "Active"))
                conn.commit(); st.session_state.last_b = ref; st.success("Saved")
        if 'last_b' in st.session_state:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.last_b}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD INVOICE", create_pdf(row), f"Bill_{row['ref_no']}.pdf", use_container_width=True)

    # --- TECHNICIAN DASHBOARD (UPDATED WITH TABS & BACK OPTION) ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 Technician Workspace")
        
        if st.session_state.editing_ref:
            # --- RESULTS ENTRY PANEL ---
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            if st.button("⬅️ Back to List"):
                st.session_state.editing_ref = None
                st.rerun()
            
            st.markdown(f"### Entering Results for: **{row['name']}** ({row['ref_no']})")
            f_struct = get_fbc_structure(row['age_y'], row['gender'])
            with st.form("results_form"):
                results = {}
                for item in f_struct:
                    col1, col2, col3 = st.columns([3, 1, 2])
                    results[item['label']] = col1.text_input(item['label'], key=f"in_{row['ref_no']}_{item['label']}")
                    col2.write(f"\n{item['unit']}")
                    col3.caption(f"Range: {item['range']}")
                if st.form_submit_button("AUTHORIZE REPORT"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?)", (row['ref_no'], json.dumps(results), st.session_state.username, str(date.today()), "FBC"))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                    conn.commit()
                    st.success("Report Authorized!")
                    st.session_state.last_rep = row['ref_no']
                    st.session_state.editing_ref = None
                    st.rerun()
        else:
            # --- DASHBOARD TABS ---
            tab_pending, tab_completed = st.tabs(["📋 Pending Reports", "✅ Completed Reports"])
            
            with tab_pending:
                pending_sql = "SELECT * FROM billing WHERE status='Active' AND ref_no NOT IN (SELECT bill_ref FROM results) ORDER BY id DESC"
                pending_data = pd.read_sql_query(pending_sql, conn)
                if pending_data.empty: st.info("No pending reports.")
                else:
                    for _, r in pending_data.iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([4, 1])
                            c1.write(f"**{r['ref_no']} - {r['name']}** ({r['date']})")
                            if c2.button("Enter Results", key=f"btn_{r['ref_no']}"):
                                st.session_state.editing_ref = r['ref_no']
                                st.rerun()
            
            with tab_completed:
                comp_sql = "SELECT b.*, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC"
                comp_data = pd.read_sql_query(comp_sql, conn)
                if comp_data.empty: st.info("No completed reports yet.")
                else:
                    for _, r in comp_data.iterrows():
                        with st.container(border=True):
                            st.write(f"✅ **{r['ref_no']} - {r['name']}** | Authorized by: {r['authorized_by']}")
                            if st.button("View/Download", key=f"view_{r['ref_no']}"):
                                st.session_state.last_rep = r['ref_no']
                                st.rerun()

        if 'last_rep' in st.session_state:
            res_row = pd.read_sql_query(f"SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.ref_no='{st.session_state.last_rep}'", conn).iloc[0]
            st.download_button("📥 DOWNLOAD PDF", create_pdf(res_row, json.loads(res_row['data']), res_row['authorized_by'], True), f"Report_{res_row['ref_no']}.pdf", use_container_width=True)

    # --- SATELLITE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("📡 Final Reports")
        reps = pd.read_sql_query("SELECT b.*, r.data, r.authorized_by FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC", conn)
        for _, r in reps.iterrows():
            with st.container(border=True):
                st.write(f"**{r['name']}** ({r['ref_no']})"); st.download_button("Print", create_pdf(r, json.loads(r['data']), r['authorized_by'], True), f"Rep_{r['ref_no']}.pdf", key=f"s_{r['ref_no']}")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()

conn.close()
