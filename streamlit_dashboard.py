import streamlit as st
import pandas as pd
from pymongo import MongoClient
import os
from urllib.parse import quote_plus
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Set page config
st.set_page_config(
    page_title="Real-Time Fraud Detection",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 36px;
        font-weight: bold;
        color: #1E90FF;
        text-align: center;
        margin-bottom: 30px;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        color: #4682B4;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .metric-container {
        background-color: #F0F8FF;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 18px;
        font-weight: bold;
        color: #4682B4;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #1E90FF;
    }
    .stPlotlyChart {
        background-color: #F0F8FF;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# MongoDB connection function (unchanged)
def connect_to_mongodb():
    """Connects to MongoDB and returns the client and database objects."""
    try:
        mongodb_username = os.getenv('MONGO_USERNAME', 'sa')
        mongodb_password = os.getenv('MONGO_PASSWORD', 'RFL@2o2o')
        mongodb_host = os.getenv('MONGO_HOST', 'mongodb:27017')
        database_name = os.getenv('MONGO_DATABASE', 'fraud_detection_db')

        escaped_username = quote_plus(mongodb_username)
        escaped_password = quote_plus(mongodb_password)

        mongodb_uri = f"mongodb://{escaped_username}:{escaped_password}@{mongodb_host}/{database_name}?authSource=admin"
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        return client, db
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        st.stop()

# Connect to MongoDB
client, db = connect_to_mongodb()

# Fetch data functions (unchanged)
def fetch_fraud_alerts():
    alerts = db.fraud_alerts.find()
    return pd.DataFrame(list(alerts))

def fetch_transactions():
    transactions = db.transactions.find()
    return pd.DataFrame(list(transactions))

# Display summary statistics
def display_summary_statistics(transactions_df, alerts_df):
    num_transactions = len(transactions_df)
    num_fraud_alerts = len(alerts_df)
    fraud_rate = (num_fraud_alerts / num_transactions) * 100 if num_transactions > 0 else 0
    avg_transaction_amount = transactions_df['amount'].mean() if 'amount' in transactions_df.columns else 0

    st.markdown('<h2 class="section-header">Summary Statistics</h2>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Total Transactions</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{num_transactions:,}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Fraud Alerts</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{num_fraud_alerts:,}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Fraud Rate</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{fraud_rate:.2f}%</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.markdown('<p class="metric-label">Avg Transaction</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">${avg_transaction_amount:.2f}</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# Visualizations
def plot_fraud_alerts_trends(alerts_df):
    if not alerts_df.empty and 'timestamp' in alerts_df.columns:
        alerts_df['timestamp'] = pd.to_datetime(alerts_df['timestamp'])
        alerts_per_day = alerts_df.resample('D', on='timestamp').size().reset_index(name='count')
        
        fig = px.line(alerts_per_day, x='timestamp', y='count', title='Fraud Alerts Over Time')
        fig.update_layout(xaxis_title='Date', yaxis_title='Number of Alerts')
        st.plotly_chart(fig, use_container_width=True)

def plot_transaction_type_distribution(transactions_df):
    if not transactions_df.empty and 'transaction_type' in transactions_df.columns:
        type_counts = transactions_df['transaction_type'].value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index, title='Transaction Type Distribution')
        st.plotly_chart(fig, use_container_width=True)

def plot_top_senders_receivers(transactions_df):
    if not transactions_df.empty:
        top_senders = transactions_df['sender'].value_counts().nlargest(10)
        top_receivers = transactions_df['receiver'].value_counts().nlargest(10)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=top_senders.values, y=top_senders.index, name='Top Senders', orientation='h'))
        fig.add_trace(go.Bar(x=top_receivers.values, y=top_receivers.index, name='Top Receivers', orientation='h'))
        fig.update_layout(title='Top 10 Senders and Receivers', barmode='group', height=500)
        st.plotly_chart(fig, use_container_width=True)

def plot_hourly_transaction_heatmap(transactions_df):
    if not transactions_df.empty and 'timestamp' in transactions_df.columns:
        transactions_df['timestamp'] = pd.to_datetime(transactions_df['timestamp'])
        transactions_df['hour'] = transactions_df['timestamp'].dt.hour
        transactions_df['day_of_week'] = transactions_df['timestamp'].dt.dayofweek
        
        heatmap_data = transactions_df.groupby(['day_of_week', 'hour']).size().unstack()
        
        fig = px.imshow(heatmap_data, 
                        labels=dict(x="Hour of Day", y="Day of Week", color="Number of Transactions"),
                        x=list(range(24)),
                        y=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                        title="Hourly Transaction Heatmap")
        st.plotly_chart(fig, use_container_width=True)

# Sidebar for navigation
st.sidebar.header("Navigation")
selection = st.sidebar.radio("Choose a page:", ['Dashboard', 'Alerts', 'Trends', 'Settings'])

# Refresh button with spinner
if st.sidebar.button("Refresh Data"):
    with st.spinner("Fetching data..."):
        st.session_state.data = fetch_fraud_alerts()
        st.session_state.transactions = fetch_transactions()

# Load data initially
if 'data' not in st.session_state or 'transactions' not in st.session_state:
    st.session_state.data = fetch_fraud_alerts()
    st.session_state.transactions = fetch_transactions()

# Page Content
if selection == 'Dashboard':
    st.markdown('<h1 class="main-header">Real-Time Fraud Detection Dashboard</h1>', unsafe_allow_html=True)
    
    display_summary_statistics(st.session_state.transactions, st.session_state.data)
    
    col1, col2 = st.columns(2)
    with col1:
        plot_fraud_alerts_trends(st.session_state.data)
    with col2:
        plot_transaction_type_distribution(st.session_state.transactions)
    
    plot_top_senders_receivers(st.session_state.transactions)
    
    # Display recent fraud alerts
    st.markdown('<h2 class="section-header">Recent Fraud Alerts</h2>', unsafe_allow_html=True)
    if not st.session_state.data.empty:
        st.dataframe(st.session_state.data.iloc[:10], use_container_width=True)
    else:
        st.write("No fraud alerts available.")

elif selection == 'Alerts':
    st.markdown('<h1 class="main-header">Fraud Alerts</h1>', unsafe_allow_html=True)
    
    # Display all fraud alerts with pagination
    alerts_per_page = 20
    num_alerts = len(st.session_state.data)
    num_pages = (num_alerts - 1) // alerts_per_page + 1
    page = st.number_input('Page', min_value=1, max_value=num_pages, value=1)
    
    start_idx = (page - 1) * alerts_per_page
    end_idx = min(start_idx + alerts_per_page, num_alerts)
    
    st.dataframe(st.session_state.data.iloc[start_idx:end_idx], use_container_width=True)
    st.write(f"Showing alerts {start_idx + 1} to {end_idx} out of {num_alerts}")

elif selection == 'Trends':
    st.markdown('<h1 class="main-header">Fraud Trends</h1>', unsafe_allow_html=True)

    # Display fraud trends
    plot_fraud_alerts_trends(st.session_state.data)
    plot_hourly_transaction_heatmap(st.session_state.transactions)
    
    # Add more trend analysis here
    st.markdown('<h2 class="section-header">Transaction Amount Distribution</h2>', unsafe_allow_html=True)
    fig = px.histogram(st.session_state.transactions, x='amount', nbins=50, title='Distribution of Transaction Amounts')
    st.plotly_chart(fig, use_container_width=True)

elif selection == 'Settings':
    st.markdown('<h1 class="main-header">Settings</h1>', unsafe_allow_html=True)
    st.write("Here you can configure settings for the dashboard.")
    
    # Add some example settings
    st.markdown('<h2 class="section-header">Alert Thresholds</h2>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Multiple Transactions Threshold", min_value=1, value=3, help="Number of transactions within a short time frame to trigger an alert")
    with col2:
        st.number_input("Large Transfer Threshold ($)", min_value=1000, value=10000, step=1000, help="Amount above which a transaction is considered large")

    st.markdown('<h2 class="section-header">Data Refresh Rate</h2>', unsafe_allow_html=True)
    st.slider("Refresh Interval (minutes)", min_value=1, max_value=60, value=5, help="How often the dashboard should fetch new data")

    # Add a save button (note: this doesn't actually save settings in this example)
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")

# Footer
st.markdown("---")
st.markdown("Developed by DCP | © 2024")