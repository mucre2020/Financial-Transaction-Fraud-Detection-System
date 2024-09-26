db = db.getSiblingDB('fraud_detection_db');
db.createCollection('transactions');
db.createCollection('fraud_alerts');
db.transactions.createIndex({ "timestamp": 1 });
db.fraud_alerts.createIndex({ "timestamp": 1 });