# Use an official PySpark image
FROM jupyter/pyspark-notebook:spark-3.5.0

USER root

# Install Kafka and MongoDB dependencies
RUN pip install kafka-python pymongo

# Create directory for checkpoints
RUN mkdir -p /opt/spark-checkpoints && chown ${NB_UID}:${NB_GID} /opt/spark-checkpoints

# Copy the PySpark script into the container
COPY transaction_processor.py /home/jovyan/transaction_processor.py

# Set the working directory
WORKDIR /home/jovyan

# Switch back to the notebook user
USER ${NB_UID}

# Command to run the PySpark script
CMD ["spark-submit", \
     "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.mongodb.spark:mongo-spark-connector_2.12:3.0.1", \
     "--conf", "spark.mongodb.input.uri=mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@${MONGO_HOST}/${MONGO_DATABASE}.transactions?authSource=admin", \
     "--conf", "spark.mongodb.output.uri=mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@${MONGO_HOST}/${MONGO_DATABASE}.fraud_alerts?authSource=admin", \
     "--conf", "spark.mongodb.input.socketTimeout=120000", \
     "--conf", "spark.mongodb.output.socketTimeout=120000", \
     "transaction_processor.py"]