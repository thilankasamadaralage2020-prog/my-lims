import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os
import json

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

# --- CONSTANTS & LAB SETTINGS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

# --- FBC RANGES & STRUCTURE ---
def get_fbc_details(age_y, gender):
    if age_y < 5:
        ranges = {
            "WBC": "5000 - 13000", "Neut": "25 - 45", "Lymph": "45 - 65", "Mono": "02 - 10", 
            "Eosi": "01 - 06", "Baso": "00 - 01", "Hb": "10.5 - 14.0", "Plt": "150 - 450"
        }
    else:
        ranges = {
            "WBC": "4000 - 11000", "Neut": "40 - 75", "Lymph": "20 - 45", "Mono": "02 - 10", 
            "Eosi": "01 - 06", "Baso": "00 - 01", 
            "Hb": "13.5 - 17.5" if gender == "Male" else "12.0 - 15.5",
            "Plt": "150 - 410"
        }
    
    return [
        {"label": "Total White Cell Count (WBC)", "unit": "cells/cu/mm", "range": ranges["WBC"], "calc": False},
        {"label": "Neutrophils", "unit": "%", "range": ranges["Neut"], "calc": True},
        {"label": "Lymphocytes", "unit": "%", "range": ranges["Lymph"], "calc": True},
        {"label": "Monocytes", "unit": "%", "range": ranges["Mono"], "calc": True},
        {"label": "Eosinophils", "unit": "%", "range": ranges["Eosi"], "calc": True},
        {"label": "Basophils", "unit": "%", "range": ranges["Baso"], "calc": True},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": ranges["Hb"], "calc": False},
        {"label": "Platelet Count", "unit": "10^3/uL", "range": ranges["Plt"], "calc": False}
    ]

# --- PDF GENERATOR (A4 FORMAT) ---
def create_pdf(bill_row, results_dict, auth_user, formats_to_print, comment=""):
    pdf = FPDF()
    for fmt in formats_to_print:
        pdf.add_page()
        if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 12, 10, 30)
        pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
        pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
        pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        pdf.set_font("Arial", '', 10); curr_y = pdf.get_y()
        pdf.text(12, curr_y + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
        pdf.text(12, curr_y + 12, f"Age / Gender : {bill_row['age_y']}Y / {bill_row['gender']}")
        pdf.text(130, curr_y + 5, f"Reference No  : {bill_row['ref_no']}")
        pdf.text(130, curr_y + 12, f"Date          : {bill_row['date']}")
        pdf.set_y(curr_y + 20); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

        if "FBC" in fmt.upper():
            pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(3)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 8, "Test Description"); pdf.cell(25, 8, "Result", 0, 0, 'C')
            pdf.cell(35, 8, "Absolute Count", 0, 0, 'C'); pdf.cell(30, 8, "Unit", 0, 0, 'C')
            pdf.cell(35, 8, "Ref. Range", 0, 1, 'C'); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            
            pdf.set_font("Arial", '', 10)
            wbc_val = float(results_dict.get("Total White Cell Count (WBC)", 0))
            for comp in get_fbc_details(bill_row['age_y'], bill_row['gender']):
                res_val = results_dict.get(comp['label'], "")
                abs_val = int((float(res_val)/100)*wbc_val) if comp['calc'] and res_val and wbc_val > 0 else ""
                pdf.cell(65, 7, f"  {comp['label']}")
                pdf.cell(25, 7, str(res_val), 0, 0, 'C')
                pdf.cell(35, 7, str(abs_val), 0, 0, 'C')
                pdf.cell(30, 7, comp['unit'], 0, 0, 'C')
                pdf.cell(35, 7, comp['range'], 0, 1, 'C')

        if comment:
            pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "Comments:", ln=True)
            pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 7, comment, 1)

        pdf.set_y(260); pdf.line(10, 260, 200, 260)
        pdf.cell(0, 10, f"Authorized by: {auth_user}", align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- STREAMLIT UI ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

# RESTORED LOGIN PAGE
if not st.session_state.logged_in:
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=250)
        st.subheader("Login to Life Care")
        with st.form("login_form"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Select Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                res = c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r)).fetchone()
                if res: st.session_state.update({'logged_in':True, 'username':u, 'user_role':r}); st.rerun()
                else: st.error("Invalid Credentials")
else:
    # --- BILLING ROLE ---
    if st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["New Bill", "Saved Bills"])
        with t1:
            with st.form("billing"):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); name = c2.text_input("Patient Name")
                age = c1.number_input("Age (Y)", 0); gen = c2.selectbox("Gender", ["Male", "Female"])
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", tests_db['test_name'].tolist())
                gross = sum(tests_db[tests_db['test_name'].isin(sel)]['price']); disc = st.number_input("Discount")
                st.write(f"### Final Amount: LKR {gross - disc}")
                if st.form_submit_button("SAVE BILL"):
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, gender, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, name, age, gen, ",".join(sel), gross, disc, gross-disc, str(date.today()), "Active"))
                    conn.commit(); st.success(f"Bill Saved: {ref}")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC LIMIT 15", conn)
            for _, b in bills.iterrows():
                st.write(f"**{b['name']}** | {b['ref_no']} | {b['tests']}")

    # --- TECHNICIAN ROLE ---
    elif st.session_state.user_role == "Technician":
        if st.session_state.get('editing_ref'):
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            res_data = {}
            with st.form("ws"):
                st.subheader(f"Full Worksheet: {row['name']}")
                for comp in get_fbc_details(row['age_y'], row['gender']):
                    res_data[comp['label']] = st.text_input(comp['label'], key=comp['label'])
                comment = st.text_area("Report Comments")
                if st.form_submit_button("AUTHORIZE ALL"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today()), json.dumps(["FBC"]), comment))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                    conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending", "Completed & Bulk Print"])
            with t1:
                pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
                for _, r in pending.iterrows():
                    if st.button(f"LOAD: {r['name']} ({r['ref_no']})", use_container_width=True):
                        st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                done = pd.read_sql_query("SELECT b.*, r.data, r.comment FROM billing b JOIN results r ON b.ref_no = r.bill_ref", conn)
                for _, r in done.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.write(f"**{r['name']}** | {r['tests']}")
                        c2.download_button("Bulk Print A4", create_pdf(r, json.loads(r['data']), st.session_state.username, ["FBC"], r['comment']), f"Report_{r['ref_no']}.pdf")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
conn.close()
