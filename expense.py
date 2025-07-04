import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- File Paths ---
DATA_FILE = "expense_data.xlsx"

# --- Initialize Excel File with Sheets ---
def initialize_excel_file():
    if not os.path.exists(DATA_FILE):
        with pd.ExcelWriter(DATA_FILE) as writer:
            pd.DataFrame(columns=["Date", "Category", "Description", "Amount"]).to_excel(writer, sheet_name="Expenses", index=False)
            pd.DataFrame(columns=["Month", "Year", "Budget"]).to_excel(writer, sheet_name="Budgets", index=False)

# --- Load Data ---
def load_expenses():
    df = pd.read_excel(DATA_FILE, sheet_name="Expenses")
    df = df.loc[:, ~df.columns.duplicated()]
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df["Amount"] = df["Amount"].astype(float)
        df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)
    return df

def load_budgets():
    df = pd.read_excel(DATA_FILE, sheet_name="Budgets")
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.astype(str).str.strip().str.lower()
    return df

# --- Save Data ---
def save_dataframes(expenses_df, budgets_df):
    with pd.ExcelWriter(DATA_FILE, engine="openpyxl", mode="w") as writer:
        expenses_df.to_excel(writer, sheet_name="Expenses", index=False)
        budgets_df.to_excel(writer, sheet_name="Budgets", index=False)

# --- Add Expense ---
def add_expense(date, category, description, amount):
    df = load_expenses()
    new_row = {"Date": pd.to_datetime(date), "Category": category, "Description": description, "Amount": float(amount)}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_dataframes(df, load_budgets())

# --- Delete Expense ---
def delete_expense(selected):
    df = load_expenses()
    df["Category"] = df["Category"].astype(str)
    df["Description"] = df["Description"].astype(str)
    df["DateStr"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Label"] = df.apply(lambda row: f"{row['DateStr']} | {row['Category']} | {row['Description']} | ₹{row['Amount']}", axis=1)
    df = df[df["Label"] != selected]
    df = df.drop(columns=["DateStr", "Label"])
    save_dataframes(df, load_budgets())

# --- Budget Management ---
def add_or_update_budget(month, year, budget):
    budgets = load_budgets()
    month_clean = month.strip().lower()
    updated = False
    for i, row in budgets.iterrows():
        if str(row["month"]).strip().lower() == month_clean and int(row["year"]) == int(year):
            budgets.at[i, "budget"] = float(budget)
            updated = True
            break
    if not updated:
        new_row = {"month": month_clean, "year": int(year), "budget": float(budget)}
        budgets = pd.concat([budgets, pd.DataFrame([new_row])], ignore_index=True)
    save_dataframes(load_expenses(), budgets)

def delete_budget(selected):
    budgets = load_budgets()
    budgets["Label"] = budgets.apply(lambda row: f"{row['month'].capitalize()} {row['year']} - ₹{row['budget']}", axis=1)
    budgets = budgets[budgets["Label"] != selected].drop(columns=["Label"])
    save_dataframes(load_expenses(), budgets)

# --- Initialize File ---
initialize_excel_file()
df = load_expenses()
budget_df = load_budgets()

st.set_page_config(page_title="Expense Tracker", layout="wide")
st.title("💸 Local Excel Expense Tracker")

# Sidebar Budget Summary
st.sidebar.markdown("## 📊 Budget Summary")
if not df.empty:
    current_month = datetime.today().strftime("%B")
    current_year = datetime.today().year
    current_df = df[(df["Date"].dt.month_name() == current_month) & (df["Date"].dt.year == current_year)]
    current_spent = current_df["Amount"].sum()
    budget_row = budget_df[(budget_df["month"] == current_month.lower()) & (budget_df["year"] == current_year)]
    current_budget = float(budget_row["budget"].values[0]) if not budget_row.empty else 0
    remaining = current_budget - current_spent
    st.sidebar.metric("📋 Budget", f"₹{current_budget:,.2f}")
    st.sidebar.metric("💸 Spent", f"₹{current_spent:,.2f}")
    st.sidebar.metric("💰 Remaining", f"₹{remaining:,.2f}")
else:
    st.sidebar.info("No expenses yet.")

# Add Expense Form
with st.form("add_expense"):
    st.subheader("➕ Add New Expense")
    date = st.date_input("Date", datetime.today())
    category = st.selectbox("Category", ["Food", "Transport", "Bills", "Shopping", "Other"])
    description = st.text_input("Description")
    amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
    if st.form_submit_button("Add Expense"):
        add_expense(date, category, description, amount)
        st.success("✅ Expense added.")
        st.experimental_rerun()

# Delete Expense
st.markdown("### ❌ Delete Expense")
if not df.empty:
    df["DateStr"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Label"] = df.apply(lambda row: f"{row['DateStr']} | {row['Category']} | {row['Description']} | ₹{row['Amount']}", axis=1)
    selected_expense = st.selectbox("Select Expense to Delete", df["Label"].tolist())
    if st.button("Delete Selected Expense"):
        delete_expense(selected_expense)
        st.success("🗑️ Expense deleted.")
        st.experimental_rerun()

# Budget Management
st.markdown("---")
st.header("📅 Manage Budgets")
col1, col2, col3 = st.columns(3)
with col1:
    month = st.selectbox("Month", [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ], key="add_month")
with col2:
    year = st.selectbox("Year", list(range(2022, datetime.today().year + 2)), index=1, key="add_year")
with col3:
    budget = st.number_input("Budget (₹)", min_value=0.0, format="%.2f", key="add_budget")
if st.button("💾 Add/Update Budget"):
    add_or_update_budget(month, year, budget)
    st.success("✅ Budget saved.")
    st.experimental_rerun()

# Delete Budget
st.subheader("🗑️ Delete a Budget Entry")
budget_df = load_budgets()  # Refresh latest
if not budget_df.empty:
    budget_df["Label"] = budget_df.apply(lambda row: f"{row['month'].capitalize()} {row['year']} - ₹{row['budget']}", axis=1)
    selected_budget = st.selectbox("Select Budget to Delete", budget_df["Label"].tolist())
    if st.button("Delete Selected Budget"):
        delete_budget(selected_budget)
        st.warning("🗑️ Budget deleted.")
        st.experimental_rerun()
else:
    st.info("No budget entries available to delete.")

# Daily View
st.markdown("---")
st.header("🗓️ Daily Expenses")
if not df.empty:
    selected_date = st.date_input("Pick a date", datetime.today())
    daily_df = df[df["Date"] == pd.to_datetime(selected_date)]
    if not daily_df.empty:
        st.subheader(f"Expenses on {selected_date.strftime('%d %B %Y')}")
        st.dataframe(daily_df.sort_values(by="Amount", ascending=False), use_container_width=True)
        st.info(f"🧾 Total: ₹{daily_df['Amount'].sum():,.2f}")
    else:
        st.info("No expenses for this date.")

# Monthly Overview
st.markdown("---")
st.header("📊 Monthly Overview")
if not df.empty:
    month_options = sorted(df["YearMonth"].unique())
    selected_months = st.multiselect("Select Months", month_options, default=[month_options[-1]])
    filtered_df = df[df["YearMonth"].isin(selected_months)]
    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values(by="Date", ascending=False), use_container_width=True)
        st.subheader("💡 Top Category")
        top_category = filtered_df.groupby("Category")["Amount"].sum().idxmax()
        st.success(f"Most spent on: {top_category}")
        monthly_totals = filtered_df.groupby("YearMonth")["Amount"].sum()
        st.bar_chart(monthly_totals)
        summary = []
        for ym in selected_months:
            year, month = ym.split("-")
            month_name = datetime.strptime(month, "%m").strftime("%B").lower()
            row = budget_df[(budget_df["month"] == month_name) & (budget_df["year"] == int(year))]
            budget_val = float(row["budget"].values[0]) if not row.empty else 0
            spent = monthly_totals.get(ym, 0)
            summary.append({"Month": ym, "Budget": budget_val, "Spent": spent, "Remaining": budget_val - spent})
        st.subheader("📘 Budget vs Actual")
        st.dataframe(pd.DataFrame(summary))
    else:
        st.warning("No expenses in selected months.")
