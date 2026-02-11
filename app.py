import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from fpdf import FPDF

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v3.db', check_same_thread=False)
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
    c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT)')
    
    # මුල් Admin පාරිභෝගිකයා සෑදීම
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- UI LOGIC ---
st.set_page_config(page_title="Advanced LIMS v3", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- LOGIN ---
if not st.session_state.logged_in:
    st.title("🔐 LIMS Secure Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        c.execute('SELECT role FROM users WHERE username=? AND password=?', (user, pw))
        res = c.fetchone()
        if res:
            st.session_state.logged_in = True
            st.session_state.user_role = res[0]
            st.session_state.username = user
            st.rerun()
        else:
            st.error("Invalid Username or Password")

else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.write(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. ADMIN INTERFACE ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Test/Service Management", "Sales Report", "Approvals"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "User Management":
            st.subheader("Manage System Users")
            col1, col2 = st.columns(2)
            with col1:
                new_user = st.text_input("New Username")
                new_pw = st.text_input("New Password")
                new_role = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.button("Add User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (new_user, new_pw, new_role))
                    conn.commit()
                    st.success(f"User {new_user} added!")
            with col2:
                st.write("Current Users")
                users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
                st.dataframe(users_df)

        elif choice == "Test/Service Management":
            st.subheader("Test Price List")
            t_name = st.text_input("Test/Service Name")
            t_price = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Add/Update Item"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_name, t_price))
                conn.commit()
                st.success("Item Updated")
            
            st.write("Available Services")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn))

        elif choice == "Approvals":
            st.subheader("Cancellation Approvals")
            reqs = pd.read_sql_query("SELECT b.id, b.name, r.reason FROM cancel_requests r JOIN billing b ON r.bill_id = b.id WHERE r.status='Pending'", conn)
            st.table(reqs)
            bid = st.number_input("Bill ID to Approve", step=1)
            if st.button("Approve Cancel"):
                c.execute("UPDATE billing SET status='Cancelled' WHERE id=?", (bid,))
                c.execute("UPDATE cancel_requests SET status='Approved' WHERE bill_id=?", (bid,))
                conn.commit()
                st.success("Bill Cancelled Successfully")

    # --- 2. BILLING INTERFACE ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Recall/Search", "Daily Summary", "Cancellation Request"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "New Registration":
            st.subheader("Billing & Registration")
            c1, c2 = st.columns(2)
            with c1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                name = st.text_input("Patient Name")
                age = st.number_input("Age", 0, 120)
                gender = st.selectbox("Gender", ["Male", "Female"])
            with c2:
                mobile = st.text_input("Mobile Number")
                doctor = st.text_input("Referral Doctor")
            
            st.markdown("---")
            tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
            selected = st.multiselect("Select Tests", tests_db['test_name'].tolist())
            
            subtotal = 0
            for s in selected:
                subtotal += tests_db[tests_db['test_name'] == s]['price'].values[0]
            
            st.write(f"Sub Total: LKR {subtotal:,.2f}")
            discount = st.number_input("Discount", 0.0)
            final = subtotal - discount
            st.header(f"Total Amount: LKR {final:,.2f}")
            
            if st.button("Print & Save Bill"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, name, age, gender, mobile, doctor, ", ".join(selected), subtotal, discount, final, str(date.today()), st.session_state.username, 'Active'))
                conn.commit()
                st.success("Bill Generated!")

        elif choice == "Recall/Search":
            st.subheader("Recall Old Bills")
            s_type = st.radio("Search By", ["Name", "Mobile", "Date Period"])
            if s_type == "Name":
                val = st.text_input("Enter Name")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE name LIKE '%{val}%'", conn)
            elif s_type == "Mobile":
                val = st.text_input("Enter Mobile")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE mobile='{val}'", conn)
            st.dataframe(df)

    # --- 3. SATELLITE INTERFACE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("Print Authorised Reports")
        ref_id = st.text_input("Bill ID / Reference Number")
        if st.button("Search Report"):
            st.info("Searching for patient record...")
            # පසුව Technician කොටස මෙයට සම්බන්ධ වනු ඇත.

conn.close()
