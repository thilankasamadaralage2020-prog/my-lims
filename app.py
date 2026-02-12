import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import os

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v40.db', check_same_thread=False)
    c = conn.cursor()
    # පරණ table වලට අමතරව results table එකක් එක් කිරීම
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (bill_ref TEXT PRIMARY KEY, data TEXT, authorized_by TEXT, auth_date TEXT)''')
    # ඉතිරි tables (users, doctors, tests, billing) පෙර පරිදිම පවතී
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

LAB_NAME = "Life care laboratory Pvt (Ltd)"
LAB_ADDRESS = "In front of hospital, Kotuwegada, Katuwana"
LAB_TEL = "0773326715"

# --- UI HEADER ---
def ui_header():
    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists("logo.png"): st.image("logo.png", width=120)
    with col2:
        st.markdown(f"### {LAB_NAME}\n{LAB_ADDRESS} | Tel: {LAB_TEL}")
    st.write("---")

# --- REPORT PDF GENERATOR ---
def create_report_pdf(bill_row, results_dict, auth_user):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"): pdf.image("logo.png", 10, 8, 25)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.set_x(40); pdf.cell(0, 10, LAB_NAME.upper(), ln=True)
    pdf.set_font("Arial", '', 9); pdf.set_x(40); pdf.cell(0, 5, LAB_ADDRESS, ln=True)
    pdf.ln(10); pdf.line(10, pdf.get_y(), 200, pdf.get_y()); pdf.ln(5)
    
    # Patient Info Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(90, 7, f"Lab No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Age/Gen: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(90, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.cell(100, 7, f"Ref by: {bill_row['doctor']}")
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11); pdf.cell(0, 10, "LABORATORY TEST REPORT", ln=True, align='C'); pdf.ln(5)
    
    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, "Test Parameter", 1); pdf.cell(40, 8, "Result", 1); pdf.cell(70, 8, "Reference Range", 1, ln=True)
    
    pdf.set_font("Arial", '', 10)
    for param, val in results_dict.items():
        pdf.cell(80, 8, str(param), 1)
        pdf.cell(40, 8, str(val), 1)
        pdf.cell(70, 8, "As per lab standards", 1, ln=True)
        
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 5, f"Authorized by: {auth_user}", ln=True, align='R')
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, f"Printed on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    ui_header()
    with st.columns([1, 1.2, 1])[1]:
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN"):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Invalid Login")
else:
    # --- TECHNICIAN PORTAL ---
    if st.session_state.user_role == "Technician":
        st.title("🔬 Technician Portal")
        # බිල්පත් ලැයිස්තුව පෙන්වීම
        st.subheader("Pending & Active Jobs")
        pending_bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
        
        for i, row in pending_bills.iterrows():
            with st.expander(f"📌 {row['ref_no']} - {row['name']} ({row['tests']})"):
                st.write(f"Patient Detail: {row['age_y']}Y {row['gender']} | Doctor: {row['doctor']}")
                
                # පරීක්ෂණ අනුව results enter කිරීමට fields සෑදීම
                tests_list = row['tests'].split(", ")
                res_data = {}
                with st.form(f"form_{row['ref_no']}"):
                    st.write("Enter Results:")
                    cols = st.columns(len(tests_list) if len(tests_list) < 4 else 3)
                    for idx, t_name in enumerate(tests_list):
                        res_data[t_name] = cols[idx % 3].text_input(t_name, key=f"{row['ref_no']}_{t_name}")
                    
                    if st.form_submit_button("Authorize & Save Report"):
                        import json
                        c.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)", 
                                  (row['ref_no'], json.dumps(res_data), st.session_state.username, str(date.today())))
                        conn.commit()
                        st.success("Report Authorized Successfully!")

    # --- SATELLITE PORTAL ---
    elif st.session_state.user_role == "Satellite":
        st.title("📡 Satellite Portal")
        st.subheader("Download Authorized Reports")
        
        # Authorize කළ වාර්තා පමණක් ලබාගැනීම
        query = """
            SELECT b.*, r.data, r.authorized_by 
            FROM billing b 
            JOIN results r ON b.ref_no = r.bill_ref 
            ORDER BY b.id DESC
        """
        auth_reports = pd.read_sql_query(query, conn)
        
        if auth_reports.empty:
            st.info("No authorized reports available yet.")
        else:
            for i, row in auth_reports.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    c1.write(f"**{row['name']}**\n{row['ref_no']}")
                    c2.write(f"Date: {row['date']}\nAuth by: {row['authorized_by']}")
                    
                    import json
                    results_dict = json.loads(row['data'])
                    pdf_bytes = create_report_pdf(row, results_dict, row['authorized_by'])
                    
                    c3.download_button("📥 Print Report", pdf_bytes, f"Report_{row['ref_no']}.pdf", "application/pdf")

    # --- BILLING & ADMIN (පෙර පරිදිම පවතී - කෙටි කර දක්වා ඇත) ---
    elif st.session_state.user_role in ["Admin", "Billing"]:
        st.write(f"Logged in as {st.session_state.user_role}")
        # මෙහි පෙර ලබාදුන් Admin/Billing කේතය එලෙසම පවතී.
        if st.sidebar.button("Logout"): 
            st.session_state.logged_in = False
            st.rerun()

conn.close()
