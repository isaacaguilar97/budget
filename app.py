#%% Import libraries
import pandas as pd
import gspread
import streamlit as st
import plotly.graph_objects as go
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

#%% Create a connection object
conn = st.connection("gsheets", type=GSheetsConnection)

# Create raw Budget dataframe
budget_df = conn.read(usecols=list(range(15)), worksheet=st.secrets["connections"]["gsheets"]["wk1"], ttl=5)

# Create raw Actual dataframe
actual_df = conn.read(usecols=list(range(15)), worksheet=st.secrets["connections"]["gsheets"]["wk2"], ttl=5)

#%% Clean table

# Make a copy of both dfs
b_df = budget_df.copy()
a_df = actual_df.copy()

# Rename columns
b_df.columns = ["Type", "Buckets"] + list(budget_df.iloc[3])[2:] # Budget
a_df.columns = ["Type", "Buckets"] + list(actual_df.iloc[3])[2:] # Actual

# Remove unnecessary rows
b_df = b_df.iloc[26:48] # Budget
a_df = a_df.iloc[26:48] # Actual

# Store Type and Buckets array in a Dataframe
categories = pd.DataFrame({
	"Type": b_df.Type,
	"Bucket": b_df.Buckets
})

# Remove unnecessary columns
b_df.drop(b_df.columns[[0, -1]], axis=1, inplace=True) # Budget
a_df.drop(a_df.columns[[0, -1]], axis=1, inplace=True) # Actual

# Reset index for all dataframes
b_df = b_df.reset_index(drop=True).drop("Buckets", axis=1) # Budget
a_df = a_df.reset_index(drop=True).drop("Buckets", axis=1) # Actual
categories = categories.reset_index(drop=True)

# Remove comas from all columns
budget = b_df.applymap(lambda x: str(x).replace(',', ''))
for col in a_df.select_dtypes(include='object'):
    a_df[col] = a_df[col].str.replace(',', '', regex=False)

# Convert to numbers
budget = budget.apply(pd.to_numeric)
actuals = a_df.apply(pd.to_numeric)

# Fill NA with 0
budget = budget.fillna(0)
actuals = actuals.fillna(0)

# Get today's month
td = datetime.today().strftime("%b")

# Final Table
final_df = pd.DataFrame({
    'Type': categories.Type,
    'Category': categories.Bucket,
    'Balance': budget[td] - actuals[td],
    'Budget': budget[td]
})

# Parameters
col_inter = ['Food', 'Supplies', 'Self Care', 'Isaac', 'Adri', 'Eliam', 'Dates/Fun', 'Gifts', 'Fast Food', 'Junk Food']
filtered_df = final_df[final_df['Category'].isin(col_inter)]

# Authenticate and connect to Google Sheets
def connect_to_gsheet(creds_dict, spreadsheet_name, sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", 
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", 
             "https://www.googleapis.com/auth/drive"]
    
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open(spreadsheet_name)  
    return spreadsheet.worksheet(sheet_name)  # Access specific sheet by name

# Google Sheet credentials and details
SPREADSHEET_NAME = 'Cash Flow Fam Aguilar'
SHEET_NAME = 'Real'
CREDENTIALS_FILE = st.secrets["google"]

# Connect to the Google Sheet
sheet_by_name = connect_to_gsheet(CREDENTIALS_FILE, SPREADSHEET_NAME, sheet_name=SHEET_NAME)

#%% Start Streamlit app

### SIDEBAR
with st.sidebar:
    # App Title
    st.title('Enter your Transaction')

    with st.form(key="Enter your Transaction"):
        amt = st.number_input("Amount")
        cty = st.selectbox("Category", col_inter)
        card = st.selectbox("Payment Method", ['Silver', 'Barclays', 'DFCU', 'Venture', 'Cosco', 'Chase'])
        # Submit button inside the form
        submitted = st.form_submit_button("Submit")
        # Handle form submission
        if submitted:
            if amt and cty and card:  # Basic validation to check if required fields are filled
                # Update Spreadsheet
                # Get the values of row 5 and column B
                row_5 = sheet_by_name.row_values(5)
                col_B = sheet_by_name.col_values(2)

                # Find the column and row indexes
                col_index = row_5.index(td) + 1
                row_index = col_B.index(cty) + 1

                # Read current value
                current_value = sheet_by_name.cell(row_index, col_index).value
                new_value = float(current_value or 0) + amt

                # Update Category
                sheet_by_name.update_cell(row_index, col_index, new_value)

                if card != "Chase": # I don't make updates if I paid with my chase
                    # Update Debt
                    sheet_by_name.update_cell(row_index, col_index, new_value)
                    row_index = col_B.index("Deuda") + 1
                    sheet_by_name.update_cell(row_index, col_index, float(sheet_by_name.cell(row_index, col_index).value)+10)

                    # Update Card
                    row_index = col_B.index(card) + 1
                    sheet_by_name.update_cell(row_index, col_index, float(sheet_by_name.cell(row_index, col_index).value)+10)

                st.success("Data added successfully!")
            else:
                st.error("Please fill out the form correctly.")

# Header 1
st.header('👪🏼 Family Aguilar Budget')

st.divider()

for i in range(filtered_df.shape[0]):
    cat = filtered_df['Category'].iloc[i]
    but = filtered_df['Budget'].iloc[i]
    bal = filtered_df['Balance'].iloc[i]
    remaining_pct = bal/but
    bar_col = 'red' if remaining_pct <= 0 else 'orange' if remaining_pct <= 0.15 else 'green'

    fig = go.Figure(go.Indicator(
        mode = "gauge,delta", 
        value = but - bal,
        domain = {'x': [0.15, 1], 'y': [0, 1]},
        title = {'text' :f"<b>{cat}</b>"},
        delta = {'reference': but - 2*bal, 
                 "valueformat": "$.0f",
                 "increasing": {"color": "white", "symbol": ""}, 
                 "decreasing": {"color": "white", "symbol": ""}},
        gauge = {
            'shape': "bullet",
            'axis': {'range': [None, but*1.20]},
            'bar': {'color': bar_col},
            'threshold': {
                'line': {'color': "red", 'width': 2},
                'thickness': 0.75,
                'value': but}
            }))
    fig.update_layout(
        height = 60,
        margin=dict(t=0, b=0),
        autosize=True 
        )
    st.plotly_chart(fig)