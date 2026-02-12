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
    "CHEMICAL": ["NIL", "TRACE", "PRESENT (+)", "PRESENT (++ )", "PRESENT (+++ )", "PRESENT (++++)"],
    "UROBILINOGEN": ["PRESENT IN NORMAL AMOUNT", "INCREASED"],
    "CELLS": ["NIL", "OCCASIONAL", "1 - 2", "2 - 4", "4 - 6", "6 - 8", "8 - 10", "10 - 15", "15 - 20", "FIELD FULL"],
    "EPI": ["NIL", "FEW", "MODERATE (+)", "PLENTY (++)"],
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
    # --- ADMIN ROLE ---
    if st.session_state.user_role == "Admin":
        st.sidebar.title("Admin Functions")
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
        
        tab1, tab2, tab3 = st.tabs(["Manage Users", "Manage Doctors", "Manage Tests"])
        
        with tab1:
            st.subheader("Add/Update User")
            with st.form("admin_user"):
                new_u = st.text_input("Username")
                new_p = st.text_input("Password")
                new_r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
                if st.form_submit_button("Save User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (new_u, new_p, new_r))
                    conn.commit(); st.success("User saved successfully")
            st.write("---")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        with tab2:
            st.subheader("Doctor Management")
            new_doc = st.text_input("Doctor Name")
            if st.button("Add Doctor"):
                c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (new_doc,))
                conn.commit(); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT id, doc_name FROM doctors", conn), use_container_width=True)

        with tab3:
            st.subheader("Test Price Management")
            with st.form("admin_test"):
                t_name = st.text_input("Test Name")
                t_price = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_name, t_price))
                    conn.commit(); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

    # --- BILLING ROLE ---
    elif st.session_state.user_role == "Billing":
        st.sidebar.title("Billing Panel")
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
        
        t1, t2 = st.tabs(["New Patient Bill", "History"])
        with t1:
            with st.form("bill_entry"):
                c1, c2 = st.columns(2)
                sal = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                pname = c2.text_input("Name")
                age = c1.number_input("Age (Y)", 0)
                gen = c2.selectbox("Gender", ["Male", "Female"])
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                d_sel = st.selectbox("Referral", ["Self"] + docs)
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                sel_tests = st.multiselect("Select Tests", tests_db['test_name'].tolist())
                gross = sum(tests_db[tests_db['test_name'].isin(sel_tests)]['price'])
                disc = st.number_input("Discount")
                st.write(f"### Net Total: LKR {gross - disc}")
                if st.form_submit_button("Generate Bill"):
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    c.execute("INSERT INTO billing (ref_no, salute, name, age_y, gender, doctor, tests, total, discount, final_amount, date, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (ref, sal, pname, age, gen, d_sel, ",".join(sel_tests), gross, disc, gross-disc, str(date.today()), "Active"))
                    conn.commit(); st.success(f"Bill Generated: {ref}")
        with t2:
            st.dataframe(pd.read_sql_query("SELECT ref_no, name, status, final_amount FROM billing ORDER BY id DESC", conn), use_container_width=True)

    # --- TECHNICIAN ROLE ---
    elif st.session_state.user_role == "Technician":
        st.sidebar.title("Lab Entry")
        if st.sidebar.button("Logout"): st.session_state.logged_in = False; st.rerun()
        
        pending = pd.read_sql_query("SELECT * FROM billing WHERE status='Active'", conn)
        for _, r in pending.iterrows():
            with st.expander(f"Patient: {r['name']} | Tests: {r['tests']}"):
                b_tests = r['tests'].split(",")
                results = {}
                for t in b_tests:
                    st.markdown(f"**Results for {t}**")
                    t_data = {}
                    if "FBC" in t.upper():
                        for comp in get_fbc_details(r['age_y'], r['gender']):
                            t_data[comp['label']] = st.text_input(f"{comp['label']}", key=f"{r['ref_no']}{comp['label']}")
                        results["FBC"] = t_data
                    elif "UFR" in t.upper():
                        t_data["COLOUR"] = st.selectbox("COLOUR", UFR_DROPDOWNS["COLOUR"], key=f"{r['ref_no']}u1")
                        t_data["APPEARANCE"] = st.selectbox("APPEARANCE", UFR_DROPDOWNS["APPEARANCE"], key=f"{r['ref_no']}u2")
                        t_data["SG"] = st.selectbox("SG", UFR_DROPDOWNS["SG"], key=f"{r['ref_no']}u3")
                        t_data["PH"] = st.selectbox("PH", UFR_DROPDOWNS["PH"], key=f"{r['ref_no']}u4")
                        t_data["SUGAR"] = st.selectbox("SUGAR", UFR_DROPDOWNS["CHEMICAL"], key=f"{r['ref_no']}u5")
                        t_data["PROTEIN"] = st.selectbox("PROTEIN", UFR_DROPDOWNS["CHEMICAL"], key=f"{r['ref_no']}u6")
                        t_data["PUS CELLS"] = st.selectbox("PUS CELLS", UFR_DROPDOWNS["CELLS"], key=f"{r['ref_no']}u7")
                        t_data["RED CELLS"] = st.selectbox("RED CELLS", UFR_DROPDOWNS["CELLS"], key=f"{r['ref_no']}u8")
                        t_data["EPITHELIAL"] = st.selectbox("EPI CELLS", UFR_DROPDOWNS["EPI"], key=f"{r['ref_no']}u9")
                        t_data["CRYSTALS"] = st.selectbox("CRYSTALS", UFR_DROPDOWNS["CRYSTALS"], key=f"{r['ref_no']}u10")
                        results["UFR"] = t_data
                    elif "CREATININE" in t.upper():
                        t_data["Serum Creatinine"] = st.text_input("Creatinine Value", key=f"{r['ref_no']}cr")
                        results["CREATININE"] = t_data
                    
                    if st.button(f"Authorize {t}", key=f"auth_{t}_{r['ref_no']}"):
                        cur = c.execute("SELECT data FROM results WHERE bill_ref=?", (r['ref_no'],)).fetchone()
                        existing = json.loads(cur[0]) if cur else {}
                        existing.update({t.upper(): results.get(t.upper(), t_data)})
                        c.execute("INSERT OR REPLACE INTO results (bill_ref, data, authorized_by, auth_date, format_used) VALUES (?,?,?,?,?)",
                                  (r['ref_no'], json.dumps(existing), st.session_state.username, str(date.today()), json.dumps(list(existing.keys()))))
                        conn.commit(); st.success(f"{t} Authorized")
                
                if st.button("Complete Report", key=f"fin_{r['ref_no']}"):
                    c.execute("UPDATE billing SET status='Completed' WHERE ref_no=?", (r['ref_no'],)); conn.commit(); st.rerun()

        st.divider()
        st.subheader("Print Section")
        done = pd.read_sql_query("SELECT b.*, r.data FROM billing b JOIN results r ON b.ref_no = r.bill_ref WHERE b.status='Completed'", conn)
        for _, dr in done.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                r_dict = json.loads(dr['data'])
                c1.write(f"**{dr['name']}** - {dr['ref_no']}")
                for tn in r_dict.keys():
                    c2.download_button(f"Print {tn}", create_pdf(dr, r_dict, st.session_state.username, [tn]), f"{tn}_{dr['ref_no']}.pdf")
                c3.download_button("BULK PRINT", create_pdf(dr, r_dict, st.session_state.username, list(r_dict.keys())), f"Full_{dr['ref_no']}.pdf", type="primary")

conn.close()
