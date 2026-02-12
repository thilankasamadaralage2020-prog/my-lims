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
    ranges = {"WBC": "5.0-13.0" if age_y<5 else "4.0-11.0", "Hb": "10.5-14.0" if age_y<5 else ("13.5-17.5" if gender=="Male" else "12.0-15.5")}
    return [
        {"label": "Total White Cell Count (WBC)", "unit": "10^3/uL", "range": ranges["WBC"], "calc": False},
        {"label": "Neutrophils", "unit": "%", "range": "40-75", "calc": True},
        {"label": "Lymphocytes", "unit": "%", "range": "20-45", "calc": True},
        {"label": "Monocytes", "unit": "%", "range": "02-10", "calc": True},
        {"label": "Eosinophils", "unit": "%", "range": "01-06", "calc": True},
        {"label": "Basophils", "unit": "%", "range": "00-01", "calc": True},
        {"label": "Hemoglobin (Hb)", "unit": "g/dL", "range": ranges["Hb"], "calc": False},
        {"label": "Red Blood Cell (RBC)", "unit": "10^6/uL", "range": "4.5-5.5", "calc": False},
        {"label": "HCT / PCV", "unit": "%", "range": "40-52", "calc": False},
        {"label": "MCV", "unit": "fL", "range": "80-100", "calc": False},
        {"label": "MCH", "unit": "pg", "range": "27-32", "calc": False},
        {"label": "MCHC", "unit": "g/dL", "range": "32-36", "calc": False},
        {"label": "RDW", "unit": "%", "range": "11.5-14.5", "calc": False},
        {"label": "Platelet Count", "unit": "10^3/uL", "range": "150-410", "calc": False}
    ]

UFR_DROPDOWNS = {
    "COLOUR": ["PALE YELLOW", "DARK YELLOW", "STRAW YELLOW", "AMBER", "REDDISH YELLOW", "BLOOD STAINED"],
    "APPEARANCE": ["CLEAR", "SLIGHTLY TURBID", "TURBID"],
    "SG": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0"],
    "CHEMICAL": ["NIL", "TRACE", "PRESENT (+)", "PRESENT (++)", "PRESENT (+++)", "PRESENT (++++)"],
    "URO": ["NORMAL", "INCREASED"],
    "CELLS": ["NIL", "OCCASIONAL", "1-2", "2-4", "4-6", "6-8", "8-10", "10-15", "FIELD FULL"],
    "EPI": ["NIL", "FEW", "MODERATE", "PLENTY"],
    "CRYSTALS": ["NIL", "CALCIUM OXALATES FEW", "URIC ACID FEW"]
}

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict, auth_user, formats_to_print, comment_dict={}):
    pdf = FPDF()
    for fmt_name in formats_to_print:
        pdf.add_page()
        if os.path.exists(LOGO_PATH): pdf.image(LOGO_PATH, 12, 10, 30)
        pdf.set_font("Arial", 'B', 16); pdf.set_x(45); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
        pdf.set_font("Arial", '', 10); pdf.set_x(45); pdf.cell(0, 5, f"{LAB_ADDRESS} | {LAB_TEL}", ln=True)
        pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
        
        pdf.set_font("Arial", '', 10); cy = pdf.get_y()
        pdf.text(12, cy+5, f"Patient Name : {bill_row['salute']} {bill_row['name']}")
        pdf.text(12, cy+12, f"Age / Gender : {bill_row['age_y']}Y / {bill_row['gender']}")
        pdf.text(12, cy+19, f"Ref. Doctor  : {bill_row['doctor']}")
        pdf.text(130, cy+5, f"Ref. No : {bill_row['ref_no']}")
        pdf.text(130, cy+12, f"Date   : {bill_row['date']}")
        pdf.set_y(cy+25); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(8)

        pdf.set_font("Arial", 'B', 11); pdf.cell(0, 8, fmt_name.upper(), ln=True, align='C'); pdf.ln(3)

        if "FBC" in fmt_name.upper():
            pdf.set_font("Arial", 'B', 9); pdf.cell(65, 8, "Description"); pdf.cell(25, 8, "Result", align='C')
            pdf.cell(35, 8, "Abs Count", align='C'); pdf.cell(30, 8, "Unit", align='C'); pdf.cell(35, 8, "Ref Range", 0, 1, 'C')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
            data = results_dict.get("FBC", {})
            wbc = float(data.get("Total White Cell Count (WBC)", 0) or 0)
            for comp in get_fbc_details(bill_row['age_y'], bill_row['gender']):
                rv = data.get(comp['label'], "")
                av = int((float(rv or 0)/100)*wbc) if comp['calc'] and rv and wbc>0 else ""
                pdf.cell(65, 7, f"  {comp['label']}"); pdf.cell(25, 7, str(rv), align='C')
                pdf.cell(35, 7, str(av), align='C'); pdf.cell(30, 7, comp['unit'], align='C'); pdf.cell(35, 7, comp['range'], 0, 1, 'C')

        elif "UFR" in fmt_name.upper():
            pdf.set_font("Arial", 'B', 9); pdf.cell(80, 7, "Description"); pdf.cell(60, 7, "Result", ln=True)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2); pdf.set_font("Arial", '', 10)
            ufr = results_dict.get("UFR", {})
            for k, v in ufr.items():
                pdf.cell(80, 7, f"  {k}"); pdf.cell(60, 7, str(v), ln=True)

        elif "CREATININE" in fmt_name.upper():
            cr_d = results_dict.get("CREATININE", {})
            pdf.cell(70, 7, "  Serum Creatinine"); pdf.cell(35, 7, str(cr_d.get("Value")), align='C')
            pdf.cell(30, 7, "mg/dL", align='C'); pdf.cell(55, 7, "0.6 - 1.2", 0, 1, 'C')
            if cr_d.get("eGFR"):
                pdf.set_font("Arial", 'B', 10); pdf.cell(70, 7, "  eGFR"); pdf.cell(35, 7, str(cr_d.get("eGFR")), align='C')
                pdf.cell(30, 7, "mL/min", align='C'); pdf.cell(55, 7, "> 90", 0, 1, 'C')
            pdf.ln(5); pdf.set_font("Arial", 'B', 8); pdf.cell(0, 5, "CKD STAGES (eGFR):", ln=True)
            pdf.set_font("Arial", '', 8)
            pdf.cell(0, 4, "Stage 1: >90 | Stage 2: 60-89 | Stage 3a: 45-59 | Stage 3b: 30-44 | Stage 4: 15-29 | Stage 5: <15", ln=True)

        cmt = comment_dict.get(fmt_name.upper(), "") if isinstance(comment_dict, dict) else ""
        if cmt: pdf.ln(5); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 5, "Comments:"); pdf.set_font("Arial", '', 9); pdf.ln(5); pdf.multi_cell(0, 5, cmt, 1)
        
        pdf.set_y(265); pdf.line(10, 265, 200, 265); pdf.set_font("Arial", 'I', 8); pdf.cell(0, 10, f"Authorized by: {auth_user}", align='R')
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- MAIN UI ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if not st.session_state.get('logged_in'):
    with st.columns([1,1,1])[1]:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=250)
        with st.form("login"):
            u, p, r = st.text_input("User"), st.text_input("Pass", type="password"), st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.form_submit_button("LOGIN"):
                res = c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r)).fetchone()
                if res: st.session_state.update({'logged_in':True, 'username':u, 'user_role':r}); st.rerun()
else:
    if st.sidebar.button("← BACK / LOGOUT"): st.session_state.logged_in = False; st.rerun()

    if st.session_state.user_role == "Technician":
        pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
        for _, r in pending.iterrows():
            with st.expander(f"{r['name']} ({r['ref_no']})"):
                b_tests = r['tests'].split(","); res_map, cmt_map = {}, {}
                for t in b_tests:
                    st.markdown(f"**{t}**")
                    t_data = {}
                    if "FBC" in t.upper():
                        for comp in get_fbc_details(r['age_y'], r['gender']):
                            t_data[comp['label']] = st.text_input(f"{comp['label']}", key=f"{r['ref_no']}{comp['label']}")
                        cmt_map["FBC"] = st.text_area("FBC Comment", key=f"c_fbc_{r['ref_no']}")
                        res_map["FBC"] = t_data
                    elif "UFR" in t.upper() or "URINE FULL REPORT" in t.upper():
                        t_data["COLOUR"] = st.selectbox("COLOUR", UFR_DROPDOWNS["COLOUR"], key=f"u1_{r['ref_no']}")
                        t_data["APPEARANCE"] = st.selectbox("APPEARANCE", UFR_DROPDOWNS["APPEARANCE"], key=f"u2_{r['ref_no']}")
                        t_data["SG"] = st.selectbox("SG", UFR_DROPDOWNS["SG"], key=f"u3_{r['ref_no']}")
                        t_data["PH"] = st.selectbox("PH", UFR_DROPDOWNS["PH"], key=f"u4_{r['ref_no']}")
                        t_data["SUGAR"] = st.selectbox("SUGAR", UFR_DROPDOWNS["CHEMICAL"], key=f"u5_{r['ref_no']}")
                        t_data["PROTEIN"] = st.selectbox("PROTEIN", UFR_DROPDOWNS["CHEMICAL"], key=f"u6_{r['ref_no']}")
                        t_data["PUS CELLS"] = st.selectbox("PUS CELLS", UFR_DROPDOWNS["CELLS"], key=f"u7_{r['ref_no']}")
                        t_data["RED CELLS"] = st.selectbox("RED CELLS", UFR_DROPDOWNS["CELLS"], key=f"u8_{r['ref_no']}")
                        t_data["EPITHELIAL"] = st.selectbox("EPI CELLS", UFR_DROPDOWNS["EPI"], key=f"u9_{r['ref_no']}")
                        t_data["CRYSTALS"] = st.selectbox("CRYSTALS", UFR_DROPDOWNS["CRYSTALS"], key=f"u10_{r['ref_no']}")
                        cmt_map["UFR"] = st.text_area("UFR Comment", key=f"c_ufr_{r['ref_no']}")
                        res_map["UFR"] = t_data
                    elif "CREATININE" in t.upper():
                        v = st.text_input("Value", key=f"cr_{r['ref_no']}")
                        if v: 
                            cr = float(v); egfr = 175 * (cr**-1.154) * (r['age_y']**-0.203)
                            if r['gender'] == "Female": egfr *= 0.742
                            t_data = {"Value": v, "eGFR": round(egfr, 2)}; st.info(f"eGFR: {t_data['eGFR']}")
                        res_map["CREATININE"] = t_data

                    if st.button(f"Authorize {t}", key=f"a_{t}_{r['ref_no']}"):
                        cur = c.execute("SELECT data, comment, format_used FROM results WHERE bill_ref=?", (r['ref_no'],)).fetchone()
                        ex_d = json.loads(cur[0]) if cur and cur[0] else {}
                        ex_c = json.loads(cur[1]) if cur and cur[1] else {}
                        ex_f = json.loads(cur[2]) if cur and cur[2] else []
                        
                        ex_d.update({t.upper(): res_map.get(t.upper(), t_data)})
                        ex_c.update({t.upper(): cmt_map.get(t.upper(), "")})
                        if t.upper() not in ex_f: ex_f.append(t.upper())
                        
                        c.execute("INSERT OR REPLACE INTO results (bill_ref, data, authorized_by, auth_date, comment, format_used) VALUES (?,?,?,?,?,?)", 
                                  (r['ref_no'], json.dumps(ex_d), st.session_state.username, str(date.today()), json.dumps(ex_c), json.dumps(ex_f)))
                        conn.commit(); st.success(f"{t} Saved")
                if st.button("Finalize", key=f"f_{r['ref_no']}"):
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (r['ref_no'],)); conn.commit(); st.rerun()
        
        st.divider(); 
        res_done = c.execute("SELECT b.*, r.data, r.comment, r.format_used FROM billing b JOIN results r ON b.ref_no=r.bill_ref WHERE b.status='Completed'").fetchall()
        for dr in res_done:
            dr_dict = dict(zip([col[0] for col in c.description], dr))
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                rd = json.loads(dr_dict['data']) if dr_dict['data'] else {}
                cd = json.loads(dr_dict['comment']) if dr_dict['comment'] else {}
                fu = json.loads(dr_dict['format_used']) if dr_dict['format_used'] else list(rd.keys())
                
                c1.write(f"**{dr_dict['name']}** ({dr_dict['doctor']})")
                for tn in fu: 
                    c2.download_button(f"Print {tn}", create_pdf(dr_dict, rd, st.session_state.username, [tn], cd), f"{tn}_{dr_dict['ref_no']}.pdf")
                c3.download_button("BULK PRINT", create_pdf(dr_dict, rd, st.session_state.username, fu, cd), f"Full_{dr_dict['ref_no']}.pdf", type="primary")

    elif st.session_state.user_role == "Admin":
        st.write("### Admin Dashboard")
        t1, t2, t3 = st.tabs(["Users", "Doctors", "Tests"])
        with t1:
            nu, np, nr = st.text_input("Username"), st.text_input("Password"), st.selectbox("Role", ["Admin", "Billing", "Technician"])
            if st.button("Save User"):
                c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("User Saved")
        with t2:
            nd = st.text_input("Doc Name")
            if st.button("Add Doctor"):
                c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (nd,)); conn.commit(); st.rerun()
        with t3:
            tn, tp = st.text_input("Test Name"), st.number_input("Price")
            if st.button("Save Test"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()

    elif st.session_state.user_role == "Billing":
        st.write("### New Bill")
        with st.form("bill"):
            c1, c2 = st.columns(2)
            sal, pname = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]), c2.text_input("Name")
            age, gen = c1.number_input("Age", 0), c2.selectbox("Gender", ["Male", "Female"])
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            d_sel = st.selectbox("Doctor", ["Self"]+docs)
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            sel_t = st.multiselect("Tests", tests_db['test_name'].tolist())
            total = sum(tests_db[tests_db['test_name'].isin(sel_t)]['price'])
            disc = st.number_input("Discount")
            if st.form_submit_button("Save Bill"):
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                c.execute("INSERT INTO billing (ref_no, salute, name, age_y, gender, doctor, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, pname, age, gen, d_sel, ",".join(sel_t), total, disc, total-disc, str(date.today()), "Active"))
                conn.commit(); st.success(f"Bill: {ref}")

conn.close()
