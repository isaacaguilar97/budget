#%% Import libraries
import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

#%% Connect to the spreadsheet
url = "https://docs.google.com/spreadsheets/d/1xVKoVmKZOpNZ1oBySdLTE5GXZwN66UNoKjaBoEifZss/edit?usp=sharing"

# Create a connection object
conn = st.connection("gsheets", type=GSheetsConnection)

# Create raw Budget dataframe
budget_df = conn.read(spreadsheet =url, usecols=list(range(15)), worksheet=832591380, ttl=5)

# Create raw Actual dataframe
actual_df = conn.read(spreadsheet =url, usecols=list(range(15)), worksheet=487806377, ttl=5)

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
final_df

#%% Start Streamlit app

### SIDEBAR
with st.sidebar:
    # App Title
    st.title('Enter your Transaction')

    # Position Input
    pos1 = st.selectbox("Select Position", final_df['pos'].unique().tolist())

    # Height unit
    h = st.selectbox("Select Height Unit", ['inches', 'meters'])
    unit_dic = {'inches': 'height_in', 'meters': 'height_m'}

    # Warning message
    st.info("Be aware that results come from a sample of NBA players from season 2023")

    # Abbreviations
    with st.expander("Abbreviation Index"):
        st.table(abb)

# Header 1
st.header('Explore the Positions')