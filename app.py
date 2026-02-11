import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime

# --- DATABASE SETUP ---
def init_db():
    # මෙහිදී v3 ලෙස නම වෙනස් කිරීමෙන් පරණ දත්ත ගැටළු මගහැරේ
    conn = sqlite3.connect('lims_v3_secure.db', check_same_thread=False)
    c = conn.cursor()
    # Users Table
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    # Tests Table
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    # Billing Table
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Cancel Requests
    c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT, requested_by TEXT)')
    
    # පද්ධතියේ පළමු Admin වරයා සෑදීම
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- UI SETTINGS ---
st.set_page_config(page_title="Secure LIMS - Login", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔬 Laboratory Information Management System</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            st.subheader("🔑 Secure Login")
            l_user = st.text_input("Username")
            l_pw = st.text_input("Password", type="password")
            l_role = st.selectbox("Select Your Role", ["Admin", "Billing", "Technician", "Satellite"])
            submit_login = st.form_submit_button("Login to System", use_container_width=True)
            
            if submit_login:
                # Username, Password සහ Role යන තුනම එකවර පරීක්ෂා කරයි
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (l_user, l_pw, l_role))
                user_data = c.fetchone()
                
                if user_data:
                    st.session_state.update({'logged_in': True, 'user_role': l_role, 'username': l_user})
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Access Denied! Check Username, Password and Role again.")

# --- AFTER LOGIN ---
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.write(f"Level: **{st.session_state.user_role}**")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Test/Service Management", "Sales Reports", "Approvals"]
        choice = st.sidebar.selectbox("Admin Menu", menu)

        if choice == "User Management":
            st.subheader("System User Control")
            # අලුත් පරිශීලකයන් එක් කිරීමේ කොටස
            with st.expander("➕ Add New User (Staff)"):
                new_u = st.text_input("Username")
                new_p = st.text_input("Password")
                new_r = st.selectbox("Assign Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.button("Create Account"):
                    if new_u and new_p:
                        c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (new_u, new_p, new_r))
                        conn.commit()
                        st.success(f"User {new_u} added as {new_r}")
                    else: st.error("Fields cannot be empty")
            
            st.write("### Current Active Users")
            users_list = pd.read_sql_query("SELECT username, role FROM users", conn)
            st.dataframe(users_list, use_container_width=True)

        elif choice == "Test/Service Management":
            st.subheader("Manage Services & Pricing")
            t_n = st.text_input("Service Name")
            t_p = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Save/Update Service"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_n, t_p))
                conn.commit()
                st.success("Test list updated")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

    # --- 2. BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Recall", "My Summary", "Cancel Request"]
        choice = st.sidebar.selectbox("Billing Menu", menu)
        
        if choice == "New Registration":
            st.subheader("Patient Billing")
            c1, c2 = st.columns(2)
            with c1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Name")
                p_age = st.number_input("Age", 0, 120)
            with c2:
                p_gender = st.selectbox("Gender", ["Male", "Female"])
                p_mobile = st.text_input("Mobile Number")
                p_doc = st.text_input("Referral Doctor")

            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            selected = st.multiselect("Select Tests", tests_df['test_name'].tolist())
            
            subtotal = sum(tests_df[tests_df['test_name'].isin(selected)]['price'])
            st.write(f"Sub Total: Rs. {subtotal:,.2f}")
            dis = st.number_input("Discount", 0.0)
            final = subtotal - dis
            st.header(f"Grand Total: Rs. {final:,.2f}")
            
            if st.button("Save & Complete Bill"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected), subtotal, dis, final, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success("Bill Registered Successfully!")

conn.close()
