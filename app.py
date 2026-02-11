import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_final_v1.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT, requested_by TEXT)')
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- PDF GENERATION FUNCTION ---
def create_pdf(bill_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "LABORATORY INVOICE", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(100, 10, f"Bill ID: {bill_data[0]}")
    pdf.cell(100, 10, f"Date: {bill_data[11]}", ln=True)
    pdf.cell(200, 10, f"Patient: {bill_data[1]} {bill_data[2]}", ln=True)
    pdf.cell(200, 10, f"Mobile: {bill_data[5]}", ln=True)
    pdf.cell(200, 10, f"Doctor: {bill_data[6]}", ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, "Tests: " + bill_data[7], ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"Total Amount: LKR {bill_data[10]:,.2f}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- UI SETTINGS ---
st.set_page_config(page_title="Professional LIMS", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.title("🔐 LIMS Secure Login")
    user = st.text_input("Username")
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        c.execute('SELECT role FROM users WHERE username=? AND password=?', (user, pw))
        res = c.fetchone()
        if res:
            st.session_state.update({'logged_in': True, 'user_role': res[0], 'username': user})
            st.rerun()
        else: st.error("Invalid Credentials")

else:
    st.sidebar.title(f"👤 {st.session_state.username} ({st.session_state.user_role})")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- 1. ADMIN ROLE ---
    if st.session_state.user_role == "Admin":
        menu = ["Dashboard", "User Management", "Test/Service Management", "Sale", "Approval"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "User Management":
            st.subheader("User Management")
            with st.expander("Add/Update User"):
                u_n = st.text_input("Username")
                u_p = st.text_input("Password")
                u_r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
                if st.button("Save User"):
                    c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (u_n, u_p, u_r))
                    conn.commit()
                    st.success("User Updated")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif choice == "Test/Service Management":
            st.subheader("Manage Services")
            t_n = st.text_input("Service Name")
            t_p = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Add/Update Service"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_n, t_p))
                conn.commit()
                st.success("Service Updated")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn))

        elif choice == "Sale":
            st.subheader("Sales Reports")
            rep_type = st.radio("Report Type", ["Daily Sale", "Doctor Wise Sale"])
            if rep_type == "Daily Sale":
                sel_date = st.date_input("Select Date", date.today())
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE date='{sel_date}' AND status='Active'", conn)
                st.dataframe(df)
                st.metric("Total Revenue", f"LKR {df['final_amount'].sum():,.2f}")
            else:
                doc = st.text_input("Doctor Name")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE doctor LIKE '%{doc}%' AND status='Active'", conn)
                st.dataframe(df)
                st.metric(f"Total for Dr. {doc}", f"LKR {df['final_amount'].sum():,.2f}")

        elif choice == "Approval":
            st.subheader("Pending Cancellations")
            reqs = pd.read_sql_query("SELECT r.bill_id, b.name, b.final_amount, r.reason FROM cancel_requests r JOIN billing b ON r.bill_id=b.id WHERE r.status='Pending'", conn)
            st.dataframe(reqs)
            app_id = st.number_input("Enter Bill ID to Approve", step=1)
            if st.button("Approve & Reset Summary"):
                c.execute("UPDATE billing SET status='Cancelled' WHERE id=?", (app_id,))
                c.execute("UPDATE cancel_requests SET status='Approved' WHERE bill_id=?", (app_id,))
                conn.commit()
                st.success(f"Bill {app_id} has been cancelled.")

    # --- 2. BILLING ROLE ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Recall", "Summary", "Cancellation Request"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "New Registration":
            st.subheader("Patient Registration")
            col1, col2 = st.columns(2)
            with col1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Name")
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with col2:
                p_mobile = st.text_input("Mobile Number")
                p_doc = st.text_input("Referral Doctor")
            
            st.markdown("---")
            tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
            search_test = st.multiselect("Select Tests/Services", tests_df['test_name'].tolist())
            
            subtotal = sum(tests_df[tests_df['test_name'].isin(search_test)]['price'])
            st.write(f"Sub Total: LKR {subtotal:,.2f}")
            dis = st.number_input("Discount (LKR)", 0.0)
            final = subtotal - dis
            st.header(f"Total Amount: LKR {final:,.2f}")
            
            if st.button("Save & Generate PDF"):
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(search_test), subtotal, dis, final, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success("Bill Saved!")
                # PDF Download කොටස (සරලව)
                st.info("Bill ID: " + str(c.lastrowid))

        elif choice == "Recall":
            st.subheader("Recall Bills")
            search_by = st.radio("Search By", ["Name", "Mobile", "Period"])
            if search_by == "Name":
                q = st.text_input("Enter Name")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE name LIKE '%{q}%'", conn)
            elif search_by == "Mobile":
                q = st.text_input("Enter Mobile")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE mobile='{q}'", conn)
            else:
                d1 = st.date_input("From")
                d2 = st.date_input("To")
                df = pd.read_sql_query(f"SELECT * FROM billing WHERE date BETWEEN '{d1}' AND '{d2}'", conn)
            st.dataframe(df)

        elif choice == "Summary":
            st.subheader("Your Daily Summary")
            s_date = st.date_input("Select Date", date.today())
            df = pd.read_sql_query(f"SELECT * FROM billing WHERE date='{s_date}' AND bill_user='{st.session_state.username}' AND status='Active'", conn)
            st.dataframe(df)
            st.metric("Your Total Collection", f"LKR {df['final_amount'].sum():,.2f}")

        elif choice == "Cancellation Request":
            st.subheader("Request Cancellation")
            b_id = st.number_input("Bill ID", step=1)
            reason = st.text_area("Reason for cancellation")
            if st.button("Send Request"):
                c.execute("INSERT INTO cancel_requests VALUES (?,?,'Pending',?)", (b_id, reason, st.session_state.username))
                conn.commit()
                st.warning("Request sent to Admin.")

    # --- 3. SATELLITE ROLE ---
    elif st.session_state.user_role == "Satellite":
        st.subheader("Satellite Report Portal")
        search_id = st.text_input("Enter Bill ID or Patient Name")
        if st.button("Print Report"):
            st.info("Authorized reports will appear here after Technician approval.")

conn.close()
