"""
Initial Model Training Script
Run this first to create the models/ directory with trained models
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
from pathlib import Path
import logging

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False
    print(" TensorFlow not available, skipping Autoencoder training")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.model_path = Path("models")
        self.model_path.mkdir(exist_ok=True)
        
    def generate_training_data(self, n_samples=5000):
        """Generate synthetic training data"""
        logger.info(f"Generating {n_samples} training samples...")
        
        np.random.seed(42)
        data = []
        
        for i in range(n_samples):
            # 95% normal transactions
            if np.random.random() > 0.05:
                amount = np.random.uniform(30, 400)
                time_since = np.random.uniform(2, 48)
                velocity = np.random.uniform(0.3, 3.5)
                is_intl = np.random.choice([0, 1], p=[0.85, 0.15])
                hour = np.random.randint(6, 23)
            else:  # 5% anomalies
                amount = np.random.uniform(800, 5000)
                time_since = np.random.uniform(0.01, 1.0)
                velocity = np.random.uniform(8, 25)
                is_intl = 1
                hour = np.random.choice([1, 2, 3, 23])
            
            day = np.random.randint(0, 7)
            
            features = [
                amount,
                time_since,
                velocity,
                is_intl,
                hour,
                day,
                np.log1p(amount),
                np.log1p(velocity),
                np.log1p(time_since),
                int(day >= 5),  # is_weekend
                int(hour < 6 or hour > 22)  # is_night
            ]
            
            data.append(features)
        
        return np.array(data)
    
    def train_isolation_forest(self, X):
        """Train Isolation Forest model"""
        logger.info("Training Isolation Forest...")
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train model
        model = IsolationForest(
            contamination=0.05,
            random_state=42,
            n_estimators=100,
            max_samples=256,
            n_jobs=-1
        )
        model.fit(X_scaled)
        
        # Save model and scaler
        joblib.dump(model, self.model_path / "isolation_forest.pkl")
        joblib.dump(scaler, self.model_path / "if_scaler.pkl")
        
        logger.info(" Isolation Forest saved")
        return model, scaler
    
    def train_autoencoder(self, X):
        """Train Autoencoder model"""
        if not KERAS_AVAILABLE:
            logger.warning(" TensorFlow not available, skipping Autoencoder")
            return None, None
        
        logger.info("Training Autoencoder...")
        
        # Scale data
        scaler = MinMaxScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Build autoencoder
        input_dim = X.shape[1]
        encoder_input = layers.Input(shape=(input_dim,))
        encoded = layers.Dense(8, activation='relu')(encoder_input)
        encoded = layers.Dense(4, activation='relu')(encoded)
        decoded = layers.Dense(8, activation='relu')(encoded)
        decoded = layers.Dense(input_dim, activation='sigmoid')(decoded)
        
        autoencoder = keras.Model(encoder_input, decoded)
        autoencoder.compile(optimizer='adam', loss='mse')
        
        # Train
        autoencoder.fit(
            X_scaled, X_scaled,
            epochs=50,
            batch_size=32,
            shuffle=True,
            verbose=1,
            validation_split=0.1
        )
        
        # Save model and scaler
        autoencoder.save(self.model_path / "autoencoder.h5")
        joblib.dump(scaler, self.model_path / "ae_scaler.pkl")
        
        logger.info("Autoencoder saved")
        return autoencoder, scaler
    
    def evaluate_models(self, X, if_model, if_scaler, ae_model, ae_scaler):
        """Evaluate models on test data"""
        logger.info("Evaluating models...")
        
        # Generate test data with labels
        X_test_normal = self.generate_training_data(1000)
        
        # Generate fraud samples
        X_test_fraud = []
        for _ in range(100):
            fraud_sample = [
                np.random.uniform(1000, 5000),  # amount
                np.random.uniform(0.01, 0.5),    # time_since
                np.random.uniform(10, 25),       # velocity
                1,                               # is_intl
                np.random.choice([1, 2, 3]),    # hour
                np.random.randint(0, 7),         # day
                0, 0, 0, 0, 0                    # derived features (will compute)
            ]
            # Compute derived features
            fraud_sample[6] = np.log1p(fraud_sample[0])
            fraud_sample[7] = np.log1p(fraud_sample[2])
            fraud_sample[8] = np.log1p(fraud_sample[1])
            fraud_sample[9] = int(fraud_sample[5] >= 5)
            fraud_sample[10] = int(fraud_sample[4] < 6 or fraud_sample[4] > 22)
            X_test_fraud.append(fraud_sample)
        
        X_test_fraud = np.array(X_test_fraud)
        
        # Combine
        X_test = np.vstack([X_test_normal, X_test_fraud])
        y_test = np.array([0] * 1000 + [1] * 100)
        
        # Isolation Forest predictions
        X_if_scaled = if_scaler.transform(X_test)
        if_scores = if_model.decision_function(X_if_scaled)
        if_scores = 1 / (1 + np.exp(if_scores * 2))
        
        # Autoencoder predictions
        if ae_model:
            X_ae_scaled = ae_scaler.transform(X_test)
            reconstructions = ae_model.predict(X_ae_scaled, verbose=0)
            mse = np.mean(np.power(X_ae_scaled - reconstructions, 2), axis=1)
            ae_scores = np.clip(mse * 10, 0, 1)
        else:
            ae_scores = if_scores
        
        # Ensemble
        ensemble_scores = 0.4 * if_scores + 0.6 * ae_scores
        predictions = (ensemble_scores >= 0.65).astype(int)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        accuracy = accuracy_score(y_test, predictions)
        precision = precision_score(y_test, predictions)
        recall = recall_score(y_test, predictions)
        f1 = f1_score(y_test, predictions)
        
        logger.info(f" Evaluation Results:")
        logger.info(f"   Accuracy:  {accuracy:.3f}")
        logger.info(f"   Precision: {precision:.3f}")
        logger.info(f"   Recall:    {recall:.3f}")
        logger.info(f"   F1-Score:  {f1:.3f}")
        
    def run(self):
        """Run complete training pipeline"""
        logger.info(" Starting model training pipeline...")
        
        # Generate training data
        X_train = self.generate_training_data(5000)
        
        # Train models
        if_model, if_scaler = self.train_isolation_forest(X_train)
        ae_model, ae_scaler = self.train_autoencoder(X_train)
        
        # Evaluate
        self.evaluate_models(X_train, if_model, if_scaler, ae_model, ae_scaler)
        
        logger.info(" Training complete! Models saved to models/ directory")
        logger.info("You can now start the FastAPI service with: uvicorn api_service:app --reload")

if __name__ == "__main__":
    trainer = ModelTrainer()
    trainer.run()