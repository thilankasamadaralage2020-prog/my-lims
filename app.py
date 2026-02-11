import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v28.db', check_same_thread=False)
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

# --- REFERENCE RANGES LOGIC BASED ON YOUR FILES ---
def get_full_fbc_ranges(age_y, gender):
    if age_y < 5: # BABY FORMAT
        return {
            "type": "BABY",
            "wbc": "5,000 - 13,000", "wmin": 5000, "wmax": 13000,
            "rbc": "4.0 - 5.2", "hb": "11.5 - 15.5", "hmin": 11.5, "hmax": 15.5,
            "hct": "35.0 - 45.0", "mcv": "75.0 - 87.0", "mch": "25.0 - 31.0",
            "mchc": "32.0 - 36.0", "rdw": "11.5 - 14.5", "plt": "150,000 - 450,000", "pmin": 150000, "pmax": 450000, "mpv": "7.0 - 11.0"
        }
    elif gender == "Female": # FEMALE FORMAT
        return {
            "type": "FEMALE",
            "wbc": "4,000 - 11,000", "wmin": 4000, "wmax": 11000,
            "rbc": "3.9 - 4.5", "hb": "11.5 - 16.5", "hmin": 11.5, "hmax": 16.5,
            "hct": "36.0 - 46.0", "mcv": "80.0 - 95.0", "mch": "27.0 - 32.0",
            "mchc": "32.0 - 36.0", "rdw": "11.5 - 14.5", "plt": "150,000 - 450,000", "pmin": 150000, "pmax": 450000, "mpv": "7.0 - 11.0"
        }
    else: # MALE FORMAT
        return {
            "type": "MALE",
            "wbc": "4,000 - 11,000", "wmin": 4000, "wmax": 11000,
            "rbc": "4.5 - 5.6", "hb": "13.0 - 17.0", "hmin": 10.0, "hmax": 17.0,
            "hct": "40.0 - 50.0", "mcv": "82.0 - 98.0", "mch": "27.0 - 32.0",
            "mchc": "32.0 - 36.0", "rdw": "11.5 - 14.5", "plt": "150,000 - 450,000", "pmin": 150000, "pmax": 550000, "mpv": "7.0 - 11.0"
        }

# --- PDF GENERATOR (FULL FBC) ---
def create_full_fbc_pdf(p_data, res, refs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(200, 5, f"FULL BLOOD COUNT REPORT ({refs['type']})", ln=True, align='C')
    pdf.ln(8)

    # Header
    pdf.set_font("Arial", '', 9)
    pdf.cell(100, 6, f"Patient Name: {p_data['salute']} {p_data['name']}")
    pdf.cell(100, 6, f"Ref No: {p_data['ref_no']}", ln=True, align='R')
    pdf.cell(100, 6, f"Age/Gender: {p_data['age_y']}Y {p_data['age_m']}M / {p_data['gender']}")
    pdf.cell(100, 6, f"Date: {date.today()}", ln=True, align='R')
    pdf.ln(2); pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(4)

    # Table
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(60, 8, "PARAMETER"); pdf.cell(30, 8, "RESULT", align='C')
    pdf.cell(30, 8, "UNIT", align='C'); pdf.cell(30, 8, "ABS.COUNT", align='C')
    pdf.cell(40, 8, "REF.RANGE", ln=True, align='C')
    pdf.set_font("Arial", '', 9)

    def add_line(label, val, unit, abs_v, ref_t, is_bold=False):
        if is_bold: pdf.set_font("Arial", 'B', 9)
        else: pdf.set_font("Arial", '', 9)
        pdf.cell(60, 7, label); pdf.cell(30, 7, str(val), align='C')
        pdf.cell(30, 7, unit, align='C'); pdf.cell(30, 7, str(abs_v), align='C')
        pdf.cell(40, 7, ref_t, ln=True, align='C')

    # WBC Section
    add_line("WHITE BLOOD CELLS", res['wbc'], "cells/cu.mm", "-", refs['wbc'], True)
    for c in ['Neutrophils', 'Lymphocytes', 'Monocytes', 'Eosinophils', 'Basophils']:
        pct = res[c.lower()]; abs_val = int((pct/100)*res['wbc'])
        add_line(f"  {c.upper()}", f"{pct}%", "%", abs_val, "")
    
    pdf.ln(2); pdf.set_font("Arial", 'B', 9); pdf.cell(0, 7, "Hb AND RBC INDICES", ln=True); pdf.set_font("Arial", '', 9)
    
    # RBC Indices
    add_line("RED BLOOD CELLS", res['rbc'], "mill/cu.mm", "-", refs['rbc'])
    add_line("HAEMOGLOBIN (Hb)", res['hb'], "g/dL", "-", refs['hb'], True)
    add_line("PACKED CELL VOLUME (HCT)", res['hct'], "%", "-", refs['hct'])
    add_line("MEAN CORPUSCULAR VOL (MCV)", res['mcv'], "fL", "-", refs['mcv'])
    add_line("MEAN CORPUSCULAR Hb (MCH)", res['mch'], "pg", "-", refs['mch'])
    add_line("MCHC", res['mchc'], "g/dL", "-", refs['mchc'])
    add_line("RDW-CV", res['rdw'], "%", "-", refs['rdw'])
    
    pdf.ln(2)
    add_line("PLATELET COUNT", res['plt'], "cells/cu.mm", "-", refs['plt'], True)
    add_line("MEAN PLATELET VOL (MPV)", res['mpv'], "fL", "-", refs['mpv'])

    return pdf.output(dest='S').encode('latin-1')

# --- STREAMLIT DASHBOARD ---
# (Previous Database and Login logic remains same)

if 'logged_in' in st.session_state and st.session_state.logged_in:
    if st.session_state.user_role == "Technician":
        st.header("🔬 Full Blood Count - Result Entry")
        
        pending = c.execute("SELECT ref_no, name, age_y, age_m, gender, salute FROM billing WHERE status='Active'").fetchall()
        if pending:
            sel_pat = st.selectbox("Select Patient", [f"{p[0]} - {p[1]}" for p in pending])
            if sel_pat:
                ref = sel_pat.split(" - ")[0]
                p_info = [p for p in pending if p[0] == ref][0]
                refs = get_full_fbc_ranges(p_info[2], p_info[4])
                
                st.success(f"Format: {refs['type']} | Age: {p_info[2]}Y {p_info[3]}M | Gender: {p_info[4]}")
                
                with st.form("fbc_full_form"):
                    # WBC Section
                    st.subheader("WBC & Differentials")
                    col1, col2, col3 = st.columns(3)
                    wbc = col1.number_input("Total WBC", value=None, placeholder="Enter WBC...")
                    hb = col2.number_input("Haemoglobin (Hb)", value=None, placeholder="Enter Hb...")
                    plt = col3.number_input("Platelet Count", value=None, placeholder="Enter Platelets...")

                    d1, d2, d3, d4, d5 = st.columns(5)
                    nt = d1.number_input("Neut %", value=None)
                    ly = d2.number_input("Lymph %", value=None)
                    mo = d3.number_input("Mono %", value=None)
                    eo = d4.number_input("Eos %", value=None)
                    ba = d5.number_input("Baso %", value=None)

                    # RBC Indices Section
                    st.subheader("RBC Indices & Others")
                    r1, r2, r3, r4 = st.columns(4)
                    rbc = r1.number_input("RBC Count", value=None)
                    hct = r2.number_input("HCT / PCV", value=None)
                    mcv = r3.number_input("MCV", value=None)
                    mch = r4.number_input("MCH", value=None)
                    
                    r5, r6, r7 = st.columns(3)
                    mchc = r5.number_input("MCHC", value=None)
                    rdw = r6.number_input("RDW-CV", value=None)
                    mpv = r7.number_input("MPV", value=None)

                    if st.form_submit_button("Generate Full FBC Report"):
                        # Validation for Diff Count
                        if (nt or 0)+(ly or 0)+(mo or 0)+(eo or 0)+(ba or 0) != 100:
                            st.error("Error: Differential count total must be 100%!")
                        elif None in [wbc, hb, plt, rbc, hct, mcv, mch, mchc, rdw, mpv]:
                            st.error("Error: All fields are required. Please fill the results.")
                        else:
                            res_data = {
                                'wbc': wbc, 'hb': hb, 'plt': plt, 'rbc': rbc, 'hct': hct, 
                                'mcv': mcv, 'mch': mch, 'mchc': mchc, 'rdw': rdw, 'mpv': mpv,
                                'neutrophils': nt, 'lymphocytes': ly, 'monocytes': mo, 'eosinophils': eo, 'basophils': ba
                            }
                            pdf = create_full_fbc_pdf({'name':p_info[1], 'age_y':p_info[2], 'age_m':p_info[3], 'gender':p_info[4], 'ref_no':ref, 'salute':p_info[5]}, res_data, refs)
                            st.download_button("📥 Download Final Report", pdf, f"FBC_Full_{ref}.pdf", "application/pdf", use_container_width=True)
        else:
            st.warning("No pending patients found.")

conn.close()
