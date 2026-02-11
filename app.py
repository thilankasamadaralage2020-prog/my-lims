import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v22.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- REFERENCE RANGES LOGIC ---
def get_ref_ranges(age, gender):
    if age < 5:
        return {
            "type": "BABY",
            "wbc": "5,000 - 13,000", "wbc_min": 5000, "wbc_max": 13000,
            "hb": "11.5 - 15.5", "hb_min": 11.5, "hb_max": 15.5,
            "plt": "150,000 - 450,000", "plt_min": 150000, "plt_max": 450000,
            "rbc": "4.0 - 5.2"
        }
    elif gender == "Female":
        return {
            "type": "FEMALE",
            "wbc": "4,000 - 11,000", "wbc_min": 4000, "wbc_max": 11000,
            "hb": "11.5 - 16.5", "hb_min": 11.5, "hb_max": 16.5,
            "plt": "150,000 - 450,000", "plt_min": 150000, "plt_max": 450000,
            "rbc": "3.9 - 4.5"
        }
    else: # Male
        return {
            "type": "MALE",
            "wbc": "4,000 - 11,000", "wbc_min": 4000, "wbc_max": 11000,
            "hb": "13.0 - 17.0", "hb_min": 10.0, "hb_max": 17.0, # ඔබ දුන් highlight සීමාවන්
            "plt": "150,000 - 450,000", "plt_min": 150000, "plt_max": 550000,
            "rbc": "4.5 - 5.6"
        }

# --- PDF REPORT GENERATION ---
def create_fbc_pdf(p_data, res, refs):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(200, 5, f"FULL BLOOD COUNT REPORT ({refs['type']})", ln=True, align='C')
    pdf.ln(10)

    # Patient Details Box
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Patient Name: {p_data['name']}")
    pdf.cell(100, 7, f"Ref No: {p_data['ref_no']}", ln=True, align='R')
    pdf.cell(100, 7, f"Age / Gender: {p_data['age']}Y / {p_data['gender']}")
    pdf.cell(100, 7, f"Date: {date.today()}", ln=True, align='R')
    pdf.ln(5); pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(5)

    # Table Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 10, "PARAMETER"); pdf.cell(35, 10, "RESULT", align='C')
    pdf.cell(35, 10, "ABS. COUNT", align='C'); pdf.cell(60, 10, "REF. RANGE", ln=True, align='C')
    
    def add_fbc_row(label, val, abs_val, ref_text, is_abn):
        pdf.set_font("Arial", 'B' if is_abn else '', 10)
        if is_abn: pdf.set_text_color(255, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 8, label); pdf.cell(35, 8, str(val), align='C')
        pdf.cell(35, 8, str(abs_val), align='C'); pdf.cell(60, 8, ref_text, ln=True, align='C')
        pdf.set_text_color(0, 0, 0)

    # WBC
    wbc_val = res['wbc']
    is_wbc_abn = wbc_val < refs['wbc_min'] or wbc_val > refs['wbc_max']
    add_fbc_row("WHITE BLOOD CELLS", wbc_val, "-", refs['wbc'], is_wbc_abn)

    # Differentials
    for cell in ['Neut', 'Lymph', 'Mono', 'Eos', 'Baso']:
        pct = res[cell.lower()]
        abs_c = int((pct/100) * wbc_val)
        add_fbc_row(f"  {cell.upper()}", f"{pct}%", abs_c, "", False)

    # Hb & Plt
    hb_val = res['hb']
    is_hb_abn = hb_val < refs['hb_min'] or hb_val > refs['hb_max']
    pdf.ln(2)
    add_fbc_row("HAEMOGLOBIN", hb_val, "-", refs['hb'], is_hb_abn)
    
    plt_val = res['plt']
    is_plt_abn = plt_val < refs['plt_min'] or plt_val > refs['plt_max']
    add_fbc_row("PLATELET COUNT", plt_val, "-", refs['plt'], is_plt_abn)

    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

# (Login logic assumed here...)
if 'user_role' in st.session_state and st.session_state.user_role == "Technician":
    st.header("🔬 Laboratory Report Entry")
    
    c.execute("SELECT ref_no, name, age, gender FROM billing WHERE status='Active'")
    pending = c.fetchall()
    
    if pending:
        selected_p = st.selectbox("Select Patient to Enter Results", [f"{p[0]} - {p[1]}" for p in pending])
        if selected_p:
            ref = selected_p.split(" - ")[0]
            # රෝගියාගේ විස්තර ලබාගැනීම
            c.execute("SELECT name, age, gender FROM billing WHERE ref_no=?", (ref,))
            p_info = c.fetchone()
            name, age, gender = p_info
            
            # ස්වයංක්‍රීයව අදාළ Format එක තෝරාගැනීම
            refs = get_ref_ranges(age, gender)
            st.info(f"Selected Format: **{refs['type']}** (Based on Age: {age}, Gender: {gender})")
            
            with st.form("result_form"):
                col1, col2 = st.columns(2)
                with col1:
                    wbc = st.number_input("Total WBC Count", min_value=0, value=7000)
                    hb = st.number_input("Haemoglobin (Hb)", min_value=0.0, value=13.0, format="%.1f")
                    plt = st.number_input("Platelet Count", min_value=0, value=250000)
                
                st.markdown("---")
                st.write("**Differential Counts (%)**")
                d1, d2, d3, d4, d5 = st.columns(5)
                neut = d1.number_input("Neut", 0, 100, 60)
                lymph = d2.number_input("Lymph", 0, 100, 30)
                mono = d3.number_input("Mono", 0, 100, 6)
                eos = d4.number_input("Eos", 0, 100, 3)
                baso = d5.number_input("Baso", 0, 100, 1)
                
                diff_total = neut + lymph + mono + eos + baso
                
                if diff_total != 100:
                    st.error(f"Error: Differential Total is {diff_total}%. It must be exactly 100%.")
                
                if st.form_submit_button("Generate Report") and diff_total == 100:
                    res = {'wbc':wbc, 'hb':hb, 'plt':plt, 'neut':neut, 'lymph':lymph, 'mono':mono, 'eos':eos, 'baso':baso}
                    p_data = {'name':name, 'age':age, 'gender':gender, 'ref_no':ref}
                    
                    pdf_bytes = create_fbc_pdf(p_data, res, refs)
                    st.download_button(f"📥 Download {refs['type']} FBC Report", pdf_bytes, f"FBC_{ref}.pdf", "application/pdf")
    else:
        st.warning("No pending patients found.")
