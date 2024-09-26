import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from urllib.parse import quote_plus

# MongoDB credentials
MONGO_USERNAME = "sa"
MONGO_PASSWORD = "RFL@2o2o"
MONGO_HOST = "localhost:27017"
MONGO_DATABASE = "fraud_detection_db"

# Set page configuration (must be first Streamlit command)
st.set_page_config(page_title="Fraud Detection Dashboard", layout="wide", initial_sidebar_state="expanded")

# MongoDB connection
@st.cache_resource
def init_connection():
    try:
        mongodb_username = quote_plus(MONGO_USERNAME)
        mongodb_password = quote_plus(MONGO_PASSWORD)
        mongodb_uri = f"mongodb://{mongodb_username}:{mongodb_password}@{MONGO_HOST}/{MONGO_DATABASE}?authSource=admin"
        client = MongoClient(mongodb_uri)
        client.admin.command('ismaster')
        st.success("Successfully connected to MongoDB")
        return client
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {str(e)}")
        return None

client = init_connection()

def convert_date_to_datetime(data):
    if isinstance(data, list):
        for doc in data:
            for key, value in doc.items():
                if isinstance(value, (datetime, date)):
                    doc[key] = datetime.combine(value.date(), datetime.min.time())
    return data

# Fetch data
@st.cache_data(ttl=600)
def get_data(collection, query=None, limit=1000):
    if client is None:
        return []
    try:
        db = client.get_database(MONGO_DATABASE)
        items = db[collection].find(query).limit(limit)
        return convert_date_to_datetime(list(items))
    except Exception as e:
        st.error(f"Error fetching data from MongoDB: {str(e)}")
        return []

# Main dashboard
st.title("Fraud Detection Analysis Dashboard")

# Sidebar filters
st.sidebar.header("Filter Data")
end_date = datetime.now()
start_date = end_date - timedelta(days=7)
date_range = st.sidebar.date_input("Select Date Range", [start_date, end_date])

if len(date_range) == 2:
    start_date, end_date = date_range
    query = {
        "timestamp": {
            "$gte": datetime.combine(start_date, datetime.min.time()),
            "$lte": datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        }
    }
else:
    query = None

transactions = get_data("transactions", query)
fraud_alerts = get_data("fraud_alerts", query)

# Data validation
if not transactions or not fraud_alerts:
    st.warning("No data available. Please check your MongoDB connection and collections.")
    st.stop()

# Convert to DataFrames
df_transactions = pd.DataFrame(transactions)
df_fraud_alerts = pd.DataFrame(fraud_alerts)

# Overview Metrics
st.header("Overview Metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Total Transactions", len(df_transactions), delta=len(df_transactions) - 1000)
col2.metric("Total Amount", f"${df_transactions['amount'].sum():,.2f}" if 'amount' in df_transactions.columns else "N/A", delta=df_transactions['amount'].sum() - 10000)
col3.metric("Fraud Alerts", len(df_fraud_alerts), delta=len(df_fraud_alerts) - 10)

# Transactions over time chart
st.header("Transactions Over Time")
if 'timestamp' in df_transactions.columns:
    df_transactions['date'] = pd.to_datetime(df_transactions['timestamp']).dt.date
    daily_transactions = df_transactions.groupby('date').agg({'amount': 'sum', 'transaction_id': 'count'}).reset_index()
    daily_transactions.columns = ['date', 'total_amount', 'transaction_count']
    fig = px.line(daily_transactions, x='date', y=['total_amount', 'transaction_count'],
                 title='Daily Transactions and Amount',
                 labels={"value": "Count / Amount", "variable": "Metrics"})
    fig.update_layout(legend_title_text="Metrics", title_x=0.5)
    st.plotly_chart(fig)
else:
    st.warning("Timestamp data not available in transactions.")

# Transaction Types pie chart
st.header("Transaction Types")
if 'transaction_type' in df_transactions.columns:
    type_counts = df_transactions['transaction_type'].value_counts()
    fig = px.pie(values=type_counts.values, names=type_counts.index, title='Transaction Types Distribution')
    fig.update_traces(textinfo='percent+label')
    st.plotly_chart(fig)
else:
    st.warning("Transaction type data not available.")

# Top Senders and Receivers
st.header("Top Senders and Receivers")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Top Senders")
    if 'sender' in df_transactions.columns:
        top_senders = df_transactions['sender'].value_counts().head(10)
        fig = px.bar(x=top_senders.index, y=top_senders.values, title='Top 10 Senders')
        st.plotly_chart(fig)
    else:
        st.warning("Sender data not available.")

with col2:
    st.subheader("Top Receivers")
    if 'receiver' in df_transactions.columns:
        top_receivers = df_transactions['receiver'].value_counts().head(10)
        fig = px.bar(x=top_receivers.index, y=top_receivers.values, title='Top 10 Receivers')
        st.plotly_chart(fig)
    else:
        st.warning("Receiver data not available.")

# Fraud Alerts Analysis
st.header("Fraud Alerts Analysis")

if not df_fraud_alerts.empty:
    if 'transaction_count' in df_fraud_alerts.columns:
        st.subheader("Multiple Transactions Alerts")
        fig = px.scatter(df_fraud_alerts, x='total_amount', y='transaction_count',
                         hover_data=['sender'], title='Multiple Transactions Alerts')
        st.plotly_chart(fig)
    else:
        st.warning("No multiple transactions alert data available.")

    if 'amount' in df_fraud_alerts.columns:
        st.subheader("Large Transfers Alerts")
        fig = px.histogram(df_fraud_alerts, x='amount', title='Distribution of Large Transfers')
        st.plotly_chart(fig)
    else:
        st.warning("No large transfer alert data available.")
else:
    st.info("No fraud alerts found in the selected date range.")

# Raw Data Views
st.header("Raw Data")
if st.checkbox("Show Raw Transaction Data"):
    st.write(df_transactions)
if st.checkbox("Show Raw Fraud Alerts"):
    st.write(df_fraud_alerts)

# Footer
st.markdown("---")
st.markdown("##### Created by [Your Name]")