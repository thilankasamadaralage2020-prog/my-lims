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

# --- CONSTANTS & STRUCTURES ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

# FBC Structure with Ref Ranges & Absolute Counts
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

# UFR Dropdown Data
UFR_DROPDOWNS = {
    "Colour": ["PALE YELLOW", "DARK YELLOW", "STRAW YELLOW", "AMBER", "REDDISH YELLOW", "BLOOD STAINED"],
    "Appearance": ["CLEAR", "SLIGHTLY TURBID", "TURBID"],
    "Specific Gravity": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"],
    "Sugar/Protein/Ketone/Bilirubin": ["NIL", "TRACE", "+", "++", "+++", "++++"],
    "Urobilinogen": ["PRESENT IN NORMAL AMOUNT", "INCREASED"],
    "Pus/Red Cells": ["NIL", "OCCASIONAL", "1 - 2", "2 - 4", "4 - 6", "6 - 8", "8 - 10", "10 - 15", "15 - 20", "FIELD FULL"],
    "Epithelial Cells": ["NIL", "FEW", "+", "++", "+++"],
    "Crystals/Casts": ["NIL", "CALCIUM OXALATES FEW", "CALCIUM OXALATES +", "URIC ACID FEW", "AMORPHOUS URATES +"]
}

# --- PDF GENERATOR (A4) ---
def create_pdf(bill_row, results_dict, auth_user, formats_to_print):
    pdf = FPDF()
    for fmt in formats_to_print:
        pdf.add_page()
        if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 10, 10, 30)
        pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, LAB_NAME.upper(), ln=True, align='C')
        pdf.set_font("Arial", '', 9); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True, align='C')
        pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 10); pdf.cell(100, 6, f"Patient: {bill_row['salute']} {bill_row['name']}"); pdf.cell(0, 6, f"Ref: {bill_row['ref_no']}", ln=True)
        pdf.set_font("Arial", '', 10); pdf.cell(100, 6, f"Age/Gen: {bill_row['age_y']}Y / {bill_row['gender']}"); pdf.cell(0, 6, f"Date: {bill_row['date']}", ln=True)
        pdf.ln(5); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, f"{fmt.upper()}", ln=True, align='C'); pdf.ln(3)
        pdf.set_font("Arial", 'B', 10); pdf.cell(80, 7, "Test Parameter"); pdf.cell(40, 7, "Result"); pdf.cell(30, 7, "Unit"); pdf.cell(40, 7, "Ref. Range", ln=True)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
        
        # Display Results Based on Format
        if "FBC" in fmt.upper():
            for f in get_fbc_structure(bill_row['age_y'], bill_row['gender']):
                val = results_dict.get(f['label'], "")
                pdf.cell(80, 6, f['label']); pdf.cell(40, 6, str(val)); pdf.cell(30, 6, f['unit']); pdf.cell(40, 6, f['range'], ln=True)
        elif "UFR" in fmt.upper():
            for k, v in results_dict.items():
                if k in ["Colour", "Appearance", "PH", "Specific Gravity", "Urine sugar", "Pus cells", "Red cells"]:
                    pdf.cell(80, 6, k); pdf.cell(0, 6, str(v), ln=True)
        
        pdf.set_y(260); pdf.line(10, 260, 200, 260); pdf.cell(0, 10, f"Authorized by: {auth_user}", align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=200)
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password"); r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
else:
    if st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["Billing", "Saved Bills"])
        with t1:
            with st.form("bill"):
                c1, c2 = st.columns(2)
                name = c1.text_input("Name"); age = c2.number_input("Age", 0); gen = c1.selectbox("Gender", ["Male", "Female"])
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", tests_db['test_name'].tolist())
                gross = sum(tests_db[tests_db['test_name'].isin(sel)]['price'])
                disc = st.number_input("Discount")
                st.write(f"Total: {gross-disc}")
                if st.form_submit_button("Save"):
                    ref = f"LC{datetime.now().strftime('%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, name, age_y, gender, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?)", (ref, name, age, gen, ",".join(sel), gross, disc, gross-disc, str(date.today()), "Active"))
                    conn.commit(); st.success("Saved")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            st.dataframe(bills)

    elif st.session_state.user_role == "Technician":
        if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None
        
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            billed_tests = row['tests'].split(",")
            res_data = {}
            with st.form("ws"):
                st.subheader(f"Worksheet: {row['name']}")
                for t in billed_tests:
                    st.divider()
                    st.write(f"### {t}")
                    if "FBC" in t.upper():
                        for f in get_fbc_structure(row['age_y'], row['gender']):
                            res_data[f['label']] = st.text_input(f"{f['label']} ({f['unit']})", key=f"{t}_{f['label']}")
                    elif "UFR" in t.upper():
                        res_data["Colour"] = st.selectbox("Colour", UFR_DROPDOWNS["Colour"])
                        res_data["Appearance"] = st.selectbox("Appearance", UFR_DROPDOWNS["Appearance"])
                        res_data["Specific Gravity"] = st.selectbox("Specific Gravity", UFR_DROPDOWNS["Specific Gravity"])
                        res_data["PH"] = st.selectbox("PH", UFR_DROPDOWNS["PH"])
                        res_data["Urine sugar"] = st.selectbox("Urine sugar", UFR_DROPDOWNS["Sugar/Protein/Ketone/Bilirubin"])
                        res_data["Pus cells"] = st.selectbox("Pus cells", UFR_DROPDOWNS["Pus/Red Cells"])
                        res_data["Red cells"] = st.selectbox("Red cells", UFR_DROPDOWNS["Pus/Red Cells"])
                
                if st.form_submit_button("AUTHORIZE ALL"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today()), json.dumps(billed_tests), ""))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                    conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Back"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending", "Completed & Bulk Print"])
            with t1:
                pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
                for _, r in pending.iterrows():
                    if st.button(f"Enter: {r['name']} ({r['tests']})", key=r['ref_no']):
                        st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                done = pd.read_sql_query("SELECT b.*, r.data, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed'", conn)
                for _, r in done.iterrows():
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        col1.write(f"**{r['name']}** - {r['tests']}")
                        # Individual Print
                        col2.download_button("Print One", create_pdf(r, json.loads(r['data']), st.session_state.username, [r['tests'].split(",")[0]]), f"Single_{r['ref_no']}.pdf")
                        # Bulk Print (All tests in one PDF)
                        col3.download_button("Bulk Print", create_pdf(r, json.loads(r['data']), st.session_state.username, json.loads(r['format_used'])), f"Bulk_{r['ref_no']}.pdf")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
