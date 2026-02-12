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

# --- CONSTANTS ---
LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"
LOGO_PATH = "logo.png"

# --- DATA STRUCTURES ---
def get_fbc_details(age_y, gender):
    ranges = {
        "WBC": "5.0 - 13.0" if age_y < 5 else "4.0 - 11.0",
        "Neut": "25 - 45" if age_y < 5 else "40 - 75",
        "Lymph": "45 - 65" if age_y < 5 else "20 - 45",
        "Hb": "10.5 - 14.0" if age_y < 5 else ("13.5 - 17.5" if gender == "Male" else "12.0 - 15.5"),
        "Plt": "150 - 450" if age_y < 5 else "150 - 410"
    }
    return [
        {"label": "Total White Cell Count (WBC)", "unit": "10^3/uL", "range": ranges["WBC"], "calc": False},
        {"label": "Neutrophils", "unit": "%", "range": ranges["Neut"], "calc": True},
        {"label": "Lymphocytes", "unit": "%", "range": ranges["Lymph"], "calc": True},
        {"label": "Monocytes", "unit": "%", "range": "02 - 10", "calc": True},
        {"label": "Eosinophils", "unit": "%", "range": "01 - 06", "calc": True},
        {"label": "Basophils", "unit": "%", "range": "00 - 01", "calc": True},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": ranges["Hb"], "calc": False},
        {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL", "range": "4.5 - 5.5", "calc": False},
        {"label": "HCT / PCV", "unit": "%", "range": "40 - 52", "calc": False},
        {"label": "MCV", "unit": "fL", "range": "80 - 100", "calc": False},
        {"label": "MCH", "unit": "pg", "range": "27 - 32", "calc": False},
        {"label": "MCHC", "unit": "g/dL", "range": "32 - 36", "calc": False},
        {"label": "RDW", "unit": "%", "range": "11.5 - 14.5", "calc": False},
        {"label": "Platelet Count", "unit": "10^3/uL", "range": ranges["Plt"], "calc": False}
    ]

UFR_DROPDOWNS = {
    "COLOUR": ["PALE YELLOW", "DARK YELLOW", "STRAW YELLOW", "AMBER", "REDDISH YELLOW", "BLOOD STAINED"],
    "APPEARANCE": ["CLEAR", "SLIGHTLY TURBID", "TURBID"],
    "SG": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"],
    "CHEMICAL": ["NIL", "TRACE", "PRESENT (+)", "PRESENT (+ + )", "PRESENT (+ + + )", "PRESENT (+ + + + )"],
    "UROBILINOGEN": ["PRESENT IN NORMAL AMOUNT", "INCREASED"],
    "CELLS": ["NIL", "OCCASIONAL", "1 - 2", "2 - 4", "4 - 6", "6 - 8", "8 - 10", "10 - 15", "15 - 20", "FIELD FULL"],
    "EPI": ["NIL", "FEW", "MODERATE (+)", "PLENTY (+ +)"],
    "CRYSTALS": ["NIL", "CALCIUM OXALATES FEW", "CALCIUM OXALATES +", "URIC ACID FEW", "AMORPHOUS URATES +"]
}

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict, auth_user, formats_to_print, comment=""):
    pdf = FPDF()
    for fmt_name in formats_to_print:
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

        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, fmt_name.upper(), ln=True, align='C'); pdf.ln(3)

        if "FBC" in fmt_name.upper():
            pdf.set_font("Arial", 'B', 9)
            pdf.cell(65, 8, "Test Description"); pdf.cell(25, 8, "Result", 0, 0, 'C')
            pdf.cell(35, 8, "Absolute Count", 0, 0, 'C'); pdf.cell(30, 8, "Unit", 0, 0, 'C')
            pdf.cell(35, 8, "Ref. Range", 0, 1, 'C'); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            pdf.set_font("Arial", '', 10)
            data = results_dict.get("FBC", {})
            wbc_val = float(data.get("Total White Cell Count (WBC)", 0) or 0)
            for comp in get_fbc_details(bill_row['age_y'], bill_row['gender']):
                res_val = data.get(comp['label'], "")
                abs_val = int((float(res_val or 0)/100)*wbc_val) if comp['calc'] and res_val and wbc_val > 0 else ""
                pdf.cell(65, 7, f"  {comp['label']}"); pdf.cell(25, 7, str(res_val), 0, 0, 'C')
                pdf.cell(35, 7, str(abs_val), 0, 0, 'C'); pdf.cell(30, 7, comp['unit'], 0, 0, 'C')
                pdf.cell(35, 7, comp['range'], 0, 1, 'C')

        elif "UFR" in fmt_name.upper():
            pdf.set_font("Arial", 'B', 9); pdf.cell(80, 7, "Description"); pdf.cell(60, 7, "Result"); pdf.cell(40, 7, "Unit", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
            ufr_data = results_dict.get("UFR", {})
            for k, v in ufr_data.items():
                pdf.cell(80, 7, f"  {k}"); pdf.cell(60, 7, str(v)); pdf.cell(40, 7, "", ln=True)

        elif "CREATININE" in fmt_name.upper():
            pdf.set_font("Arial", 'B', 9); pdf.cell(80, 7, "Description"); pdf.cell(40, 7, "Result", 0, 0, 'C')
            pdf.cell(40, 7, "Unit", 0, 0, 'C'); pdf.cell(40, 7, "Ref. Range", 0, 1, 'C')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
            cr_val = results_dict.get("CREATININE", {}).get("Serum Creatinine", "")
            pdf.cell(80, 7, "  Serum Creatinine"); pdf.cell(40, 7, str(cr_val), 0, 0, 'C')
            pdf.cell(40, 7, "mg/dL", 0, 0, 'C'); pdf.cell(40, 7, "0.6 - 1.2", 0, 1, 'C')

        if comment:
            pdf.ln(5); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "Comments:", ln=True)
            pdf.set_font("Arial", '', 9); pdf.multi_cell(0, 5, comment, 1)

        pdf.set_y(265); pdf.line(10, 265, 200, 265)
        pdf.set_font("Arial", 'I', 8); pdf.cell(0, 10, f"Authorized by: {auth_user}", align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN UI ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")
if not st.session_state.get('logged_in'):
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=250)
        with st.form("login"):
            u = st.text_input("Username"); p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                res = c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r)).fetchone()
                if res: st.session_state.update({'logged_in':True, 'username':u, 'user_role':r}); st.rerun()
                else: st.error("Invalid Login")
else:
    if st.session_state.user_role == "Technician":
        st.sidebar.title(f"User: {st.session_state.username}")
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
        
        pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
        for _, r in pending.iterrows():
            with st.expander(f"ENTER RESULTS: {r['name']} ({r['ref_no']})"):
                billed_tests = r['tests'].split(",")
                final_results = {}
                for t in billed_tests:
                    st.markdown(f"**{t}**")
                    test_data = {}
                    if "FBC" in t.upper():
                        for comp in get_fbc_details(r['age_y'], r['gender']):
                            test_data[comp['label']] = st.text_input(f"{comp['label']}", key=f"{r['ref_no']}{comp['label']}")
                        final_results["FBC"] = test_data
                    elif "UFR" in t.upper():
                        test_data["COLOUR"] = st.selectbox("COLOUR", UFR_DROPDOWNS["COLOUR"], key=f"{r['ref_no']}u1")
                        test_data["APPEARANCE"] = st.selectbox("APPEARANCE", UFR_DROPDOWNS["APPEARANCE"], key=f"{r['ref_no']}u2")
                        test_data["PH"] = st.selectbox("PH", UFR_DROPDOWNS["PH"], key=f"{r['ref_no']}u3")
                        test_data["SPECIFIC GRAVITY"] = st.selectbox("SG", UFR_DROPDOWNS["SG"], key=f"{r['ref_no']}u4")
                        test_data["URINE SUGAR"] = st.selectbox("SUGAR", UFR_DROPDOWNS["CHEMICAL"], key=f"{r['ref_no']}u5")
                        test_data["URINE PROTEIN"] = st.selectbox("PROTEIN", UFR_DROPDOWNS["CHEMICAL"], key=f"{r['ref_no']}u6")
                        test_data["PUS CELLS"] = st.selectbox("PUS CELLS", UFR_DROPDOWNS["CELLS"], key=f"{r['ref_no']}u7")
                        test_data["RED CELLS"] = st.selectbox("RED CELLS", UFR_DROPDOWNS["CELLS"], key=f"{r['ref_no']}u8")
                        test_data["EPITHELIAL CELLS"] = st.selectbox("EPI CELLS", UFR_DROPDOWNS["EPI"], key=f"{r['ref_no']}u9")
                        test_data["CRYSTALS"] = st.selectbox("CRYSTALS", UFR_DROPDOWNS["CRYSTALS"], key=f"{r['ref_no']}u10")
                        final_results["UFR"] = test_data
                    elif "CREATININE" in t.upper():
                        test_data["Serum Creatinine"] = st.text_input("Serum Creatinine (mg/dL)", key=f"{r['ref_no']}cr")
                        final_results["CREATININE"] = test_data

                    if st.button(f"Authorize {t}", key=f"ath_{t}_{r['ref_no']}"):
                        cur = c.execute("SELECT data FROM results WHERE bill_ref=?", (r['ref_no'],)).fetchone()
                        existing = json.loads(cur[0]) if cur else {}
                        existing.update({t.upper(): final_results.get(t.upper(), test_data)})
                        c.execute("INSERT OR REPLACE INTO results (bill_ref, data, authorized_by, auth_date, format_used) VALUES (?,?,?,?,?)",
                                  (r['ref_no'], json.dumps(existing), st.session_state.username, str(date.today()), json.dumps(list(existing.keys()))))
                        conn.commit(); st.success(f"{t} Authorized")
                
                if st.button("Finalize All", key=f"fin_{r['ref_no']}"):
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (r['ref_no'],)); conn.commit(); st.rerun()

        st.divider()
        done = pd.read_sql_query("SELECT b.*, r.data FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed'", conn)
        for _, dr in done.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                res_dict = json.loads(dr['data'])
                c1.write(f"**{dr['name']}** ({dr['ref_no']})")
                for t_name in res_dict.keys():
                    c2.download_button(f"Print {t_name}", create_pdf(dr, res_dict, st.session_state.username, [t_name]), f"{t_name}_{dr['ref_no']}.pdf")
                c3.download_button("BULK PRINT (A4)", create_pdf(dr, res_dict, st.session_state.username, list(res_dict.keys())), f"Full_{dr['ref_no']}.pdf", type="primary")

    elif st.session_state.user_role == "Billing":
        # (Billing logic same as previous version)
        st.write("Billing Dashboard Active")
    elif st.session_state.user_role == "Admin":
        # (Admin logic same as previous version)
        st.write("Admin Dashboard Active")
