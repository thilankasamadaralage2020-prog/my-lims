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

# --- LAB SETTINGS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

# --- FBC & UFR DATA STRUCTURES ---
def get_fbc_structure(age_y, gender):
    return [
        {"label": "Total White Cell Count (WBC)", "unit": "cells/cu/mm", "range": "4000 - 11000"},
        {"label": "Neutrophils %", "unit": "%", "range": "40 - 75"},
        {"label": "Lymphocytes %", "unit": "%", "range": "20 - 45"},
        {"label": "Monocytes %", "unit": "%", "range": "02 - 10"},
        {"label": "Eosinophils %", "unit": "%", "range": "01 - 06"},
        {"label": "Basophils %", "unit": "%", "range": "00 - 01"},
        {"label": "Neutrophils Absolute", "unit": "cells/cu/mm", "range": "2000 - 7500"},
        {"label": "Lymphocytes Absolute", "unit": "cells/cu/mm", "range": "1000 - 4500"},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": "13.5 - 17.5" if gender == "Male" else "12.0 - 15.5"},
        {"label": "Platelet Count", "unit": "10^3/uL", "range": "150 - 410"},
        {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL", "range": "4.5 - 5.5" if gender == "Male" else "3.8 - 4.8"},
        {"label": "HCT / PCV", "unit": "%", "range": "40 - 52" if gender == "Male" else "36 - 47"},
        {"label": "MCV", "unit": "fL", "range": "80 - 100"},
        {"label": "MCH", "unit": "pg", "range": "27 - 32"},
        {"label": "MCHC", "unit": "g/dL", "range": "32 - 36"},
    ]

UFR_DROPDOWNS = {
    "Colour": ["PALE YELLOW", "YELLOW", "DARK YELLOW", "STRAW YELLOW", "AMBER", "REDDISH YELLOW", "BLOOD STAINED"],
    "Appearance": ["CLEAR", "SLIGHTLY TURBID", "TURBID"],
    "SG": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"],
    "Chemicals": ["NIL", "TRACE", "+", "++", "+++", "++++"],
    "Uro": ["PRESENT IN NORMAL AMOUNT", "INCREASED"],
    "Cells": ["NIL", "OCCASIONAL", "1 - 2", "2 - 4", "4 - 6", "6 - 8", "8 - 10", "10 - 15", "15 - 20", "FIELD FULL"],
    "Epi": ["NIL", "FEW", "+", "++", "+++"],
    "Misc": ["NIL", "PRESENT", "NOT FOUND"]
}

# --- PDF GENERATOR (STRICT ORIGINAL FORMAT) ---
def create_report_pdf(bill_row, results_dict, auth_user, formats_to_print):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    for fmt in formats_to_print:
        pdf.add_page()
        # Header Section
        if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 10, 10, 33)
        pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
        pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, LAB_ADDRESS, ln=True)
        pdf.set_x(45); pdf.cell(0, 5, f"Tel: {LAB_TEL}", ln=True)
        pdf.ln(8); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)

        # Patient Info Section (Formatted like original)
        pdf.set_font("Arial", 'B', 10); curr_y = pdf.get_y()
        pdf.cell(100, 7, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
        pdf.cell(0, 7, f"Ref. No : {bill_row['ref_no']}", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(100, 7, f"Age / Gender : {bill_row['age_y']}Y / {bill_row['gender']}")
        pdf.cell(0, 7, f"Date : {bill_row['date']}", ln=True)
        pdf.cell(100, 7, f"Ref. Doctor  : {bill_row['doctor']}")
        pdf.cell(0, 7, f"Status : COMPLETED", ln=True)
        pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

        # Test Title
        pdf.set_font("Arial", 'BU', 12); pdf.cell(0, 10, fmt.upper(), ln=True, align='C'); pdf.ln(5)

        # Table Headers
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(80, 8, "DESCRIPTION", 0); pdf.cell(35, 8, "RESULT", 0, 0, 'C')
        pdf.cell(35, 8, "UNIT", 0, 0, 'C'); pdf.cell(40, 8, "REF. RANGE", 0, 1, 'C')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(3)

        # Data Rows
        pdf.set_font("Arial", '', 10)
        if "FBC" in fmt.upper():
            fbc_items = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
            for item in fbc_items:
                val = results_dict.get(item['label'], "N/A")
                pdf.cell(80, 7, item['label'])
                pdf.set_font("Arial", 'B', 10); pdf.cell(35, 7, str(val), 0, 0, 'C')
                pdf.set_font("Arial", '', 10); pdf.cell(35, 7, item['unit'], 0, 0, 'C')
                pdf.cell(40, 7, item['range'], 0, 1, 'C')
        
        elif "UFR" in fmt.upper():
            for key, val in results_dict.items():
                pdf.cell(80, 7, key); pdf.cell(0, 7, str(val), ln=True)

        # Footer
        pdf.set_y(260); pdf.line(10, 260, 200, 260)
        pdf.set_font("Arial", 'I', 9); pdf.cell(0, 10, f"Computer generated report authorized by: {auth_user}", align='R')

    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN UI ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=200)
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                st.session_state.update({'logged_in':True, 'user_role':r, 'username':u}); st.rerun()
else:
    # --- BILLING ROLE ---
    if st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["New Bill", "Saved Bills"])
        with t1:
            with st.form("billing"):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); name = c2.text_input("Name")
                age = c1.number_input("Age (Y)", 0); gen = c2.selectbox("Gender", ["Male", "Female"])
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                doc = st.selectbox("Doctor", ["Self"]+docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", tests_db['test_name'].tolist())
                total = sum(tests_db[tests_db['test_name'].isin(sel)]['price']); disc = st.number_input("Discount")
                st.subheader(f"Total Amount: LKR {total - disc:,.2f}")
                if st.form_submit_button("SAVE BILL"):
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, gender, doctor, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", 
                              (ref, sal, name, age, gen, doc, ",".join(sel), total, disc, total-disc, str(date.today()), "Active"))
                    conn.commit(); st.success(f"Bill Saved: {ref}")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC LIMIT 10", conn)
            st.dataframe(bills)

    # --- TECHNICIAN ROLE ---
    elif st.session_state.user_role == "Technician":
        if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None
        
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            tests = row['tests'].split(",")
            results_data = {}
            with st.form("worksheet"):
                st.subheader(f"Full Worksheet for {row['name']}")
                for t in tests:
                    st.markdown(f"**Test: {t}**")
                    if "FBC" in t.upper():
                        for f in get_fbc_structure(row['age_y'], row['gender']):
                            results_data[f['label']] = st.text_input(f"{f['label']} ({f['unit']})", key=f"fbc_{f['label']}")
                    elif "UFR" in t.upper():
                        c1, c2 = st.columns(2)
                        results_data["COLOUR"] = c1.selectbox("Colour", UFR_DROPDOWNS["Colour"])
                        results_data["APPEARANCE"] = c2.selectbox("Appearance", UFR_DROPDOWNS["Appearance"])
                        results_data["SPECIFIC GRAVITY"] = c1.selectbox("SG", UFR_DROPDOWNS["SG"])
                        results_data["PH"] = c2.selectbox("PH", UFR_DROPDOWNS["PH"])
                        results_data["URINE SUGAR"] = c1.selectbox("Sugar", UFR_DROPDOWNS["Chemicals"])
                        results_data["URINE PROTEIN"] = c2.selectbox("Protein", UFR_DROPDOWNS["Chemicals"])
                        results_data["PUS CELLS"] = c1.selectbox("Pus", UFR_DROPDOWNS["Cells"])
                        results_data["RED CELLS"] = c2.selectbox("Red cells", UFR_DROPDOWNS["Cells"])
                    else:
                        results_data[t] = st.text_input("Result", key=f"g_{t}")

                if st.form_submit_button("AUTHORIZE ALL"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(results_data), st.session_state.username, str(date.today()), json.dumps(tests), ""))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                    conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending Tests", "Reports (Bulk/Single)"])
            with t1:
                p = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
                for _, r in p.iterrows():
                    if st.button(f"Load Worksheet: {r['name']} ({r['tests']})", use_container_width=True):
                        st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                d = pd.read_sql_query("SELECT b.*, r.data, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref", conn)
                for _, r in d.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.write(f"**{r['name']}** - {r['tests']}")
                        c2.download_button("Print One", create_report_pdf(r, json.loads(r['data']), st.session_state.username, [r['tests'].split(",")[0]]), f"Single_{r['ref_no']}.pdf")
                        c3.download_button("Bulk Print", create_report_pdf(r, json.loads(r['data']), st.session_state.username, json.loads(r['format_used'])), f"Bulk_{r['ref_no']}.pdf")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
conn.close()
