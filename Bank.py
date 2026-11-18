from datetime import datetime
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Apex Bank Loan Portal", page_icon="🏦", layout="wide")

# Connect to local SQLite database to store applicant records
conn = sqlite3.connect("bank_customers.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    "CREATE TABLE IF NOT EXISTS applicants ("
    "customer_id TEXT PRIMARY KEY, full_name TEXT, dob TEXT, phone TEXT, "
    "email TEXT, city TEXT, employment_type TEXT, monthly_income REAL, "
    "existing_emi REAL, credit_score INTEGER, requested_loan REAL, "
    "approval_status TEXT, approved_limit REAL, created_at TEXT)"
)
conn.commit()

# Track which page (Step 1 or Step 2) and which customer is active
if "page" not in st.session_state:
    st.session_state.page = 1

if "customer" not in st.session_state:
    st.session_state.customer = {}

# Main App Header
st.title("🏦 Apex Bank — Loan Approval & EMI Calculator")
st.write("Complete Step 1 for instant loan approval, then move to Step 2 to calculate EMIs and extra monthly payments.")

# Top Navigation Buttons
nav1, nav2 = st.columns(2)
if nav1.button("Page 1: Loan Approval & Verification", use_container_width=True):
    st.session_state.page = 1
    st.rerun()

if nav2.button("Page 2: EMI & Extra Payment Calculator", use_container_width=True):
    st.session_state.page = 2
    st.rerun()

st.divider()

# ==========================================
# PAGE 1: LOAN APPROVAL & CUSTOMER IDENTITY
# ==========================================
if st.session_state.page == 1:
    st.header("Page 1: Applicant Identity & Loan Approval")

    # Option for returning customers to load their saved profile
    returning_box = st.expander("🔄 Already applied before? Click here to verify & load your profile")
    r1, r2, r3 = returning_box.columns(3)
    search_id = r1.text_input("Enter Email, Mobile Number, or Customer ID")
    search_dob = r2.date_input("Enter Date of Birth to Confirm Identity", value=datetime(1998, 1, 1))
    r3.write("")
    r3.write("")

    if r3.button("Verify & Load Profile"):
        cursor.execute(
            "SELECT * FROM applicants WHERE (LOWER(email) = LOWER(?) OR phone = ? OR UPPER(customer_id) = UPPER(?)) AND dob = ?",
            (search_id.strip(), search_id.strip(), search_id.strip(), str(search_dob))
        )
        row = cursor.fetchone()
        if row:
            st.session_state.customer = {
                "customer_id": row[0],
                "full_name": row[1],
                "dob": row[2],
                "phone": row[3],
                "email": row[4],
                "city": row[5],
                "employment_type": row[6],
                "monthly_income": row[7],
                "existing_emi": row[8],
                "credit_score": row[9],
                "requested_loan": row[10],
                "approval_status": row[11],
                "approved_limit": row[12]
            }
            st.success(f"Welcome back, {row[1]}! Your profile ({row[0]}) has been loaded.")
        else:
            st.error("No matching customer found. Please check your details and try again.")

    cust = st.session_state.customer

    # Main Application Inputs
    col1, col2 = st.columns(2)
    full_name = col1.text_input("Full Name *", value=cust.get("full_name", ""))
    default_dob = datetime.strptime(cust["dob"], "%Y-%m-%d") if "dob" in cust else datetime(1998, 1, 1)
    dob = col1.date_input("Date of Birth *", value=default_dob)
    phone = col1.text_input("Mobile Number *", value=cust.get("phone", ""))
    email = col2.text_input("Email Address *", value=cust.get("email", ""))
    monthly_income = col2.number_input("Net Monthly Income (₹) *", min_value=0.0, value=float(cust.get("monthly_income", 50000.0)), step=1000.0)
    requested_loan = col2.number_input("Loan Amount Needed (₹) *", min_value=1000.0, value=float(cust.get("requested_loan", 500000.0)), step=10000.0)

    # Extra Bank Verification Details in a separate click (Expander)
    extra_box = st.expander("➕ Click to Add Additional Bank Details (City, Job Type, Credit Score & Existing EMIs)")
    ex1, ex2 = extra_box.columns(2)
    city = ex1.text_input("Current City", value=cust.get("city", "Ahmedabad"))
    job_list = ["Salaried", "Self-Employed / Business", "Professional", "Student"]
    saved_job = cust.get("employment_type", "Salaried")
    job_index = job_list.index(saved_job) if saved_job in job_list else 0
    employment_type = ex1.selectbox("Employment Type", job_list, index=job_index)
    existing_emi = ex2.number_input("Existing Monthly EMIs (₹)", min_value=0.0, value=float(cust.get("existing_emi", 0.0)), step=500.0)
    credit_score = ex2.slider("Credit / CIBIL Score", min_value=300, max_value=900, value=int(cust.get("credit_score", 750)))

    # Approval Button
    if st.button("Check Eligibility & Save Application", type="primary"):
        if full_name == "" or phone == "" or email == "":
            st.error("Please enter your Name, Mobile Number, and Email Address.")
        else:
            # Bank rule: Total EMIs cannot exceed 50% of monthly income
            max_emi = (monthly_income * 0.50) - existing_emi
            rate_est = 0.10 / 12
            max_loan = max_emi * (((1 + rate_est) ** 60) - 1) / (rate_est * ((1 + rate_est) ** 60)) if max_emi > 0 else 0.0

            if credit_score < 650 or max_emi <= 0:
                status = "Declined"
                approved_limit = 0.0
            elif requested_loan <= max_loan:
                status = "Approved"
                approved_limit = requested_loan
            else:
                status = "Partially Approved"
                approved_limit = round(max_loan, -3)

            cust_id = cust.get("customer_id", f"APX-{abs(hash(email + str(dob))) % 100000:05d}")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Save or update customer record in database
            cursor.execute(
                "INSERT OR REPLACE INTO applicants VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    cust_id, full_name.strip(), str(dob), phone.strip(), email.strip(),
                    city.strip(), employment_type, monthly_income, existing_emi,
                    credit_score, requested_loan, status, approved_limit, now_str
                )
            )
            conn.commit()

            st.session_state.customer = {
                "customer_id": cust_id,
                "full_name": full_name.strip(),
                "dob": str(dob),
                "phone": phone.strip(),
                "email": email.strip(),
                "city": city.strip(),
                "employment_type": employment_type,
                "monthly_income": monthly_income,
                "existing_emi": existing_emi,
                "credit_score": credit_score,
                "requested_loan": requested_loan,
                "approval_status": status,
                "approved_limit": approved_limit
            }

            st.subheader(f"Result for {full_name} (ID: {cust_id})")
            m1, m2, m3 = st.columns(3)
            m1.metric("Loan Status", status)
            m2.metric("Approved Loan Amount", f"₹{approved_limit:,.2f}")
            m3.metric("Max Affordable EMI", f"₹{max(0.0, max_emi):,.2f}")

            if approved_limit > 0:
                st.success("Application saved! Click below to go to Page 2 and calculate your monthly EMI.")
                if st.button("Go to Page 2: Loan Calculator ➡️"):
                    st.session_state.page = 2
                    st.rerun()

# ==========================================
# PAGE 2: EMI & EXTRA PAYMENT CALCULATOR
# ==========================================
if st.session_state.page == 2:
    st.header("Page 2: Smart EMI & Extra Monthly Payment Calculator")

    cust = st.session_state.customer
    if cust:
        st.info(f"Applicant: **{cust['full_name']}** ({cust['customer_id']}) | Approved Limit: **₹{cust['approved_limit']:,.2f}**")
    else:
        st.warning("No customer loaded from Page 1. You can still use the calculator below.")

    start_loan = float(cust["approved_limit"]) if (cust and cust.get("approved_limit", 0) > 0) else 500000.0

    c1, c2 = st.columns(2)
    loan_amount = c1.number_input("Loan Amount (₹)", min_value=1000.0, value=start_loan, step=10000.0)
    apr = c1.number_input("Annual Interest Rate (%)", min_value=0.1, max_value=40.0, value=9.5, step=0.1)
    months = c2.number_input("Loan Tenure (Months)", min_value=1, max_value=360, value=60, step=1)
    extra_monthly = c2.number_input("Extra Payment Every Month (₹)", min_value=0.0, value=0.0, step=1000.0)

    # Extra bank feature: One-time lump sum prepayment in another click
    lump_box = st.expander("💡 Click to Add a One-Time Bonus / Lump-Sum Prepayment")
    l1, l2 = lump_box.columns(2)
    lump_amount = l1.number_input("One-Time Extra Payment (₹)", min_value=0.0, value=0.0, step=5000.0)
    lump_month = l2.number_input("Month Number to Pay Lump Sum", min_value=1, max_value=int(months), value=min(12, int(months)), step=1)

    # Standard EMI Calculation
    monthly_rate = (apr / 100) / 12
    emi = loan_amount * monthly_rate * ((1 + monthly_rate) ** months) / (((1 + monthly_rate) ** months) - 1)
    normal_total_interest = (emi * months) - loan_amount

    # Month-by-month simulation with extra payments
    balance = loan_amount
    total_interest_paid = 0.0
    actual_months = 0
    schedule_rows = []

    for m in range(1, int(months) + 1):
        if balance <= 0:
            break
        actual_months = actual_months + 1
        interest_this_month = balance * monthly_rate
        principal_this_month = emi - interest_this_month

        extra_this_month = extra_monthly
        if m == lump_month:
            extra_this_month = extra_this_month + lump_amount

        total_principal = principal_this_month + extra_this_month


if total_principal >= balance:
total_principal = balance
total_paid = balance + interest_this_month
balance = 0.0
else:
total_paid = emi + extra_this_month
balance = balance - total_principal
total_interest_paid = total_interest_paid + interest_this_month
schedule_rows.append({
"Month": m,
"Interest Paid (₹)": round(interest_this_month, 2),
"Principal Paid (₹)": round(total_principal, 2),
"Total Paid This Month (₹)": round(total_paid, 2),
"Remaining Balance (₹)": round(balance, 2)
})
interest_saved = max(0.0, normal_total_interest - total_interest_paid)
months_saved = max(0, int(months) - actual_months)
st.divider()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Monthly EMI", f"₹{emi:,.2f}")
k2.metric("Total Interest", f"₹{total_interest_paid:,.2f}", delta=f"-₹{interest_saved:,.2f} saved" if interest_saved > 0 else None)
k3.metric("Loan Duration", f"{actual_months} Months", delta=f"-{months_saved} months early" if months_saved > 0 else None)
k4.metric("Total Payable", f"₹{(loan_amount + total_interest_paid):,.2f}")
# Expandable Repayment Schedule
schedule_box = st.expander("📅 View Month-by-Month Payment Schedule")
df_schedule = pd.DataFrame(schedule_rows)
schedule_box.dataframe(df_schedule, use_container_width=True)
schedule_box.download_button(
"📥 Download Payment Schedule (CSV)",
data=df_schedule.to_csv(index=False).encode("utf-8"),
file_name="loan_payment_schedule.csv",
mime="text/csv"
)
# Expandable Bank Records Table
records_box = st.expander("🗄️ Bank Records: View All Saved Applicants")
df_all = pd.read_sql_query("SELECT * FROM applicants ORDER BY created_at DESC", conn)
if len(df_all) > 0:
records_box.dataframe(df_all, use_container_width=True)
records_box.download_button(
"📥 Download All Customer Records (CSV)",
data=df_all.to_csv(index=False).encode("utf-8"),
file_name="bank_applicants.csv",
mime="text/csv"
)
else:
records_box.info("No applicants saved yet.")