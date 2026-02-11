import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    # අලුත්ම version එකක් භාවිතා කිරීමෙන් column ගැටළු මගහැරේ
    conn = sqlite3.connect('lifecare_final_v31.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, ref_no TEXT, salute TEXT, name TEXT, age_y INTEGER, age_m INTEGER,
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Default Admin එකතු කිරීම
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- APP CONFIG ---
st.set_page_config(page_title="Life Care LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>LIFE CARE LABORATORY</h2>", unsafe_allow_html=True)
    with st.form("login_box"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Role", ["Admin", "Billing", "Technician"])
        if st.form_submit_button("LOGIN", use_container_width=True):
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (u, p, r))
            if c.fetchone():
                st.session_state.update({'logged_in': True, 'user_role': r, 'username': u})
                st.rerun()
            else:
                st.error("Invalid Credentials")

else:
    # Sidebar
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        menu = st.sidebar.selectbox("Admin Menu", ["User Management", "Doctor Management", "Test Management"])
        
        if menu == "User Management":
            st.subheader("👥 User Management")
            with st.form("u"):
                un = st.text_input("Username"); pw = st.text_input("Password"); rl = st.selectbox("Role", ["Admin", "Billing", "Technician"])
                if st.form_submit_button("Create User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (un, pw, rl)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM users", conn).itertuples():
                c1, c2, c3 = st.columns([3,2,1])
                c1.write(row.username); c2.write(row.role)
                if row.username != st.session_state.username:
                    if c3.button("🗑️", key=row.username):
                        c.execute("DELETE FROM users WHERE username=?", (row.username,)); conn.commit(); st.rerun()

        elif menu == "Doctor Management":
            st.subheader("👨‍⚕️ Doctor Management")
            with st.form("d"):
                dn = st.text_input("Doctor Name")
                if st.form_submit_button("Add Doctor"):
                    c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (dn,)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM doctors", conn).itertuples():
                c1, c2 = st.columns([5, 1])
                c1.write(row.doc_name)
                if c2.button("🗑️", key=f"d_{row.id}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (row.id,)); conn.commit(); st.rerun()

        elif menu == "Test Management":
            st.subheader("🧪 Test Management")
            with st.form("t"):
                tn = st.text_input("Test Name"); tp = st.number_input("Price (LKR)", min_value=0.0)
                if st.form_submit_button("Save Test"):
                    c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (tn, tp)); conn.commit(); st.rerun()
            
            for row in pd.read_sql_query("SELECT * FROM tests", conn).itertuples():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(row.test_name); c2.write(f"LKR {row.price:,.2f}")
                if c3.button("🗑️", key=f"t_{row.test_name}"):
                    c.execute("DELETE FROM tests WHERE test_name=?", (row.test_name,)); conn.commit(); st.rerun()

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📝 New Registration")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            salute = col1.selectbox("Salute", ["Mr", "Mrs", "Miss", "Baby", "Rev"])
            p_name = col2.text_input("Patient Name")
            ay = col1.number_input("Age (Years)", 0, 120, 0)
            am = col2.number_input("Age (Months)", 0, 11, 0)
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
        ca.metric("Total Bill", f"LKR {full_amt:,.2f}")
        disc = cb.number_input("Discount (LKR)", 0.0)
        final = full_amt - disc
        cc.metric("Final Amount", f"LKR {final:,.2f}")

        if st.button("Save and Print Bill", use_container_width=True):
            if p_name and selected:
                ref = f"LC{datetime.now().strftime('%y%m%d%H%M%S')}"
                t_names = ", ".join([s.split(" - LKR")[0] for s in selected])
                # මෙහි column ගණන 16 කි. (id, ref, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final, date, user, status)
                try:
                    query = "INSERT INTO billing (ref_no, salute, name, age_y, age_m, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                    c.execute(query, (ref, salute, p_name, ay, am, p_gen, p_mob, p_doc, t_names, full_amt, disc, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success(f"✅ Bill Saved! Reference: {ref}")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("කරුණාකර නම සහ පරීක්ෂණ ඇතුළත් කරන්න.")

    # --- TECHNICIAN ---
    elif st.session_state.user_role == "Technician":
        st.subheader("🔬 Lab Reports")
        st.write("පරීක්ෂණ ප්‍රතිඵල ඇතුළත් කිරීමේ අංශය.")

conn.close()
