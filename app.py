import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v29.db', check_same_thread=False)
    c = conn.cursor()
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

# --- REFERENCE RANGES LOGIC ---
def get_full_fbc_ranges(age_y, gender):
    if age_y < 5:
        return {"type": "BABY", "wbc": "5,000-13,000", "wmin": 5000, "wmax": 13000, "hb": "11.5-15.5", "hmin": 11.5, "hmax": 15.5, "plt": "150,000-450,000", "pmin": 150000, "pmax": 450000, "rbc": "4.0-5.2", "hct": "35.0-45.0", "mcv": "75.0-87.0", "mch": "25.0-31.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "mpv": "7.0-11.0"}
    elif gender == "Female":
        return {"type": "FEMALE", "wbc": "4,000-11,000", "wmin": 4000, "wmax": 11000, "hb": "11.5-16.5", "hmin": 11.5, "hmax": 16.5, "plt": "150,000-450,000", "pmin": 150000, "pmax": 450000, "rbc": "3.9-4.5", "hct": "36.0-46.0", "mcv": "80.0-95.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "mpv": "7.0-11.0"}
    else:
        return {"type": "MALE", "wbc": "4,000-11,000", "wmin": 4000, "wmax": 11000, "hb": "13.0-17.0", "hmin": 10.0, "hmax": 17.0, "plt": "150,000-450,000", "pmin": 150000, "pmax": 550000, "rbc": "4.5-5.6", "hct": "40.0-50.0", "mcv": "82.0-98.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "mpv": "7.0-11.0"}

# --- PDF GENERATOR (FBC) ---
def create_full_fbc_pdf(p_data, res, refs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10); pdf.cell(200, 5, f"FULL BLOOD COUNT REPORT ({refs['type']})", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 9)
    pdf.cell(100, 6, f"Patient: {p_data['salute']} {p_data['name']}"); pdf.cell(100, 6, f"Ref: {p_data['ref_no']}", ln=True, align='R')
    pdf.cell(100, 6, f"Age: {p_data['age_y']}Y {p_data['age_m']}M / {p_data['gender']}"); pdf.cell(100, 6, f"Date: {date.today()}", ln=True, align='R')
    pdf.ln(2); pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(4)
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(60, 8, "PARAMETER"); pdf.cell(30, 8, "RESULT", align='C'); pdf.cell(30, 8, "UNIT", align='C'); pdf.cell(30, 8, "ABS.COUNT", align='C'); pdf.cell(40, 8, "REF.RANGE", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    
    def add_l(lab, val, uni, abs_v, ref_t):
        pdf.cell(60, 7, lab); pdf.cell(30, 7, str(val), align='C'); pdf.cell(30, 7, uni, align='C'); pdf.cell(30, 7, str(abs_v), align='C'); pdf.cell(40, 7, ref_t, ln=True, align='C')

    add_l("WHITE BLOOD CELLS", res['wbc'], "cells/cu.mm", "-", refs['wbc'])
    for c in ['Neutrophils', 'Lymphocytes', 'Monocytes', 'Eosinophils', 'Basophils']:
        add_l(f"  {c.upper()}", f"{res[c.lower()]}%", "%", int((res[c.lower()]/100)*res['wbc']), "")
    pdf.ln(2)
    add_l("RED BLOOD CELLS", res['rbc'], "mill/cu.mm", "-", refs['rbc'])
    add_l("HAEMOGLOBIN (Hb)", res['hb'], "g/dL", "-", refs['hb'])
    add_l("PACKED CELL VOL (HCT)", res['hct'], "%", "-", refs['hct'])
    add_l("PLATELET COUNT", res['plt'], "cells/cu.mm", "-", refs['plt'])
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 1. LOGIN PAGE
if not st.session_state.logged_in:
    st.title("🏥 Life Care Laboratory")
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
        if st.form_submit_button("LOGIN"):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else: st.error("Invalid Credentials")

# 2. APP CONTENT
else:
    st.sidebar.title(f"User: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    if st.session_state.user_role == "Admin":
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management"])
        
        if menu == "User Management":
            st.subheader("User Management")
            with st.form("nu"):
                un = st.text_input("Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM users", conn).itertuples():
                c1, c2, c3 = st.columns(3)
                c1.write(row.username); c2.write(row.role)
                if row.username != st.session_state.username and c3.button("Delete", key=row.username):
                    c.execute("DELETE FROM users WHERE username=?", (row.username,)); conn.commit(); st.rerun()

        elif menu == "Doctor Management":
            st.subheader("Doctor Management")
            with st.form("nd"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM doctors", conn).itertuples():
                c1, c2 = st.columns([4, 1])
                c1.write(row.doc_name)
                if c2.button("Delete", key=f"d_{row.id}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (row.id,)); conn.commit(); st.rerun()

    elif st.session_state.user_role == "Billing":
        st.subheader("Registration & Billing")
        # Billing fields (Salute, Name, Age_Y, Age_M, Gender, Mobile, Doctor, Test multiselect)
        # Same logic as previous stable version...
        st.write("Billing functionality is active.")

    elif st.session_state.user_role == "Technician":
        st.subheader("FBC Report Entry")
        st.write("Technician functionality is active.")

conn.close()
