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

# --- DATA STRUCTURES ---
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
    "Colour": ["PALE YELLOW", "DARK YELLOW", "STRAW YELLOW", "AMBER", "REDDISH YELLOW", "BLOOD STAINED"],
    "Appearance": ["CLEAR", "SLIGHTLY TURBID", "TURBID"],
    "Specific Gravity": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"],
    "Chemicals": ["NIL", "TRACE", "+", "++", "+++", "++++"],
    "Urobilinogen": ["PRESENT IN NORMAL AMOUNT", "INCREASED"],
    "Cells": ["NIL", "OCCASIONAL", "1 - 2", "2 - 4", "4 - 6", "6 - 8", "8 - 10", "10 - 15", "15 - 20", "FIELD FULL"],
    "Epi": ["NIL", "FEW", "+", "++", "+++"],
    "Misc": ["NIL", "PRESENT", "NOT FOUND"]
}

# --- PDF GENERATOR (RESTORING ORIGINAL LAYOUT) ---
def create_pdf(bill_row, results_dict, auth_user, formats_to_print, is_report=True):
    pdf = FPDF()
    for fmt in formats_to_print:
        pdf.add_page()
        # Header
        if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 12, 10, 30)
        pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
        pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
        pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        # Patient Info Box
        pdf.set_font("Arial", '', 10); curr_y = pdf.get_y()
        pdf.text(12, curr_y + 5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
        pdf.text(12, curr_y + 12, f"Age / Gender : {bill_row['age_y']}Y / {bill_row['gender']}")
        pdf.text(12, curr_y + 19, f"Ref. Doctor   : {bill_row['doctor']}")
        pdf.text(130, curr_y + 5, f"Reference No  : {bill_row['ref_no']}")
        pdf.text(130, curr_y + 12, f"Date          : {bill_row['date']}")
        pdf.set_y(curr_y + 25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

        if is_report:
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, fmt.upper(), ln=True, align='C'); pdf.ln(5)
            
            # Table Header
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(80, 8, "  Test Description", 0); pdf.cell(40, 8, "Result", 0, 0, 'C')
            pdf.cell(30, 8, "Unit", 0, 0, 'C'); pdf.cell(40, 8, "Ref. Range", 0, 1, 'C')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            pdf.set_font("Arial", '', 10)

            if "FBC" in fmt.upper():
                for f in get_fbc_structure(bill_row['age_y'], bill_row['gender']):
                    val = results_dict.get(f['label'], "")
                    pdf.cell(80, 7, f"  {f['label']}"); pdf.cell(40, 7, str(val), 0, 0, 'C')
                    pdf.cell(30, 7, f['unit'], 0, 0, 'C'); pdf.cell(40, 7, f['range'], 0, 1, 'C')
            
            elif "UFR" in fmt.upper():
                for k, v in results_dict.items():
                    pdf.cell(80, 7, f"  {k}"); pdf.cell(0, 7, str(v), ln=True)

            # Footer / Signature
            pdf.set_y(250); pdf.line(10, 250, 200, 250)
            pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
        else:
            # Invoice Layout
            pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(10)
            pdf.cell(140, 10, "Description", 1); pdf.cell(50, 10, "Amount", 1, 1, 'R')
            pdf.set_font("Arial", '', 11); pdf.cell(140, 10, bill_row['tests'], 1); pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", 1, 1, 'R')

    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
init_db()

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=200)
        with st.form("login_form"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
else:
    # --- BILLING ---
    if st.session_state.user_role == "Billing":
        t1, t2 = st.tabs(["New Bill", "Saved Bills"])
        with t1:
            with st.form("bill"):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); name = c2.text_input("Name")
                age = c1.number_input("Age (Y)", 0); gen = c2.selectbox("Gender", ["Male", "Female"])
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                doc = st.selectbox("Doctor", ["Self"]+docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel = st.multiselect("Tests", tests_db['test_name'].tolist())
                total = sum(tests_db[tests_db['test_name'].isin(sel)]['price']); disc = st.number_input("Discount")
                st.info(f"Final Amount: {total - disc}")
                if st.form_submit_button("SAVE"):
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, gender, doctor, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", 
                              (ref, sal, name, age, gen, doc, ",".join(sel), total, disc, total-disc, str(date.today()), "Active"))
                    conn.commit(); st.success(f"Saved: {ref}")
        with t2:
            bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC LIMIT 15", conn)
            for _, b in bills.iterrows():
                with st.container(border=True):
                    cl1, cl2 = st.columns([4,1]); cl1.write(f"**{b['name']}** | {b['tests']}"); cl2.download_button("Print Bill", create_pdf(b, {}, "", ["Invoice"], False), f"Bill_{b['ref_no']}.pdf")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            billed_list = row['tests'].split(",")
            res_data = {}
            with st.form("worksheet"):
                st.subheader(f"Full Worksheet: {row['name']}")
                for t in billed_list:
                    st.markdown(f"#### {t}")
                    if "FBC" in t.upper():
                        for f in get_fbc_structure(row['age_y'], row['gender']):
                            res_data[f['label']] = st.text_input(f"{f['label']} ({f['unit']})", key=f"fbc_{f['label']}")
                    elif "UFR" in t.upper():
                        c1, c2 = st.columns(2)
                        res_data["Colour"] = c1.selectbox("Colour", UFR_DROPDOWNS["Colour"])
                        res_data["Appearance"] = c2.selectbox("Appearance", UFR_DROPDOWNS["Appearance"])
                        res_data["Specific Gravity"] = c1.selectbox("Specific Gravity", UFR_DROPDOWNS["Specific Gravity"])
                        res_data["PH"] = c2.selectbox("PH", UFR_DROPDOWNS["PH"])
                        res_data["Urine sugar"] = c1.selectbox("Sugar", UFR_DROPDOWNS["Chemicals"])
                        res_data["Protein"] = c2.selectbox("Protein", UFR_DROPDOWNS["Chemicals"])
                        res_data["Pus cells"] = c1.selectbox("Pus cells", UFR_DROPDOWNS["Cells"])
                        res_data["Red cells"] = c2.selectbox("Red cells", UFR_DROPDOWNS["Cells"])
                    else:
                        res_data[t] = st.text_input("Result", key=f"gen_{t}")
                if st.form_submit_button("AUTHORIZE ALL"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today()), json.dumps(billed_list), ""))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],)); conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending Work", "Completed & Bulk Print"])
            with t1:
                pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
                for _, r in pending.iterrows():
                    if st.button(f"LOAD: {r['name']} - {r['tests']}", use_container_width=True):
                        st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                done = pd.read_sql_query("SELECT b.*, r.data, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed' ORDER BY b.id DESC", conn)
                for _, r in done.iterrows():
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.write(f"**{r['name']}** | {r['tests']}")
                        c2.download_button("Print Single", create_pdf(r, json.loads(r['data']), st.session_state.username, [r['tests'].split(",")[0]]), f"S_{r['ref_no']}.pdf")
                        c3.download_button("Bulk Print", create_pdf(r, json.loads(r['data']), st.session_state.username, json.loads(r['format_used'])), f"Bulk_{r['ref_no']}.pdf")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
conn.close()
