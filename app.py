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

# --- FBC STRUCTURE WITH DYNAMIC RANGES ---
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
    
    components = [
        {"label": "Total White Cell Count (WBC)", "unit": "cells/cu/mm", "range": ranges["WBC"], "is_abs": False},
        {"label": "Neutrophils", "unit": "%", "range": ranges["Neut"], "is_abs": True},
        {"label": "Lymphocytes", "unit": "%", "range": ranges["Lymph"], "is_abs": True},
        {"label": "Monocytes", "unit": "%", "range": ranges["Mono"], "is_abs": True},
        {"label": "Eosinophils", "unit": "%", "range": ranges["Eosi"], "is_abs": True},
        {"label": "Basophils", "unit": "%", "range": ranges["Baso"], "is_abs": True},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": ranges["Hb"], "is_abs": False},
        {"label": "Platelet Count", "unit": "10^3/uL", "range": ranges["Plt"], "is_abs": False}
    ]
    return components

# --- PDF GENERATOR ---
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
        pdf.text(130, curr_y + 5, f"Ref. No : {bill_row['ref_no']}")
        pdf.text(130, curr_y + 12, f"Date   : {bill_row['date']}")
        pdf.set_y(curr_y + 20); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

        if "FBC" in fmt.upper():
            pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(3)
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(70, 8, "Test Description"); pdf.cell(25, 8, "Result", 0, 0, 'C')
            pdf.cell(35, 8, "Absolute Count", 0, 0, 'C'); pdf.cell(25, 8, "Unit", 0, 0, 'C')
            pdf.cell(35, 8, "Ref. Range", 0, 1, 'C'); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            
            pdf.set_font("Arial", '', 10)
            wbc_val = float(results_dict.get("Total White Cell Count (WBC)", 0))
            
            for comp in get_fbc_details(bill_row['age_y'], bill_row['gender']):
                res_val = results_dict.get(comp['label'], "")
                abs_val = ""
                if comp['is_abs'] and res_val and wbc_val > 0:
                    abs_val = int((float(res_val) / 100) * wbc_val)
                
                pdf.cell(70, 7, comp['label'])
                pdf.cell(25, 7, str(res_val), 0, 0, 'C')
                pdf.cell(35, 7, str(abs_val), 0, 0, 'C')
                pdf.cell(25, 7, comp['unit'], 0, 0, 'C')
                pdf.cell(35, 7, comp['range'], 0, 1, 'C')

        # Comment Box
        if comment:
            pdf.ln(10); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "Comments:", ln=True)
            pdf.set_font("Arial", '', 10); pdf.multi_cell(0, 7, comment, 1)

        pdf.set_y(260); pdf.line(10, 260, 200, 260)
        pdf.cell(0, 10, f"Authorized by: {auth_user}", align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if not st.session_state.get('logged_in'):
    with st.columns([1,1,1])[1]:
        st.title("Login")
        u = st.text_input("User"); p = st.text_input("Pass", type="password")
        if st.button("Login"): st.session_state.update({'logged_in':True, 'username':u, 'user_role':'Technician'}) # Simplified for demo
else:
    # --- TECHNICIAN WORKFLOW ---
    if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None
    
    if st.session_state.editing_ref:
        row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
        res_data = {}; st.subheader(f"FBC Entry: {row['name']}")
        with st.form("fbc_form"):
            for comp in get_fbc_details(row['age_y'], row['gender']):
                res_data[comp['label']] = st.text_input(comp['label'], key=comp['label'])
            comment = st.text_area("Report Comments")
            if st.form_submit_button("Authorize"):
                c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today()), json.dumps(["FBC"]), comment))
                c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],))
                conn.commit(); st.session_state.editing_ref = None; st.rerun()
    else:
        st.write("### Pending Bills")
        pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
        for _, r in pending.iterrows():
            if st.button(f"Load {r['name']}"): st.session_state.editing_ref = r['ref_no']; st.rerun()
        
        st.divider()
        st.write("### Completed Reports")
        done = pd.read_sql_query("SELECT b.*, r.data, r.comment, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref", conn)
        for _, r in done.iterrows():
            st.download_button(f"Print {r['name']}", create_pdf(r, json.loads(r['data']), st.session_state.username, json.loads(r['format_used']), r['comment']), f"{r['ref_no']}.pdf")
