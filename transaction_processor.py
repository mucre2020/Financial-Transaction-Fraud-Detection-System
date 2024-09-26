from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, count, sum
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType
import os
import logging
from urllib.parse import quote_plus
from pymongo import MongoClient

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB credentials from environment variables
mongodb_username = os.getenv('MONGO_USERNAME', 'sa')
mongodb_password = quote_plus(os.getenv('MONGO_PASSWORD', 'RFL@2o2o'))
mongodb_host = os.getenv('MONGO_HOST', 'mongodb:27017')
database_name = os.getenv('MONGO_DATABASE', 'fraud_detection_db')

# Construct the MongoDB URI
mongodb_uri = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}/{database_name}?authSource=admin"
logger.info(f"MongoDB URI: {mongodb_uri.replace(mongodb_password, '****')}")

# Test MongoDB connection
def test_mongodb_connection():
    try:
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        db.test_collection.insert_one({"test": "document"})
        logger.info("Successfully wrote test document to MongoDB")
        result = db.test_collection.find_one({"test": "document"})
        logger.info(f"Retrieved test document from MongoDB: {result}")
    except Exception as e:
        logger.error("Failed to connect to MongoDB", exc_info=True)

# Call the test function
test_mongodb_connection()

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("TransactionProcessor") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .config("spark.mongodb.input.uri", mongodb_uri) \
    .config("spark.mongodb.output.uri", mongodb_uri) \
    .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.mongodb.input.socketTimeout", "120000") \
    .config("spark.mongodb.output.socketTimeout", "120000") \
    .getOrCreate()

logger.info("Spark Session initialized successfully")

# Define schema for incoming transaction data
schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("sender", StringType(), True),
    StructField("receiver", StringType(), True),
    StructField("amount", FloatType(), True),
    StructField("transaction_type", StringType(), True),
    StructField("timestamp", TimestampType(), True)
])

# Kafka configuration
kafka_bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
logger.info(f"Kafka Bootstrap Servers: {kafka_bootstrap_servers}")

# Read streaming data from Kafka topic with adjusted options
transactions_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", "financial_transactions") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .option("maxOffsetsPerTrigger", 5000)  \
    .load()

logger.info("Kafka stream connected with updated configuration")

# Parse JSON data
parsed_df = transactions_df.select(
    from_json(col("value").cast("string"), schema).alias("parsed_value")
).select("parsed_value.*")

logger.info("Parsed incoming transactions data from Kafka")

# Function to validate data
def validate_data(df):
    logger.info("Validating data before writing to MongoDB")
    logger.info(f"Schema: {df.schema}")
    logger.info(f"Row count: {df.count()}")
    df.show(5, truncate=False)

# Store raw transactions in MongoDB
def store_raw_transactions(df, epoch_id):
    try:
        logger.info(f"Storing raw transactions for batch ID: {epoch_id}")
        validate_data(df)
        df.write \
            .format("mongo") \
            .mode("append") \
            .option("database", database_name) \
            .option("collection", "transactions") \
            .option("writeConcern.w", "majority") \
            .save()
        logger.info(f"Stored {df.count()} transactions in MongoDB")
    except Exception as e:
        logger.error("Error storing raw transactions", exc_info=True)
    finally:
        # Explicitly call garbage collection
        import gc
        gc.collect()

parsed_df.writeStream \
    .foreachBatch(store_raw_transactions) \
    .option("checkpointLocation", "/opt/spark-checkpoints/raw_transactions") \
    .start()

logger.info("Started streaming and storing raw transactions to MongoDB")

# Detect multiple transactions from the same user within a short time frame
multiple_tx_df = parsed_df \
    .withWatermark("timestamp", "5 minutes") \
    .groupBy(window("timestamp", "1 minute"), "sender") \
    .agg(count("*").alias("transaction_count"), sum("amount").alias("total_amount")) \
    .filter(col("transaction_count") > 3)

logger.info("Detecting multiple transactions within a short time frame")

# Detect large amount transfers
large_transfer_df = parsed_df.filter(col("amount") > 10000)
logger.info("Detecting large amount transfers over 10,000")

# Detect frequent transfers between the same sender and receiver
frequent_transfer_df = parsed_df \
    .withWatermark("timestamp", "1 hour") \
    .groupBy(window("timestamp", "30 minutes"), "sender", "receiver") \
    .agg(count("*").alias("transfer_count")) \
    .filter(col("transfer_count") > 3)

logger.info("Detecting frequent transfers between the same sender and receiver")

# Function to store fraud alerts in MongoDB
def store_fraud_alerts(df, epoch_id):
    try:
        logger.info(f"Storing fraud alerts for batch ID: {epoch_id}")
        validate_data(df)
        df.write \
            .format("mongo") \
            .mode("append") \
            .option("database", database_name) \
            .option("collection", "fraud_alerts") \
            .option("writeConcern.w", "majority") \
            .save()
        logger.info(f"Stored {df.count()} fraud alerts in MongoDB")
    except Exception as e:
        logger.error("Error storing fraud alerts", exc_info=True)
    finally:
        # Explicitly call garbage collection
        import gc
        gc.collect()

# Start queries and store fraud detection results in MongoDB
multiple_tx_query = multiple_tx_df.writeStream \
    .foreachBatch(store_fraud_alerts) \
    .option("checkpointLocation", "/opt/spark-checkpoints/multiple_tx") \
    .start()

large_transfer_query = large_transfer_df.writeStream \
    .foreachBatch(store_fraud_alerts) \
    .option("checkpointLocation", "/opt/spark-checkpoints/large_transfer") \
    .start()

frequent_transfer_query = frequent_transfer_df.writeStream \
    .foreachBatch(store_fraud_alerts) \
    .option("checkpointLocation", "/opt/spark-checkpoints/frequent_transfer") \
    .start()

logger.info("Started fraud detection streams and storing alerts in MongoDB")

# Wait for the streams to finish
spark.streams.awaitAnyTermination()

# Final log message
logger.info("Spark application completed successfully")
