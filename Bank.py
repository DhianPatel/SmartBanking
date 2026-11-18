from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Apex Bank | Smart Loan Portal",
    page_icon="🏦",
    layout="wide",
)

DB_FILE = "bank_customers.db"


def init_db():
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "CREATE TABLE IF NOT EXISTS applicants ("
      "customer_id TEXT PRIMARY KEY, full_name TEXT, dob TEXT, "
      "phone TEXT, email TEXT, city TEXT, employment_type TEXT, "
      "employer_name TEXT, monthly_income REAL, existing_emi REAL, "
      "credit_score INTEGER, requested_loan REAL, approval_status TEXT, "
      "approved_limit REAL, created_at TEXT)"
  )
  conn.commit()
  conn.close()


def save_applicant(data):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "INSERT OR REPLACE INTO applicants VALUES ("
      ":customer_id, :full_name, :dob, :phone, :email, :city, "
      ":employment_type, :employer_name, :monthly_income, :existing_emi, "
      ":credit_score, :requested_loan, :approval_status, :approved_limit,"
      " :created_at)",
      data,
  )
  conn.commit()
  conn.close()


def find_applicant(lookup_key, dob_str):
  conn = sqlite3.connect(DB_FILE)
  c = conn.cursor()
  c.execute(
      "SELECT * FROM applicants WHERE (LOWER(email) = LOWER(?) OR phone = ? OR"
      " UPPER(customer_id) = UPPER(?)) AND dob = ?",
      (lookup_key.strip(), lookup_key.strip(), lookup_key.strip(), dob_str),
  )
  row = c.fetchone()
  conn.close()
  if not row:
    return None
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


def get_all_applicants():
  conn = sqlite3.connect(DB_FILE)
  df = pd.read_sql_query(
      "SELECT * FROM applicants ORDER BY created_at DESC", conn
  )
  conn.close()
  return df


def build_amortization(
    loan_amount,
    annual_rate,
    tenure_months,
    extra_monthly,
    lump_sum_amount,
    lump_sum_month,
):
  r = (annual_rate / 100) / 12
  standard_emi = (
      loan_amount
      * r
      * ((1 + r) ** tenure_months)
      / (((1 + r) ** tenure_months) - 1)
  )
  standard_total_interest = (standard_emi * tenure_months) - loan_amount

  balance = loan_amount
  schedule = []
  total_interest = 0.0
  actual_months = 0

  for m in range(1, int(tenure_months) + 1):
    if balance <= 0:
      break
    actual_months += 1
    interest_m = balance * r
    principal_m = standard_emi - interest_m
    extra_m = extra_monthly + (lump_sum_amount if m == lump_sum_month else 0.0)
    total_principal = principal_m + extra_m

    if total_principal >= balance:
      total_principal = balance
      outflow = balance + interest_m
      balance = 0.0
    else:
      outflow = standard_emi + extra_m
      balance -= total_principal

    total_interest += interest_m
    schedule.append({
        "Month": m,
        "Opening Balance (₹)": round(balance + total_principal, 2),
        "Interest Paid (₹)": round(interest_m, 2),
        "Principal + Extra Paid (₹)": round(total_principal, 2),
        "Total Outflow (₹)": round(outflow, 2),
        "Closing Balance (₹)": round(balance, 2),
    })

  interest_saved = max(0.0, standard_total_interest - total_interest)
  months_saved = max(0, int(tenure_months) - actual_months)
  return (
      standard_emi,
      total_interest,
      actual_months,
      interest_saved,
      months_saved,
      schedule,
  )


def render_step_1():
  st.subheader("Step 1: Applicant Verification & Pre-Approval Check")

  ret_exp = st.expander(
      "🔄 Returning Applicant? Click here to load your saved profile",
      expanded=False,
  )
  ret_exp.write(
      "Enter your registered **Email, Phone Number, or Customer ID** along"
      " with your **Date of Birth** to verify your identity."
  )
  r_col1, r_col2, r_col3 = ret_exp.columns(3)
  lookup_input = r_col1.text_input(
      "Email / Phone / Customer ID", placeholder="e.g., dhian@example.com"
  )
  lookup_dob = r_col2.date_input(
      "Date of Birth for Verification", value=datetime(1998, 1, 1)
  )
  r_col3.write("")
  r_col3.write("")
  if r_col3.button("Verify & Load", use_container_width=True):
    found = find_applicant(lookup_input, str(lookup_dob))
    if found:
      st.session_state.active_customer = found
      st.success(
          f"Identity Verified! Welcome back, {found['full_name']}"
          f" ({found['customer_id']})."
      )
    else:
      st.error("No matching record found. Please check your details.")

  cust = st.session_state.active_customer or {}

  form = st.form("approval_form")
  form.markdown("#### Primary KYC & Financial Details")
  c1, c2, c3 = form.columns(3)
  full_name = c1.text_input(
      "Full Legal Name *", value=cust.get("full_name", "")
  )
  default_dob = (
      datetime.strptime(cust["dob"], "%Y-%m-%d")
      if "dob" in cust
      else datetime(1998, 1, 1)
  )
  dob = c1.date_input("Date of Birth *", value=default_dob)
  phone = c2.text_input(
      "Registered Mobile Number *", value=cust.get("phone", "")
  )
  email = c2.text_input("Email Address *", value=cust.get("email", ""))
  monthly_income = c3.number_input(
      "Net Monthly Income (₹) *",
      min_value=0.0,
      value=float(cust.get("monthly_income", 60000.0)),
      step=2000.0,
  )
  requested_loan = c3.number_input(
      "Requested Loan Amount (₹) *",
      min_value=5000.0,
      value=float(cust.get("requested_loan", 500000.0)),
      step=10000.0,
  )

  kyc_exp = form.expander(
      "➕ Click to Add Additional Bank Verification & Profile Details"
      " (Recommended for Higher Approval Limit)"
  )
  ex1, ex2, ex3 = kyc_exp.columns(3)
  city = ex1.text_input(
      "Current City of Residence", value=cust.get("city", "Ahmedabad")
  )
  employment_options = [
      "Salaried",
      "Self-Employed / Business",
      "Professional",
      "Student",
  ]
  saved_emp = cust.get("employment_type", "Salaried")
  emp_idx = (
      employment_options.index(saved_emp)
      if saved_emp in employment_options
      else 0
  )
  employment_type = ex1.selectbox(
      "Employment Category", employment_options, index=emp_idx
  )
  employer_name = ex2.text_input(
      "Company / Business Name", value=cust.get("employer_name", "")
  )
  existing_emi = ex2.number_input(
      "Existing Monthly Loan EMIs (₹)",
      min_value=0.0,
      value=float(cust.get("existing_emi", 0.0)),
      step=1000.0,
  )
  credit_score = ex3.slider(
      "Estimated Credit / CIBIL Score",
      min_value=300,
      max_value=900,
      value=int(cust.get("credit_score", 750)),
  )
  ex3.selectbox(
      "Existing Account with Apex Bank?",
      ["Yes - Savings/Salary Account", "No - New Customer"],
  )

  submit_approval = form.form_submit_button(
      "Check Loan Eligibility & Save Profile", type="primary"
  )

  if not submit_approval:
    return

  if not full_name.strip() or not phone.strip() or not email.strip():
    st.error(
        "Please fill in all mandatory fields marked with * (Name, Mobile,"
        " Email)."
    )
    return

  max_eligible_emi = (monthly_income * 0.50) - existing_emi
  r_est = 0.10 / 12
  max_eligible_loan = (
      max_eligible_emi
      * (((1 + r_est) ** 60) - 1)
      / (r_est * ((1 + r_est) ** 60))
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
      "customer_id", f"APX-{abs(hash(email + str(dob))) % 100000:05d}"
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
        "Your profile is saved! Click the button below to proceed to the EMI &"
        " Extra-Payment Calculator."
    )
    if st.button("Proceed to Step 2: Loan Calculator ➡️", type="primary"):
      st.session_state.step = 2
      st.rerun()
  else:
    st.warning(
        "Based on current income/credit score, the loan cannot be approved. You"
        " can still test scenarios in Step 2."
    )


def render_step_2():
  cust = st.session_state.active_customer
  if cust:
    st.info(
        f"Active Applicant: **{cust['full_name']}** (ID:"
        f" `{cust['customer_id']}`) | Approved Limit:"
        f" **₹{cust['approved_limit']:,.2f}**"
    )
  else:
    st.warning(
        "No applicant loaded from Step 1. Using standard calculator mode."
    )

  st.subheader("Step 2: Loan EMI & Extra Monthly Payment Simulator")

  default_loan = (
      float(cust["approved_limit"])
      if (cust and cust["approved_limit"] > 0)
      else 500000.0
  )

  col_in1, col_in2 = st.columns(2)





loan_amount = col_in1.number_input(
"Loan Principal Amount (₹)",
min_value=1000.0,
value=default_loan,
step=10000.0,
)
annual_rate = col_in1.number_input(
"Annual Interest Rate (%)",
min_value=0.1,
max_value=40.0,
value=9.5,
step=0.1,
)
tenure_months = col_in2.number_input(
"Loan Tenure (Months)", min_value=1, max_value=360, value=60, step=1
)
extra_monthly = col_in2.number_input(
"Extra Monthly Prepayment (₹) — Optional",
min_value=0.0,
value=0.0,
step=1000.0,
)
lump_exp = st.expander(
"💡 Advanced Bank Feature: One-Time Bonus / Lump-Sum Prepayment"
)
lump_col1, lump_col2 = lump_exp.columns(2)
lump_sum_amount = lump_col1.number_input(
"One-Time Lump Sum Payment (₹)", min_value=0.0, value=0.0, step=5000.0
)
lump_sum_month = lump_col2.number_input(
"Which Month Will You Pay This Lump Sum?",
min_value=1,
max_value=int(tenure_months),
value=min(12, int(tenure_months)),
step=1,
)
(
standard_emi,
total_interest,
actual_months,
interest_saved,
months_saved,
schedule,
) = build_amortization(
loan_amount,
annual_rate,
tenure_months,
extra_monthly,
lump_sum_amount,
lump_sum_month,
)
st.divider()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Standard Monthly EMI", f"₹{standard_emi:,.2f}")
k2.metric(
"Total Interest Payable",
f"₹{total_interest:,.2f}",
delta=f"-₹{interest_saved:,.2f} saved" if interest_saved > 0 else None,
)
k3.metric(
"Effective Loan Tenure",
f"{actual_months} Months",
delta=f"-{months_saved} months early" if months_saved > 0 else None,
)
k4.metric(
"Total Amount Payable", f"₹{(loan_amount + total_interest):,.2f}"
)
sched_exp = st.expander("📅 View Month-by-Month Bank Amortization Schedule")
df_schedule = pd.DataFrame(schedule)
sched_exp.dataframe(df_schedule, use_container_width=True)
sched_exp.download_button(
"📥 Download Repayment Schedule (CSV)",
data=df_schedule.to_csv(index=False).encode("utf-8"),
file_name="amortization_schedule.csv",
mime="text/csv",
)
ledger_exp = st.expander(
"🗄️ Bank Officer Ledger: View All Stored Applicant Records"
)
all_df = get_all_applicants()
if not all_df.empty:
ledger_exp.dataframe(all_df, use_container_width=True)
ledger_exp.download_button(
"📥 Export Full Customer Database (CSV)",
data=all_df.to_csv(index=False).encode("utf-8"),
file_name="apex_bank_customers.csv",
mime="text/csv",
)
else:
ledger_exp.info("No applicant records stored yet.")
init_db()
if "step" not in st.session_state:
st.session_state.step = 1
if "active_customer" not in st.session_state:
st.session_state.active_customer = None
st.title("🏦 Apex Bank — Digital Loan Origination & EMI Portal")
st.caption(
"Automated Pre-Approval • Customer Identity Vault • Prepayment Savings"
" Simulator"
)
col_nav1, col_nav2 = st.columns(2)
if col_nav1.button(
"1️⃣ Step 1: Verification & Approval",
use_container_width=True,
type="primary" if st.session_state.step == 1 else "secondary",
):
st.session_state.step = 1
st.rerun()
if col_nav2.button(
"2️⃣ Step 2: EMI & Prepayment Calculator",
use_container_width=True,
type="primary" if st.session_state.step == 2 else "secondary",
):
st.session_state.step = 2
st.rerun()
st.divider()
if st.session_state.step == 1:
render_step_1()
else:
render_step_2()