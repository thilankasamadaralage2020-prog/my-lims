import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('lims_v6_final.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS doctors (id INTEGER PRIMARY KEY AUTOINCREMENT, doc_name TEXT)')
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

# --- UI SETTINGS ---
st.set_page_config(page_title="LIMS v6 - Secure Management", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'username': None})

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔬 Professional Laboratory System</h2>", unsafe_allow_html=True)
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
    st.sidebar.write(f"Role: {st.session_state.user_role}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # --- ADMIN DASHBOARD ---
    if st.session_state.user_role == "Admin":
        menu = ["User Management", "Doctor Management", "Test Management"]
        choice = st.sidebar.selectbox("Admin Menu", menu)

        # --- USER MANAGEMENT (නිවැරදි කරන ලද කොටස) ---
        if choice == "User Management":
            st.subheader("👥 System User Management")
            
            # නව පරිශීලකයෙකු ඇතුළත් කිරීම
            with st.expander("➕ Add New User"):
                with st.form("add_user_form"):
                    u_name = st.text_input("New Username")
                    u_pass = st.text_input("New Password")
                    u_role = st.selectbox("Assign Role", ["Admin", "Billing", "Technician", "Satellite"])
                    if st.form_submit_button("Create Account"):
                        if u_name and u_pass:
                            try:
                                c.execute("INSERT INTO users VALUES (?,?,?)", (u_name, u_pass, u_role))
                                conn.commit()
                                st.success(f"User '{u_name}' added successfully!")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Username already exists!")
                        else: st.warning("Please fill all fields.")

            # පවතින පරිශීලකයන් පෙන්වීම සහ ඉවත් කිරීම
            st.write("### Active System Users")
            users_df = pd.read_sql_query("SELECT username, role FROM users", conn)
            
            for index, row in users_df.iterrows():
                col1, col2, col3 = st.columns([2, 2, 1])
                col1.write(f"**User:** {row['username']}")
                col2.write(f"**Role:** {row['role']}")
                if row['username'] != 'admin': # මුල් Adminව මැකීමට නොදීම
                    if col3.button("Delete", key=f"user_{row['username']}"):
                        c.execute("DELETE FROM users WHERE username=?", (row['username'],))
                        conn.commit()
                        st.rerun()
                else:
                    col3.write("🛡️ Protected")

        elif choice == "Doctor Management":
            st.subheader("👨‍⚕️ Manage Doctors")
            d_name = st.text_input("Doctor Name")
            if st.button("Add Doctor"):
                c.execute("INSERT INTO doctors (doc_name) VALUES (?)", (d_name,))
                conn.commit()
                st.success("Doctor Added")
            st.dataframe(pd.read_sql_query("SELECT * FROM doctors", conn), use_container_width=True)

        elif choice == "Test Management":
            st.subheader("🧪 Manage Tests & Prices")
            t_name = st.text_input("Test Name")
            t_price = st.number_input("Price (LKR)", min_value=0.0)
            if st.button("Save Test"):
                c.execute("INSERT OR REPLACE INTO tests VALUES (?,?)", (t_name, t_price))
                conn.commit()
                st.success("Test Saved")
            st.dataframe(pd.read_sql_query("SELECT * FROM tests", conn), use_container_width=True)

    # --- BILLING DASHBOARD ---
    elif st.session_state.user_role == "Billing":
        st.subheader("📝 New Patient Registration & Billing")
        
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                salute = st.selectbox("Salutation", ["Mr", "Mrs", "Mast", "Miss", "Baby", "Baby of Mrs", "Rev"])
                p_name = st.text_input("Full Name")
            with col2:
                p_age = st.number_input("Age", 0, 120)
                p_gender = st.selectbox("Gender", ["Male", "Female"])
            with col3:
                p_mobile = st.text_input("Mobile Number")
                doc_list = pd.read_sql_query("SELECT doc_name FROM doctors", conn)['doc_name'].tolist()
                p_doc = st.selectbox("Referral Doctor", ["Self"] + doc_list)

        st.markdown("---")
        tests_df = pd.read_sql_query("SELECT * FROM tests", conn)
        test_options = [f"{row['test_name']} - LKR {row['price']:,.2f}" for index, row in tests_df.iterrows()]
        selected_display = st.multiselect("Select Tests/Services", test_options)
        
        full_amount = 0.0
        selected_test_names = []
        for s in selected_display:
            t_name_only = s.split(" - LKR")[0]
            price = tests_df[tests_df['test_name'] == t_name_only]['price'].values[0]
            full_amount += price
            selected_test_names.append(t_name_only)

        st.markdown("### Payment Summary")
        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1: st.info(f"**Full Amount: LKR {full_amount:,.2f}**")
        with c_col2: discount = st.number_input("Discount (LKR)", 0.0, full_amount)
        with c_col3:
            final_amount = full_amount - discount
            st.success(f"**Final Amount: LKR {final_amount:,.2f}**")

        if st.button("Confirm & Save Bill", use_container_width=True):
            if p_name and selected_test_names:
                c.execute("INSERT INTO billing (salute, name, age, gender, mobile, doctor, tests, total, discount, final_amount, date, bill_user, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (salute, p_name, p_age, p_gender, p_mobile, p_doc, ", ".join(selected_test_names), full_amount, discount, final_amount, str(date.today()), st.session_state.username, "Active"))
                conn.commit()
                st.success("Bill successfully saved!")
            else: st.error("Please fill name and select tests.")

conn.close()
