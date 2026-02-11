import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF

# --- DATABASE SETUP ---
conn = sqlite3.connect('lims_v2.db', check_same_thread=False)
c = conn.cursor()

# Tables නිර්මාණය කිරීම
c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS billing (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT)')

# Default Admin User එකතු කිරීම
try:
    c.execute("INSERT INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
except:
    pass

# --- FUNCTIONS ---
def get_total_sale(filter_date=None, doctor=None):
    query = "SELECT * FROM billing WHERE status='Active'"
    params = []
    if filter_date:
        query += " AND date = ?"
        params.append(filter_date)
    if doctor:
        query += " AND doctor = ?"
        params.append(doctor)
    return pd.read_sql_query(query, conn, params=params)

# --- UI LOGIC ---
st.set_page_config(page_title="Advanced LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.username = None

# --- LOGIN PAGE ---
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
            st.error("Invalid Credentials")

# --- LOGGED IN INTERFACE ---
else:
    st.sidebar.title(f"Welcome, {st.session_state.username}")
    st.sidebar.info(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN INTERFACE ---
    if st.session_state.user_role == "Admin":
        menu = ["Dashboard", "User Management", "Test/Service Management", "Sales Report", "Approvals"]
        choice = st.sidebar.selectbox("Admin Menu", menu)

        if choice == "Test/Service Management":
            st.subheader("Manage Tests & Prices")
            t_name = st.text_input("Test Name")
            t_price = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Add/Update Test"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_name, t_price))
                conn.commit()
                st.success("Test Updated")
            
            st.write("Current Tests")
            st.table(pd.read_sql_query("SELECT * FROM tests", conn))

        elif choice == "Sales Report":
            st.subheader("Sales Analysis")
            tab1, tab2 = st.tabs(["Daily/Period Sale", "Doctor Wise Sale"])
            with tab1:
                s_date = st.date_input("Select Date", date.today())
                df = get_total_sale(filter_date=str(s_date))
                st.dataframe(df)
                st.metric("Total Revenue", f"Rs. {df['final_amount'].sum():,.2f}")
            with tab2:
                doc_name = st.text_input("Enter Doctor Name")
                if doc_name:
                    df_doc = get_total_sale(doctor=doc_name)
                    st.dataframe(df_doc)
                    st.metric(f"Revenue from Dr. {doc_name}", f"Rs. {df_doc['final_amount'].sum():,.2f}")

        elif choice == "Approvals":
            st.subheader("Cancellation Requests")
            reqs = pd.read_sql_query("SELECT * FROM cancel_requests WHERE status='Pending'", conn)
            st.table(reqs)
            bid = st.number_input("Enter Bill ID to Approve", step=1)
            if st.button("Approve Cancellation"):
                c.execute("UPDATE billing SET status='Cancelled' WHERE id=?", (bid,))
                c.execute("UPDATE cancel_requests SET status='Approved' WHERE bill_id=?", (bid,))
                conn.commit()
                st.success(f"Bill {bid} Cancelled")

    # --- BILLING INTERFACE ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Recall", "Summary", "Cancellation Request"]
        choice = st.sidebar.selectbox("Billing Menu", menu)

        if choice == "New Registration":
            st.subheader("Patient Registration & Billing")
            col1, col2 = st.columns(2)
            with col1:
                salute = st.selectbox("Salutation", ["Mr.", "Mrs.", "Mast.", "Miss", "Baby", "Baby of Mrs.", "Rev."])
                name = st.text_input("Name")
                age = st.number_input("Age", min_value=0)
            with col2:
                gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                mobile = st.text_input("Mobile Number")
                doctor = st.text_input("Referral Doctor")

            st.markdown("---")
            all_tests = pd.read_sql_query("SELECT * FROM tests", conn)
            selected_tests = st.multiselect("Select Tests/Services", all_tests['test_name'].tolist())
            
            temp_total = 0
            test_details = []
            for t in selected_tests:
                p = all_tests[all_tests['test_name'] == t]['price'].values[0]
                temp_total += p
                test_details.append(f"{t}(Rs.{p})")

            st.write(f"**Sub Total: Rs. {temp_total:,.2f}**")
            discount = st.number_input("Discount (LKR)", min_value=0.0)
            final_amt = temp_total - discount
            st.header(f"Total Amount: Rs. {final_amt:,.2f}")

            if st.button("Complete Bill & Save"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, name, age, gender, mobile, doctor, ", ".join(test_details), temp_total, discount, final_amt, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success("Bill Saved Successfully!")

        elif choice == "Cancellation Request":
            bid = st.number_input("Bill ID to Cancel", step=1)
            reason = st.text_area("Reason")
            if st.button("Send Request to Admin"):
                c.execute("INSERT INTO cancel_requests VALUES (?,?,'Pending')", (bid, reason))
                conn.commit()
                st.warning("Request Sent")

    # --- SATELLITE INTERFACE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("Report Retrieval")
        search = st.text_input("Enter Patient Name or Bill ID")
        if st.button("Search & Print"):
            st.info("Searching for Authorised Reports...")
            # Technician කොටස පසුව සම්බන්ධ කිරීමට මෙතැන ඉඩ තබා ඇත.

conn.close()
