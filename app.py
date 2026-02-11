import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v4_doctor_mgmt.db', check_same_thread=False)
    c = conn.cursor()
    # Users Table
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    # Doctors Table
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
    # Tests Table
    c.execute('CREATE TABLE IF NOT EXISTS tests (test_name TEXT PRIMARY KEY, price REAL)')
    # Billing Table
    c.execute('''CREATE TABLE IF NOT EXISTS billing 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, salute TEXT, name TEXT, age INTEGER, 
                  gender TEXT, mobile TEXT, doctor TEXT, tests TEXT, total REAL, 
                  discount REAL, final_amount REAL, date TEXT, bill_user TEXT, status TEXT)''')
    # Cancel Requests
    c.execute('CREATE TABLE IF NOT EXISTS cancel_requests (bill_id INTEGER, reason TEXT, status TEXT, requested_by TEXT)')
    
    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', 'admin123', 'Admin')")
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# --- UI SETTINGS ---
st.set_page_config(page_title="LIMS v4 - Doctor Management", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔬 Laboratory Information System</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            l_user = st.text_input("Username")
            l_pw = st.text_input("Password", type="password")
            l_role = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.form_submit_button("Login", use_container_width=True):
                c.execute('SELECT * FROM users WHERE username=? AND password=? AND role=?', (l_user, l_pw, l_role))
                if c.fetchone():
                    st.session_state.update({'logged_in': True, 'user_role': l_role, 'username': l_user})
                    st.rerun()
                else: st.error("Access Denied!")

# --- LOGGED IN ---
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Doctor Management", "Test Management", "Sales Reports", "Approvals"]
        choice = st.sidebar.selectbox("Admin Menu", menu)

        if choice == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Referral Doctors")
            
            # Add Doctor
            with st.expander("Add New Doctor"):
                d_name = st.text_input("Doctor's Name (e.g., Dr. Kamal)")
                if st.button("Add Doctor"):
                    if d_name:
                        c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (d_name,))
                        conn.commit()
                        st.success("Doctor Added!")
                    else: st.warning("Enter a name.")

            # View, Edit & Delete Doctors
            st.write("### Registered Doctors")
            doc_df = pd.read_sql_query("SELECT * FROM doctors", conn)
            
            for index, row in doc_df.iterrows():
                col1, col2, col3 = st.columns([3, 1, 1])
                col1.write(row['doc_name'])
                if col2.button("Delete", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM doctors WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
                # Edit පහසුකම (සරලව)
                new_n = col3.text_input("New Name", key=f"edit_{row['id']}", placeholder="Rename...")
                if new_n:
                    if st.button("Update", key=f"up_{row['id']}"):
                        c.execute("UPDATE doctors SET doc_name=? WHERE id=?", (new_n, row['id']))
                        conn.commit()
                        st.rerun()

        elif choice == "User Management":
            st.subheader("Manage Staff")
            u_n = st.text_input("Username")
            u_p = st.text_input("Password")
            u_r = st.selectbox("Role", ["Admin", "Billing", "Technician", "Satellite"])
            if st.button("Create Account"):
                c.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (u_n, u_p, u_r))
                conn.commit()
                st.success("Staff member added.")
            st.dataframe(pd.read_sql_query("SELECT username, role FROM users", conn))

        elif choice == "Test Management":
            st.subheader("Test Pricing")
            t_n = st.text_input("Test Name")
            t_p = st.number_input("Price (LKR)")
            if st.button("Save Test"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_n, t_p))
                conn.commit()
                st.success("Updated.")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn))

    # --- BILLING ---
    elif st.session_state.user_role == "Billing":
        menu = ["New Registration", "Summary", "Recall"]
        choice = st.sidebar.selectbox("Billing Menu", menu)

        if choice == "New Registration":
            st.subheader("New Patient Bill")
            with st.form("billing_form"):
                # Tab order එක ස්වයංක්‍රීයව පිළිවෙළට වැඩ කරයි
                col1, col2 = st.columns(2)
                with col1:
                    salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                    p_name = st.text_input("Full Name")
                    p_age = st.number_input("Age", 0, 120)
                with col2:
                    p_gender = st.selectbox("Gender", ["Male", "Female"])
                    p_mobile = st.text_input("Mobile Number")
                    
                    # Doctors Dropdown from Database
                    doc_list = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                    p_doc = st.selectbox("Select Referral Doctor", ["Self"] + doc_list)

                st.markdown("---")
                tests_db = pd.read_sql_query("SELECT * FROM tests", conn)
                selected = st.multiselect("Select Tests", tests_db['test_name'].tolist())
                
                dis = st.number_input("Discount (LKR)", 0.0)
                submit_bill = st.form_submit_button("Complete & Print Bill", use_container_width=True)
                
                if submit_bill:
                    subtotal = sum(tests_db[tests_db['test_name'].isin(selected)]['price'])
                    final = subtotal - dis
                    c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                              (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected), subtotal, dis, final, str(date.today()), st.session_state.username, "Active"))
                    conn.commit()
                    st.success(f"Bill Generated! Total: LKR {final:,.2f}")

conn.close()
