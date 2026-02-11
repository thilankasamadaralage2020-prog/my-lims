import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_final_v2.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT, requested_by TEXT)')
    # මුල් Admin පරිශීලකයා (මෙය පද්ධතියේ පළමු වරට පමණක් සෑදේ)
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- UI SETTINGS ---
st.set_page_config(page_title="Professional LIMS - Secure Access", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔬 Laboratory Information Management System</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Login to your Account")
        login_user = st.text_input("Username")
        login_pw = st.text_input("Password", type="password")
        # Role එක තෝරා ගැනීමට Dropdown එකක් එක් කළා
        login_role = st.selectbox("Select Your Role", ["Admin", "Billing", "Technician", "Satellite"])
        
        if st.button("Login", use_container_width=True):
            # Database එකේ Username, Password සහ Role යන තුනම ගැලපේදැයි පරීක්ෂා කිරීම
            c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (login_user, login_pw, login_role))
            res = c.fetchone()
            
            if res:
                st.session_state.update({'logged_in': True, 'user_role': login_role, 'username': login_user})
                st.success(f"Welcome {login_user}! Logging in as {login_role}...")
                st.rerun()
            else:
                st.error("Invalid Username, Password or Role. Please contact Admin.")

# --- LOGGED IN INTERFACE ---
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.info(f"Access Level: {st.session_state.user_role}")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. ADMIN ROLE ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Test/Service Management", "Sale Reports", "Approval Queue"]
        choice = st.sidebar.selectbox("Admin Panel", menu)

        if choice == "User Management":
            st.subheader("Create & Manage Staff Accounts")
            with st.expander("➕ Add New Staff Member"):
                u_n = st.text_input("Username")
                u_p = st.text_input("Password")
                u_r = st.selectbox("Assign Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.button("Create Account"):
                    if u_n and u_p:
                        c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (u_n, u_p, u_r))
                        conn.commit()
                        st.success(f"Account for {u_n} ({u_r}) created successfully!")
                    else: st.warning("Please fill all fields.")
            
            st.write("### Existing Users")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn), use_container_width=True)

        elif choice == "Test/Service Management":
            st.subheader("Manage Lab Services & Pricing")
            t_n = st.text_input("Service/Test Name")
            t_p = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Save Service"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_n, t_p))
                conn.commit()
                st.success("Price List Updated")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

        elif choice == "Sale Reports":
            st.subheader("Financial Reports")
            rep = st.radio("Filter By", ["Daily Sales", "Doctor-wise Revenue"])
            if rep == "Daily Sales":
                d = st.date_input("Select Date", date.today())
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE date='{d}' AND status='Active'", conn)
                st.table(df[['id', 'name', 'tests', 'final_amount', 'bill_user']])
                st.metric("Total Collection", f"Rs. {df['final_amount'].sum():,.2f}")

    # --- 2. BILLING ROLE ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Recall Bills", "My Summary", "Cancel Request"]
        choice = st.sidebar.selectbox("Billing Menu", menu)

        if choice == "New Registration":
            st.subheader("Patient Billing Interface")
            # මෙහි ඔබ කලින් ඉල්ලූ සියලුම fields (Name, Age, Mobile, Salute etc.) ඇත
            c1, c2 = st.columns(2)
            with c1:
                salute = st.selectbox("Salute", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Patient Name")
                p_age = st.number_input("Age", 0, 120)
            with c2:
                p_gender = st.selectbox("Gender", ["Male", "Female"])
                p_mobile = st.text_input("Mobile Number")
                p_doc = st.text_input("Referral Doctor")

            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            selected = st.multiselect("Search Tests/Services", tests_df['test_name'].tolist())
            
            subtotal = sum(tests_df[tests_df['test_name'].isin(selected)]['price'])
            st.write(f"**Sub Total: LKR {subtotal:,.2f}**")
            dis = st.number_input("Discount (LKR)", 0.0)
            final = subtotal - dis
            st.header(f"Grand Total: LKR {final:,.2f}")
            
            if st.button("Generate Bill"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected), subtotal, dis, final, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success("Bill Saved! You can now recall it for printing.")

        elif choice == "My Summary":
            st.subheader(f"Summary for {st.session_state.username}")
            d = st.date_input("View Date", date.today())
            df = pd.read_sql_query(f"SELECT * FROM billing WHERE date='{d}' AND bill_user='{st.session_state.username}' AND status='Active'", conn)
            st.dataframe(df[['id', 'name', 'tests', 'final_amount']])
            st.metric("Total Collection", f"Rs. {df['final_amount'].sum():,.2f}")

    # --- 3. SATELLITE ROLE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("Print Authorized Reports")
        search = st.text_input("Enter Bill ID or Patient Name")
        if st.button("Search"):
            st.info("Looking for reports approved by Technician...")

conn.close()
