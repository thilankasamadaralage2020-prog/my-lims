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

def show_logo(width=150):
    if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=width)
    else: st.title("LIFE CARE LABORATORY")

# --- DATA STRUCTURES ---
def get_fbc_structure(age_y, gender):
    components = ["Total White Cell Count (WBC)", "Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils", "Hemoglobin (Hb)", "Red Blood Cell (RBC)", "HCT / PCV", "MCV", "MCH", "MCHC", "RDW", "Platelet Count"]
    units = {"Total White Cell Count (WBC)": "cells/cu/mm", "Neutrophils": "%", "Lymphocytes": "%", "Monocytes": "%", "Eosinophils": "%", "Basophils": "%", "Hemoglobin (Hb)": "g/dL", "Red Blood Cell (RBC)": "10^6/uL", "HCT / PCV": "%", "MCV": "fL", "MCH": "pg", "MCHC": "g/dL", "RDW": "%", "Platelet Count": "10^3/uL"}
    if age_y < 5:
        ranges = {"Total White Cell Count (WBC)": "5000 - 13000", "Neutrophils": "25 - 45", "Lymphocytes": "45 - 65", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "10.5 - 14.0", "Red Blood Cell (RBC)": "3.8 - 5.2", "HCT / PCV": "32 - 42", "MCV": "75 - 90", "MCH": "24 - 30", "MCHC": "32 - 36", "RDW": "11.5 - 15.0", "Platelet Count": "150 - 450"}
    else:
        ranges = {"Total White Cell Count (WBC)": "4000 - 11000", "Neutrophils": "40 - 75", "Lymphocytes": "20 - 45", "Monocytes": "02 - 10", "Eosinophils": "01 - 06", "Basophils": "00 - 01", "Hemoglobin (Hb)": "13.5 - 17.5" if gender == "Male" else "12.0 - 15.5", "Red Blood Cell (RBC)": "4.5 - 5.5" if gender == "Male" else "3.8 - 4.8", "HCT / PCV": "40 - 52" if gender == "Male" else "36 - 47", "MCV": "80 - 100", "MCH": "27 - 32", "MCHC": "32 - 36", "RDW": "11.5 - 14.5", "Platelet Count": "150 - 410"}
    return [{"label": c, "unit": units[c], "range": ranges.get(c, "")} for c in components]

UFR_DROPDOWNS = {
    "Colour": ["Pale yellow", "Yellow", "Reddish yellow", "Amber", "Straw yellow", "Blood stained"],
    "Appearance": ["Clear", "Slightly turbid", "Turbid"],
    "Specific Gravity": ["1.010", "1.015", "1.020", "1.025", "1.030"],
    "PH": ["5.5", "6.0", "6.5", "7.5", "8.0"],
    "Urine sugar": ["Nil", "Trace", "Present+", "Present ++", "Present+++"],
    "Ketone bodies": ["Nil", "Trace", "Present+", "Present ++", "Present+++"],
    "Bilirubin": ["Nil", "Trace", "Present+", "Present ++", "Present+++"],
    "Urobilinogen": ["Present in normal amount", "Present in slightly increasing amount", "Present in increase in amount"],
    "Pus cells": ["Occasional", "1-2", "2-4", "4-6", "6-8", "8-10", "10-15", "15-20", "20-30", "30-40", "40-50", "50-60", "Moderately field full", "Approximately 100", "Field full", ">100"],
    "Red cells": ["Nil", "Occasional", "1-2", "2-4", "4-6", "6-8", "8-10", "10-15", "15-20", "20-30", "30-40", "40-50", "50-60", "Moderately field full", "Approximately 100", "Field full", ">100"],
    "Epithelial cells": ["Few", "+", "++", "+++", "++++"]
}

# --- PDF GENERATOR ---
def create_pdf(bill_row, results_dict=None, auth_user=None, is_report=False, comment="", format_used="FBC"):
    try:
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
            if format_used == "FBC":
                pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "FULL BLOOD COUNT", ln=True, align='C'); pdf.ln(5)
                pdf.set_font("Arial", 'B', 9); pdf.cell(60, 9, "  Component", 0, 0, 'L'); pdf.cell(25, 9, "Result", 0, 0, 'C'); pdf.cell(35, 9, "Absolute Count", 0, 0, 'C'); pdf.cell(20, 9, "Unit", 0, 0, 'C'); pdf.cell(50, 9, "Reference Range", 0, 1, 'C')
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
                fbc_data = get_fbc_structure(bill_row['age_y'], bill_row['gender'])
                try: wbc_val = float(results_dict.get("Total White Cell Count (WBC)", 0))
                except: wbc_val = 0
                for item in fbc_data:
                    if item['label'] == "Neutrophils":
                        pdf.ln(2); pdf.set_font("Arial", 'BU', 10); pdf.cell(0, 7, "Differential Count", ln=True); pdf.set_font("Arial", '', 10)
                    if item['label'] == "Hemoglobin (Hb)":
                        pdf.ln(4); pdf.set_font("Arial", 'BU', 10); pdf.cell(0, 7, "RBC Indices", ln=True); pdf.set_font("Arial", '', 10)
                    res_val = results_dict.get(item['label'], "")
                    abs_count = ""
                    if item['label'] in ["Neutrophils", "Lymphocytes", "Monocytes", "Eosinophils", "Basophils"]:
                        try: abs_count = f"{(float(res_val) / 100) * wbc_val:.0f}"
                        except: abs_count = "-"
                    pdf.cell(60, 7, f"  {item['label']}", 0); pdf.cell(25, 7, str(res_val), 0, 0, 'C'); pdf.cell(35, 7, str(abs_count), 0, 0, 'C'); pdf.cell(20, 7, item['unit'], 0, 0, 'C'); pdf.cell(50, 7, item['range'], 0, 1, 'C')
            
            elif format_used == "UFR":
                pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "URINE FULL REPORT", ln=True, align='C'); pdf.ln(5)
                pdf.set_font("Arial", 'B', 10); pdf.cell(80, 9, "  Description", 0, 0, 'L'); pdf.cell(70, 9, "Result", 0, 0, 'L'); pdf.cell(40, 9, "Unit", 0, 1, 'C')
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
                sections = [("Macroscopic Examinations", ["Colour", "Appearance", "Specific Gravity", "PH"]), ("Chemical Findings", ["Urine sugar", "Ketone bodies", "Bilirubin", "Urobilinogen"]), ("Microscopic Examination", ["Pus cells", "Red cells", "Epithelial cells", "Casts", "Crystals"])]
                for sec_name, comps in sections:
                    pdf.ln(2); pdf.set_font("Arial", 'BU', 10); pdf.cell(0, 7, sec_name, ln=True); pdf.set_font("Arial", '', 10)
                    for c in comps:
                        pdf.cell(80, 7, f"  {c}", 0); pdf.cell(70, 7, str(results_dict.get(c, "")), 0, 0, 'L'); u_val = "/H.P.F" if c in ["Pus cells", "Red cells"] else ""; pdf.cell(40, 7, u_val, 0, 1, 'C')

            elif format_used == "Serum Creatinine":
                pdf.set_font("Arial", 'B', 14); pdf.cell(0, 10, "BIOCHEMISTRY REPORT", ln=True, align='C'); pdf.ln(5)
                pdf.set_font("Arial", 'B', 10); pdf.cell(80, 9, "  Test Description", 0, 0, 'L'); pdf.cell(40, 9, "Result", 0, 0, 'C'); pdf.cell(30, 9, "Unit", 0, 0, 'C'); pdf.cell(40, 9, "Ref. Range", 0, 1, 'C')
                pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
                cre_ref = "0.90 - 1.30" if bill_row['gender'] == "Male" else "0.65 - 1.10"
                pdf.set_font("Arial", '', 10)
                pdf.cell(80, 7, "  Serum Creatinine", 0); pdf.cell(40, 7, str(results_dict.get("Serum Creatinine", "")), 0, 0, 'C'); pdf.cell(30, 7, "mg/dL", 0, 0, 'C'); pdf.cell(40, 7, cre_ref, 0, 1, 'C')
                
                if "eGFR" in results_dict and results_dict["eGFR"]:
                    pdf.cell(80, 7, "  eGFR (MDRD)", 0); pdf.cell(40, 7, str(results_dict.get("eGFR", "")), 0, 0, 'C'); pdf.cell(30, 7, "mL/min/1.73m2", 0, 0, 'C'); pdf.cell(40, 7, "> 60", 0, 1, 'C')
                    # CKD Classification Box
                    pdf.ln(10); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 6, "Chronic Kidney Disease (CKD) Stages:", ln=True)
                    pdf.set_font("Arial", '', 8); ckd_txt = (
                        "0) Normal kidney function - GFR above 90ml/min/1.73m^2 and no proteinuria.\n"
                        "1) CKD1 - GFR above 90ml/min/1.73m^2 with evidence of kidney damage.\n"
                        "2) CKD2 (Mid) - GFR of 60 to 89 ml/min/1.73m^2 with evidence of kidney damage.\n"
                        "3) CKD3 (Moderate) - GFR of 30 to 59 ml/min/1.73m^2\n"
                        "4) CKD4 (Severe) - GFR of 15 to 29 ml/min/1.73m^2\n"
                        "5) CKD5 kidney failure - GFR less than 15 ml/min/1.73m^2 (CKD5D for dialysis patients)"
                    )
                    pdf.rect(10, pdf.get_y(), 190, 32); pdf.set_xy(12, pdf.get_y() + 2); pdf.multi_cell(186, 4.5, ckd_txt); pdf.set_y(pdf.get_y() + 5)

            pdf.ln(5); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 7, "Comments / Remarks:", ln=True)
            pdf.set_font("Arial", '', 10); pdf.rect(10, pdf.get_y(), 190, 20); pdf.set_y(pdf.get_y() + 2); pdf.set_x(12); pdf.multi_cell(186, 5, comment if comment else "N/A")
            pdf.ln(15); pdf.set_font("Arial", 'B', 10); pdf.cell(0, 10, f"Authorized by: {auth_user}", 0, 1, 'R')
        else:
            pdf.set_font("Arial", 'B', 12); pdf.cell(0, 10, "INVOICE", ln=True, align='C'); pdf.ln(5)
            pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Description", 0); pdf.cell(50, 8, "Amount (LKR)", 0, 1, 'R')
            pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(2)
            pdf.set_font("Arial", '', 10); pdf.cell(140, 8, bill_row['tests'], 0); pdf.cell(50, 8, f"{bill_row['total']:,.2f}", 0, 1, 'R')
            pdf.cell(140, 8, "Discount", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", 0, 1, 'R')
            pdf.set_font("Arial", 'B', 10); pdf.cell(140, 8, "Net Amount", 0, 0, 'R'); pdf.cell(50, 8, f"{bill_row['final_amount']:,.2f}", 0, 1, 'R')
        
        return pdf.output(dest='S').encode('latin-1', 'ignore')
    except Exception as e:
        return f"PDF Error: {str(e)}".encode('latin-1')

st.set_page_config(page_title="Life Care LIMS", layout="wide")
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'editing_ref' not in st.session_state: st.session_state.editing_ref = None

if not st.session_state.logged_in:
    with st.columns([1, 1, 1])[1]:
        show_logo(200); st.subheader("Login to Life Care")
        with st.form("login"):
            u = st.text_input("User"); p = st.text_input("Pass", type="password"); r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone(): st.session_state.update({'logged_in': True, 'user_role': r, 'username': u}); st.rerun()
                else: st.error("Access Denied")
else:
    # --- ADMIN ROLE ---
    if st.session_state.user_role == "Admin":
        st.sidebar.subheader("Admin Menu")
        choice = st.sidebar.radio("Navigate", ["Users", "Doctors", "Tests"])
        if choice == "Users":
            with st.form("u"):
                un = st.text_input("Name"); pw = st.text_input("Pass"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Save"): c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            
            st.write("### Current Users")
            u_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            for i, r in u_df.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**{r['username']}**")
                col2.write(r['role'])
                if r['username'] != 'admin': # Admin can't delete themselves
                    if col3.button("🗑️ Delete", key=f"del_{r['username']}"):
                        c.execute("DELETE FROM users WHERE username=?", (r['username'],))
                        conn.commit()
                        st.rerun()
                else:
                    col3.write("🛡️ Protected")

        elif choice == "Doctors":
            dn = st.text_input("Doctor Name")
            if st.button("Add"): c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM doctors", conn))
        elif choice == "Tests":
            tn = st.text_input("Test"); tp = st.number_input("Price")
            if st.button("Save"): c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ROLE ---
    elif st.session_state.user_role == "Billing":
        show_logo(100); st.subheader("📝 Billing Dashboard")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); pname = c2.text_input("Name")
            ay = c1.number_input("Age (Y)", 0); am = c2.number_input("Age (M)", 0)
            gen = c1.selectbox("Gender", ["Male", "Female"]); mob = c2.text_input("Mobile")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            pdoc = st.selectbox("Doctor", ["Self"] + docs)
            t_db = pd.read_sql_query("SELECT * FROM tests", conn)
            sel = st.multiselect("Tests", [f"{r['test_name']} - {r['price']}" for _, r in t_db.iterrows()])
            gross = sum([float(s.split(" - ")[-1]) for s in sel]); disc = st.number_input("Discount (LKR)", 0.0); final = gross - disc
            st.info(f"Net Payable: {final:,.2f}")
            if st.button("SAVE BILL", use_container_width=True):
                if pname and sel:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"; tn = ", ".join([s.split(" - ")[0] for s in sel])
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, pname, ay, am, gen, mob, pdoc, tn, gross, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit(); st.success(f"Saved: {ref}")

    # --- TECHNICIAN ROLE ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 Technician Workspace")
        if st.session_state.editing_ref:
            row = pd.read_sql_query(f"SELECT * FROM billing WHERE ref_no='{st.session_state.editing_ref}'", conn).iloc[0]
            billed_tests = row['tests'].upper()
            results = {}
            with st.form("res_f"):
                if "FBC" in billed_tests:
                    f_struct = get_fbc_structure(row['age_y'], row['gender'])
                    for item in f_struct: results[item['label']] = st.text_input(item['label'])
                    f_type = "FBC"
                elif "UFR" in billed_tests:
                    for cn in ["Colour", "Appearance", "Specific Gravity", "PH", "Urine sugar", "Ketone bodies", "Bilirubin", "Urobilinogen", "Pus cells", "Red cells", "Epithelial cells"]: results[cn] = st.selectbox(cn, UFR_DROPDOWNS[cn])
                    results["Casts"] = st.text_input("Casts"); results["Crystals"] = st.text_input("Crystals"); f_type = "UFR"
                elif "CREATININE" in billed_tests:
                    cre_v = st.text_input("Serum Creatinine (mg/dL)")
                    results["Serum Creatinine"] = cre_v
                    if row['age_y'] >= 18:
                        if st.checkbox("Calculate eGFR?"):
                            try:
                                scr = float(cre_v); age = row['age_y']; egfr = 175 * (scr**-1.154) * (age**-0.203)
                                if row['gender'] == "Female": egfr *= 0.742
                                results["eGFR"] = round(egfr, 2); st.success(f"Calculated eGFR: {results['eGFR']}")
                            except: st.warning("Invalid value")
                        else: results["eGFR"] = st.text_input("eGFR (Optional)")
                    f_type = "Serum Creatinine"
                else: f_type = "General"
                u_comm = st.text_area("Report Comments")
                if st.form_submit_button("AUTHORIZE"):
                    c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?,?,?)", (row['ref_no'], json.dumps(results), st.session_state.username, str(date.today()), f_type, u_comm))
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (row['ref_no'],)); conn.commit(); st.session_state.editing_ref = None; st.rerun()
            if st.button("Cancel"): st.session_state.editing_ref = None; st.rerun()
        else:
            t1, t2 = st.tabs(["Pending Tests", "Completed Reports"])
            with t1:
                p_data = pd.read_sql_query("SELECT * FROM billing WHERE status='Active' ORDER BY id DESC", conn)
                for _, r in p_data.iterrows():
                    with st.container(border=True):
                        cl1, cl2 = st.columns([4, 1])
                        cl1.write(f"**{r['name']}** ({r['ref_no']}) - {r['tests']}")
                        if cl2.button("Enter Results", key=f"e_{r['ref_no']}"): st.session_state.editing_ref = r['ref_no']; st.rerun()
            with t2:
                c_data = pd.read_sql_query("SELECT b.*, r.data, r.authorized_by, r.comment, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed' ORDER BY b.id DESC LIMIT 15", conn)
                for _, r in c_data.iterrows():
                    with st.container(border=True):
                        cl1, cl2 = st.columns([4, 1])
                        cl1.write(f"**{r['name']}** ({r['ref_no']}) - {r['tests']}")
                        cl2.download_button("Download", create_pdf(r, json.loads(r['data']), r['authorized_by'], True, r['comment'], r['format_used']), f"Rep_{r['ref_no']}.pdf", key=f"dl_{r['ref_no']}")

    # --- SATELLITE ROLE ---
    elif st.session_state.user_role == "Satellite":
        show_logo(100); st.subheader("📡 Satellite Portal")
        reps = pd.read_sql_query("SELECT b.*, r.data, r.authorized_by, r.comment, r.format_used FROM billing b JOIN results r ON b.ref_no = r.bill_ref ORDER BY b.id DESC LIMIT 20", conn)
        for _, r in reps.iterrows():
            with st.container(border=True):
                st.write(f"**{r['name']}** ({r['ref_no']}) | Tests: {r['tests']}")
                st.download_button("Download Report", create_pdf(r, json.loads(r['data']), r['authorized_by'], True, r['comment'], r['format_used']), f"Rep_{r['ref_no']}.pdf", key=f"s_{r['ref_no']}")

    if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
conn.close()
