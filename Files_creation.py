import os

folders = [
    "aegis-fraud-detection/models",
    "aegis-fraud-detection/logs",
    "aegis-fraud-detection/data"
]

files = [
    "aegis-fraud-detection/api_service.py",
    "aegis-fraud-detection/kafka_producer.py",
    "aegis-fraud-detection/kafka_consumer.py",
    "aegis-fraud-detection/dashboard.py",
    "aegis-fraud-detection/train_models.py",
    "aegis-fraud-detection/docker-compose.yml",
    "aegis-fraud-detection/Dockerfile",
    "aegis-fraud-detection/requirements.txt",
    "aegis-fraud-detection/models/isolation_forest.pkl",
    "aegis-fraud-detection/models/if_scaler.pkl",
    "aegis-fraud-detection/models/autoencoder.h5",
    "aegis-fraud-detection/models/ae_scaler.pkl",
    "aegis-fraud-detection/README.md"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)

for file in files:
    with open(file, "w") as f:
        pass  # Creates an empty file

print("Project structure created successfully.")