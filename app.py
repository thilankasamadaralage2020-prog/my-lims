import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v32.db', check_same_thread=False)
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

# --- BILL PDF GENERATOR ---
def create_bill_pdf(bill_row):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 5, "N0 10, Main Street, Location | Tel: 0112XXXXXX", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "PATIENT INVOICE", ln=True, border='B')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Patient: {bill_row['salute']} {bill_row['name']}")
    pdf.cell(100, 7, f"Ref No: {bill_row['ref_no']}", ln=True, align='R')
    pdf.cell(100, 7, f"Age: {bill_row['age_y']}Y {bill_row['age_m']}M / {bill_row['gender']}")
    pdf.cell(100, 7, f"Date: {bill_row['date']}", ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Test Description", border=1)
    pdf.cell(50, 8, "Amount (LKR)", border=1, ln=True, align='R')
    
    pdf.set_font("Arial", '', 10)
    for test in bill_row['tests'].split(", "):
        pdf.cell(140, 8, test, border=1)
        pdf.cell(50, 8, "-", border=1, ln=True, align='R') # Simplified for now
        
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(140, 8, "Total Amount:", align='R')
    pdf.cell(50, 8, f"{bill_row['total']:,.2f}", ln=True, align='R')
    pdf.cell(140, 8, "Discount:", align='R')
    pdf.cell(50, 8, f"{bill_row['discount']:,.2f}", ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Final Amount (LKR):", align='R')
    pdf.cell(50, 10, f"{bill_row['final_amount']:,.2f}", ln=True, align='R', border='T')
    
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    # Login Section
    st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
        if st.form_submit_button("LOGIN"):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else: st.error("Invalid Login")
else:
    # Sidebar
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- BILLING DASHBOARD ---
    if st.session_state.user_role == "Billing":
        tab1, tab2 = st.tabs(["📝 New Registration", "📂 Saved Bills"])
        
        with tab1:
            st.subheader("Create New Bill")
            with st.container(border=True):
                c1, c2 = st.columns(2)
                salute = c1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
                p_name = c2.text_input("Patient Name")
                ay = c1.number_input("Age (Years)", 0, 120, 0)
                am = c2.number_input("Age (Months)", 0, 11, 0)
                p_gen = c1.selectbox("Gender", ["Male", "Female"])
                p_mob = c2.text_input("Mobile No")
                docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
                p_doc = st.selectbox("Doctor", ["Self"] + docs)

            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            test_opts = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
            selected = st.multiselect("Select Tests", test_opts)
            
            total = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
            disc = st.number_input("Discount (LKR)", 0.0)
            final = total - disc
            st.metric("Final Amount", f"LKR {final:,.2f}")

            if st.button("Save Bill", use_container_width=True):
                if p_name and selected:
                    ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                    t_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                    query = "INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                    c.execute(query, (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, t_names, total, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success("✅ Bill Saved Successfully! Go to 'Saved Bills' to download.")
                else: st.warning("Please enter name and select tests.")

        with tab2:
            st.subheader("Manage Saved Bills")
            saved_bills = pd.read_sql_query("SELECT * FROM billing ORDER BY id DESC", conn)
            
            if not saved_bills.empty:
                for index, row in saved_bills.iterrows():
                    with st.expander(f"📄 {row['ref_no']} - {row['name']} ({row['date']})"):
                        col_i, col_j = st.columns([3, 1])
                        col_i.write(f"**Tests:** {row['tests']}")
                        col_i.write(f"**Amount:** LKR {row['final_amount']:,.2f}")
                        
                        # Generate PDF for this specific row
                        bill_pdf = create_bill_pdf(row)
                        col_j.download_button(
                            label="📥 Download PDF",
                            data=bill_pdf,
                            file_name=f"Bill_{row['ref_no']}.pdf",
                            mime="application/pdf",
                            key=f"dl_{row['ref_no']}"
                        )
            else:
                st.info("No saved bills found.")

    # --- ADMIN ---
    elif st.session_state.user_role == "Admin":
        st.title("Admin Dashboard")
        st.write("Use the sidebar to manage Users, Doctors, and Tests.")
        # Admin menu logic remains same as previous...

conn.close()
