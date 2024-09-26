Real-time Fraud Detection System
This project implements a real-time fraud detection system using Apache Kafka, Apache Spark, MongoDB, and Streamlit. 
The system processes financial transactions, detects potential fraudulent activities, and visualizes the results in real-time.

The system consists of the following components:

Transaction Generator: Simulates financial transactions and sends them to Kafka.
Apache Kafka: Serves as a message broker for streaming transaction data.
Apache Spark: Consumes data from Kafka, processes it, and performs fraud detection.
MongoDB: Stores raw transactions and fraud alerts.
Streamlit Dashboard: Visualizes transaction data and fraud alerts in real-time.

Components
1. Transaction Generator

Simulates various types of financial transactions.
Injects fraudulent transactions based on predefined scenarios.
Sends transaction data to Kafka.

2. Apache Kafka

Handles real-time data streaming of transactions.
Provides a scalable and fault-tolerant messaging system.

3. Apache Spark

Consumes transaction data from Kafka.
Processes transactions in real-time.
Implements fraud detection algorithms:

Multiple transactions from the same user within a short time frame.
Large amount transfers.
Frequent transfers between the same sender and receiver.


Stores raw transactions and fraud alerts in MongoDB.

4. MongoDB

Stores raw transaction data.
Stores detected fraud alerts.

5. Streamlit Dashboard

Visualizes transaction data and fraud alerts in real-time.
Provides interactive charts and metrics for analysis.
