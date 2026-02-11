import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v23.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Default Admin
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- UTILS ---
def generate_ref_no():
    c.execute("SELECT COUNT(*) FROM billing WHERE date = ?", (str(date.today()),))
    count = c.fetchone()[0] + 1
    return f"LC/{datetime.now().strftime('%d/%m/%y')}/{count:02d}"

def get_ref_ranges(age, gender):
    if age < 5:
        return {"type": "BABY", "wbc": "5,000-13,000", "wmin": 5000, "wmax": 13000, "hb": "11.5-15.5", "hmin": 11.5, "hmax": 15.5, "plt": "150,000-450,000", "pmin": 150000, "pmax": 450000}
    elif gender == "Female":
        return {"type": "FEMALE", "wbc": "4,000-11,000", "wmin": 4000, "wmax": 11000, "hb": "11.5-16.5", "hmin": 11.5, "hmax": 16.5, "plt": "150,000-450,000", "pmin": 150000, "pmax": 450000}
    else:
        return {"type": "MALE", "wbc": "4,000-11,000", "wmin": 4000, "wmax": 11000, "hb": "13.0-17.0", "hmin": 10.0, "hmax": 17.0, "plt": "150,000-450,000", "pmin": 150000, "pmax": 550000}

# --- PDF GENERATOR (FBC) ---
def create_fbc_pdf(p_data, res, refs):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image("logo.png", 10, 8, 33)
    except: pass
    pdf.set_font("Arial", 'B', 16); pdf.cell(200, 10, "LIFE CARE LABORATORY (PVT) LTD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10); pdf.cell(200, 5, f"FULL BLOOD COUNT REPORT ({refs['type']})", ln=True, align='C')
    pdf.ln(10); pdf.set_font("Arial", '', 10)
    pdf.cell(100, 7, f"Patient: {p_data['salute']} {p_data['name']}"); pdf.cell(100, 7, f"Ref: {p_data['ref_no']}", ln=True, align='R')
    pdf.cell(100, 7, f"Age/Gender: {p_data['age']}Y / {p_data['gender']}"); pdf.cell(100, 7, f"Date: {date.today()}", ln=True, align='R')
    pdf.ln(5); pdf.cell(190, 0, "", border='T', ln=True); pdf.ln(5)
    pdf.set_font("Arial", 'B', 10); pdf.cell(60, 10, "PARAMETER"); pdf.cell(35, 10, "RESULT", align='C'); pdf.cell(35, 10, "ABS. COUNT", align='C'); pdf.cell(60, 10, "REF. RANGE", ln=True, align='C')
    
    def add_row(label, val, abs_v, ref_t, is_abn):
        pdf.set_font("Arial", 'B' if is_abn else '', 10)
        if is_abn: pdf.set_text_color(255, 0, 0)
        else: pdf.set_text_color(0, 0, 0)
        pdf.cell(60, 8, label); pdf.cell(35, 8, str(val), align='C'); pdf.cell(35, 8, str(abs_v), align='C'); pdf.cell(60, 8, ref_t, ln=True, align='C')
        pdf.set_text_color(0, 0, 0)

    add_row("WHITE BLOOD CELLS", res['wbc'], "-", refs['wbc'], res['wbc'] < refs['wmin'] or res['wbc'] > refs['wmax'])
    for c in ['Neut', 'Lymph', 'Mono', 'Eos', 'Baso']:
        pct = res[c.lower()]; abs_c = int((pct/100)*res['wbc'])
        add_row(f"  {c.upper()}", f"{pct}%", abs_c, "", False)
    pdf.ln(2)
    add_row("HAEMOGLOBIN", res['hb'], "-", refs['hb'], res['hb'] < refs['hmin'] or res['hb'] > refs['hmax'])
    add_row("PLATELET COUNT", res['plt'], "-", refs['plt'], res['plt'] < refs['pmin'] or res['plt'] > refs['pmax'])
    return pdf.output(dest='S').encode('latin-1')

# --- MAIN APP ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: pass
        st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("LOGIN", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                    st.rerun()
                else: st.error("Access Denied")
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False; st.rerun()

    # --- ADMIN DASHBOARD (FIXED) ---
    if st.session_state.user_role == "Admin":
        menu = st.sidebar.selectbox("Admin Menu", ["Test Management", "User Management", "Doctor Management", "Sales Reports"])
        
        if menu == "Test Management":
            st.subheader("🧪 Manage Tests")
            with st.form("t"):
                tn = st.text_input("Test Name")
                tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

        elif menu == "User Management":
            st.subheader("👥 System Users")
            with st.form("u"):
                nu = st.text_input("New Username"); np = st.text_input("Password")
                nr = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.form_submit_button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (nu, np, nr)); conn.commit(); st.success("User Added")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        elif menu == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Doctors")
            with st.form("d"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.success("Doctor Added")
            st.dataframe(pd.read_sql_query("SELECT * FROM doctors", conn), use_container_width=True)

        elif menu == "Sales Reports":
            st.subheader("📊 Sales Summary")
            d_pick = st.date_input("Select Date", date.today())
            sales = pd.read_sql_query(f"SELECT ref_no, name, final_amount FROM billing WHERE date='{d_pick}'", conn)
            st.dataframe(sales, use_container_width=True)
            st.metric("Total Income", f"LKR {sales['final_amount'].sum():,.2f}")

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📝 Registration & Billing")
        c1, c2, c3 = st.columns(3)
        with c1: salute = st.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"]); p_name = st.text_input("Name")
        with c2: p_age = st.number_input("Age", 0, 120); p_gender = st.selectbox("Gender", ["Male", "Female"])
        with c3: p_mob = st.text_input("Mobile"); docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]; p_doc = st.selectbox("Doctor", ["Self"] + docs)
        
        tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
        test_opt = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
        selected = st.multiselect("Select Tests", test_opt)
        
        full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
        discount = st.number_input("Discount", 0.0); final_amt = full_amt - discount
        st.metric("Final Payable", f"LKR {final_amt:,.2f}")

        if st.button("Save Bill"):
            if p_name and selected:
                ref = generate_ref_no(); t_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                c.execute("INSERT INTO billing (ref_no, salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (ref, salute, p_name, p_age, p_gender, p_mob, p_doc, t_names, full_amt, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                conn.commit(); st.success(f"Saved: {ref}")
            else: st.error("Incomplete Data")

    # --- TECHNICIAN DASHBOARD ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 FBC Report Entry")
        pending = c.execute("SELECT ref_no, name, age, gender, salute FROM billing WHERE status='Active'").fetchall()
        if pending:
            sel = st.selectbox("Select Patient", [f"{p[0]} - {p[1]}" for p in pending])
            if sel:
                ref = sel.split(" - ")[0]
                p_info = [p for p in pending if p[0] == ref][0]
                refs = get_ref_ranges(p_info[2], p_info[3])
                st.info(f"Using **{refs['type']}** Reference Ranges")
                
                with st.form("fbc_entry"):
                    c1, c2, c3 = st.columns(3); wbc = c1.number_input("WBC", value=7000); hb = c2.number_input("Hb", value=13.0); plt = c3.number_input("Platelet", value=250000)
                    st.write("Differential Counts (%)")
                    d1, d2, d3, d4, d5 = st.columns(5); nt = d1.number_input("Neut", 0, 100, 60); ly = d2.number_input("Lymph", 0, 100, 30); mo = d3.number_input("Mono", 0, 100, 6); eo = d4.number_input("Eos", 0, 100, 3); ba = d5.number_input("Baso", 0, 100, 1)
                    
                    if st.form_submit_button("Generate Report"):
                        if nt+ly+mo+eo+ba == 100:
                            res = {'wbc':wbc, 'hb':hb, 'plt':plt, 'neut':nt, 'lymph':ly, 'mono':mo, 'eos':eo, 'baso':ba}
                            pdf = create_fbc_pdf({'name':p_info[1], 'age':p_info[2], 'gender':p_info[3], 'ref_no':ref, 'salute':p_info[4]}, res, refs)
                            st.download_button("📥 Download PDF Report", pdf, f"FBC_{ref}.pdf", "application/pdf")
                        else: st.error("Differential total must be 100%")
        else: st.warning("No pending patients")

conn.close()
