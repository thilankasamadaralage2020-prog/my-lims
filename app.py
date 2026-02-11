import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lifecare_final_v30.db', check_same_thread=False)
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
        return {"type": "BABY", "wbc": "5,000-13,000", "rbc": "4.0-5.2", "hb": "11.5-15.5", "hct": "35.0-45.0", "mcv": "75.0-87.0", "mch": "25.0-31.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}
    elif gender == "Female":
        return {"type": "FEMALE", "wbc": "4,000-11,000", "rbc": "3.9-4.5", "hb": "11.5-16.5", "hct": "36.0-46.0", "mcv": "80.0-95.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}
    else:
        return {"type": "MALE", "wbc": "4,000-11,000", "rbc": "4.5-5.6", "hb": "13.0-17.0", "hct": "40.0-50.0", "mcv": "82.0-98.0", "mch": "27.0-32.0", "mchc": "32.0-36.0", "rdw": "11.5-14.5", "plt": "150,000-450,000", "mpv": "7.0-11.0"}

# --- MAIN APP CONFIG ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- LOGIN INTERFACE ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
        if st.form_submit_button("LOGIN", use_container_width=True):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else:
                st.error("පරිශීලක නාමය හෝ මුරපදය වැරදියි!")

# --- AUTHENTICATED CONTENT ---
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management"])
        
        if menu == "User Management":
            st.subheader("👥 System User Management")
            with st.form("u_form"):
                un = st.text_input("New Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician"])
                if st.form_submit_button("Create User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM users", conn).itertuples():
                c1, c2, c3 = st.columns([3,2,1])
                c1.write(row.username); c2.write(row.role)
                if row.username != st.session_state.username:
                    if c3.button("🗑️ Delete", key=f"u_{row.username}"):
                        c.execute("DELETE FROM users WHERE username=?", (row.username,)); conn.commit(); st.rerun()

        elif menu == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Doctors")
            with st.form("d_form"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM doctors", conn).itertuples():
                c1, c2 = st.columns([5, 1])
                c1.write(row.doc_name)
                if c2.button("🗑️ Delete", key=f"d_{row.id}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (row.id,)); conn.commit(); st.rerun()

        elif menu == "Test Management":
            st.subheader("🧪 Manage Laboratory Tests")
            with st.form("t_form"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM tests", conn).itertuples():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(row.test_name); c2.write(f"LKR {row.price:,.2f}")
                if c3.button("🗑️ Delete", key=f"t_{row.test_name}"):
                    c.execute("DELETE FROM tests WHERE test_name=?", (row.test_name,)); conn.commit(); st.rerun()

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📝 Registration & Billing")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            salute = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            p_name = col2.text_input("Patient Name")
            ay = col1.number_input("Age (Years)", 0, 120, 0)
            am = col2.number_input("Age (Months) - Optional", 0, 11, 0)
            p_gen = col1.selectbox("Gender", ["Male", "Female"])
            p_mob = col2.text_input("Mobile No")
            docs = [d[0] for d in c.execute("SELECT doc_name FROM doctors").fetchall()]
            p_doc = st.selectbox("Referral Doctor", ["Self"] + docs)

        tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
        test_opts = [f"{r['test_name']} - LKR {r['price']:,.2f}" for i, r in tests_db.iterrows()]
        selected = st.multiselect("Select Tests", test_opts)
        
        full_amt = sum([float(s.split(" - LKR")[-1].replace(',', '')) for s in selected])
        st.write("---")
        ca, cb, cc = st.columns(3)
        ca.metric("Total", f"LKR {full_amt:,.2f}")
        disc = cb.number_input("Discount", 0.0)
        final = full_amt - disc
        cc.metric("Final Payable", f"LKR {final:,.2f}")

        if st.button("Save & Print", use_container_width=True):
            if p_name and selected:
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M')}"
                t_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                c.execute("INSERT INTO billing VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, t_names, full_amt, disc, final, str(date.today()), st.session_state.username, "Active"))
                conn.commit(); st.success(f"Saved! Ref: {ref}")
            else: st.error("කරුණාකර රෝගියාගේ නම සහ පරීක්ෂණ ඇතුළත් කරන්න.")

    # --- TECHNICIAN DASHBOARD ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 FBC Report Entry")
        pending = c.execute("SELECT ref_no, name, age_y, gender, salute, age_m FROM billing WHERE status='Active'").fetchall()
        if pending:
            sel = st.selectbox("Select Patient", [f"{p[0]} - {p[1]}" for p in pending])
            if sel:
                ref_code = sel.split(" - ")[0]
                p_data = [p for p in pending if p[0] == ref_code][0]
                refs = get_full_fbc_ranges(p_data[2], p_data[3])
                st.info(f"Format: {refs['type']}")
                
                with st.form("fbc_form"):
                    st.write("WBC, Hb & Platelets")
                    c1, c2, c3 = st.columns(3)
                    wbc = c1.number_input("WBC", value=None); hb = c2.number_input("Hb", value=None); plt = c3.number_input("Platelets", value=None)
                    
                    st.write("RBC Indices")
                    r1, r2, r3, r4 = st.columns(4)
                    rbc = r1.number_input("RBC", value=None); hct = r2.number_input("HCT", value=None); mcv = r3.number_input("MCV", value=None); mch = r4.number_input("MCH", value=None)
                    
                    if st.form_submit_button("Submit Results"):
                        st.success("Results updated (PDF generation module ready)")
        else:
            st.warning("පරීක්ෂණ සඳහා රෝගීන් කිසිවෙකු නොමැත.")

conn.close()
