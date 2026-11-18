from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="SmartBanking",
    page_icon="🏦",
    layout="wide",
)
#DhianPatel

st.write="By DHIAN PATEL",

# --- DATABASE SETUP (Persistent SQLite Storage) ---
DB_FILE = "bank_customers.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS applicants (
            customer_id TEXT PRIMARY KEY,
            full_name TEXT,
            dob TEXT,
            phone TEXT,
            email TEXT,
            city TEXT,
            employment_type TEXT,
            employer_name TEXT,
            monthly_income REAL,
            existing_emi REAL,
            credit_score INTEGER,
            requested_loan REAL,
            approval_status TEXT,
            approved_limit REAL,
            created_at TEXT
        )
    """)
  conn.commit()
  conn.close()


def save_applicant(data):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      """
        INSERT OR REPLACE INTO applicants VALUES (
            :customer_id, :full_name, :dob, :phone, :email, :city,
            :employment_type, :employer_name, :monthly_income, :existing_emi,
            :credit_score, :requested_loan, :approval_status, :approved_limit, :created_at
        )
    """,
      data,
  )
  conn.commit()
  conn.close()


def find_applicant(lookup_key, dob_str):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      """
        SELECT * FROM applicants
        WHERE (LOWER(email) = LOWER(?) OR phone = ? OR UPPER(customer_id) = UPPER(?))
        AND dob = ?
    """,
      (lookup_key.strip(), lookup_key.strip(), lookup_key.strip(), dob_str),
  )
  row = c.fetchone()
  conn.close()
  if row:
    columns = [
        "customer_id",
        "full_name",
        "dob",
        "phone",
        "email",
        "city",
        "employment_type",
        "employer_name",
        "monthly_income",
        "existing_emi",
        "credit_score",
        "requested_loan",
        "approval_status",
        "approved_limit",
        "created_at",
    ]
    return dict(zip(columns, row))
  return None


def get_all_applicants():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query(
      "SELECT * FROM applicants ORDER BY created_at DESC", conn
  )
  conn.close()
  return df


init_db()

# --- SESSION STATE INITIALIZATION ---
if "step" not in st.session_state:
  st.session_state.step = 1
if "active_customer" not in st.session_state:
  st.session_state.active_customer = None

# --- HEADER & STEP NAVIGATION BAR ---
st.title("🏦 Apex Bank — Digital Loan Origination & EMI Portal")
st.caption(
    "Automated Pre-Approval • Customer Identity Vault • Prepayment Savings"
    " Simulator"
)

# Visual Progress Indicator
col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 2])
with col_nav1:
  if st.button(
      "1️⃣ Step 1: Verification & Approval",
      use_container_width=True,
      type="primary" if st.session_state.step == 1 else "secondary",
  ):
    st.session_state.step = 1
    st.rerun()
with col_nav2:
  if st.button(
      "2️⃣ Step 2: EMI & Prepayment Calculator",
      use_container_width=True,
      type="primary" if st.session_state.step == 2 else "secondary",
  ):
    st.session_state.step = 2
    st.rerun()

st.divider()

# ==============================================================================
# PAGE 1: CUSTOMER IDENTITY VERIFICATION & LOAN APPROVAL
# ==============================================================================
if st.session_state.step == 1:
  st.subheader("Step 1: Applicant Verification & Pre-Approval Check")

  # --- RETURNING CUSTOMER LOOKUP ---
  with st.expander(
      "🔄 Returning Applicant? Click here to load your saved profile",
      expanded=False,
  ):
    st.write(
        "Enter your registered **Email, Phone Number, or Customer ID** along"
        " with your **Date of Birth** to verify your identity."
    )
    r_col1, r_col2, r_col3 = st.columns([2, 2, 1])
    with r_col1:
      lookup_input = st.text_input(
          "Email / Phone / Customer ID", placeholder="e.g., dhian@example.com"
      )
    with r_col2:
      lookup_dob = st.date_input(
          "Date of Birth for Verification", value=datetime(1998, 1, 1)
      )
    with r_col3:
      st.write("")
      st.write("")
      if st.button("Verify & Load", use_container_width=True):
        found = find_applicant(lookup_input, str(lookup_dob))
        if found:
          st.session_state.active_customer = found
          st.success(
              f"Identity Verified! Welcome back, {found['full_name']}"
              f" ({found['customer_id']})."
          )
        else:
          st.error("No matching record found. Please check your details.")

  # Pre-fill values if a returning customer was loaded
  cust = st.session_state.active_customer or {}

  with st.form("approval_form"):
    st.markdown("#### Primary KYC & Financial Details")
    c1, c2, c3 = st.columns(3)
    with c1:
      full_name = st.text_input(
          "Full Legal Name *", value=cust.get("full_name", "")
      )
      dob = st.date_input(
          "Date of Birth *",
          value=datetime.strptime(cust["dob"], "%Y-%m-%d")
          if "dob" in cust
          else datetime(1998, 1, 1),
      )
    with c2:
      phone = st.text_input(
          "Registered Mobile Number *", value=cust.get("phone", "")
      )
      email = st.text_input("Email Address *", value=cust.get("email", ""))
    with c3:
      monthly_income = st.number_input(
          "Net Monthly Income (₹) *",
          min_value=0.0,
          value=float(cust.get("monthly_income", 60000.0)),
          step=2000.0,
      )
      requested_loan = st.number_input(
          "Requested Loan Amount (₹) *",
          min_value=5000.0,
          value=float(cust.get("requested_loan", 500000.0)),
          step=10000.0,
      )

    # --- ADDITIONAL BANK DETAILS IN ANOTHER CLICK (EXPANDER) ---
    with st.expander(
        "➕ Click to Add Additional Bank Verification & Profile Details"
        " (Recommended for Higher Approval Limit)"
    ):
      ex1, ex2, ex3 = st.columns(3)
      with ex1:
        city = st.text_input(
            "Current City of Residence", value=cust.get("city", "Ahmedabad")
        )
        employment_type = st.selectbox(
            "Employment Category",
            ["Salaried", "Self-Employed / Business", "Professional", "Student"],
            index=[
                "Salaried",
                "Self-Employed / Business",
                "Professional",
                "Student",
            ].index(cust.get("employment_type", "Salaried")),
        )
      with ex2:
        employer_name = st.text_input(
            "Company / Business Name", value=cust.get("employer_name", "")
        )
        existing_emi = st.number_input(
            "Existing Monthly Loan EMIs (₹)",
            min_value=0.0,
            value=float(cust.get("existing_emi", 0.0)),
            step=1000.0,
        )
      with ex3:
        credit_score = st.slider(
            "Estimated Credit / CIBIL Score",
            min_value=300,
            max_value=900,
            value=int(cust.get("credit_score", 750)),
        )
        bank_relation = st.selectbox(
            "Existing Account with Apex Bank?",
            ["Yes - Savings/Salary Account", "No - New Customer"],
        )

    submit_approval = st.form_submit_button(
        "Check Loan Eligibility & Save Profile", type="primary"
    )

  if submit_approval:
    if not full_name.strip() or not phone.strip() or not email.strip():
      st.error(
          "Please fill in all mandatory fields marked with * (Name, Mobile,"
          " Email)."
      )
    else:
      # Bank Underwriting Rules
      max_eligible_emi = (monthly_income * 0.50) - existing_emi
      # Estimate max loan at 10% for 60 months
      r_est = 0.10 / 12
      max_eligible_loan = (
          max_eligible_emi * (((1 + r_est) ** 60) - 1) / (r_est * ((1 + r_est) ** 60))
          if max_eligible_emi > 0
          else 0
      )

      if credit_score < 650 or max_eligible_emi <= 0:
        status = "Declined (Low Credit Score or High Existing Debt)"
        approved_limit = 0.0
      elif requested_loan <= max_eligible_loan:
        status = "Approved"
        approved_limit = requested_loan
      else:
        status = "Partially Approved (Eligible for Lower Limit)"
        approved_limit = round(max_eligible_loan, -3)

      cust_id = cust.get(
          "customer_id",
          f"APX-{abs(hash(email + str(dob))) % 100000:05d}",
      )

      record = {
          "customer_id": cust_id,
          "full_name": full_name.strip(),
          "dob": str(dob),
          "phone": phone.strip(),
          "email": email.strip(),
          "city": city.strip(),
          "employment_type": employment_type,
          "employer_name": employer_name.strip(),
          "monthly_income": monthly_income,
          "existing_emi": existing_emi,
          "credit_score": credit_score,
          "requested_loan": requested_loan,
          "approval_status": status,
          "approved_limit": approved_limit,
          "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
      }

      save_applicant(record)
      st.session_state.active_customer = record

      st.divider()
      st.markdown(f"### Underwriting Decision for **{full_name}** (`{cust_id}`)")
      m1, m2, m3 = st.columns(3)
      m1.metric("Application Status", status)
      m2.metric("Approved Loan Limit", f"₹{approved_limit:,.2f}")
      m3.metric("Max Safe Monthly EMI", f"₹{max(0.0, max_eligible_emi):,.2f}")

      if approved_limit > 0:
        st.success(
            "Your profile is saved! Click the button below to proceed to the"
            " EMI & Extra-Payment Calculator."
        )
        if st.button("Proceed to Step 2: Loan Calculator ➡️", type="primary"):
          st.session_state.step = 2
