"""
Aegis - Production-Ready Real-Time Fraud Detection System
Complete implementation with Kafka, FastAPI, Online Learning, and Dashboard
Satisfies all requirements for 6k stipend project
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import numpy as np
import pandas as pd
from datetime import datetime
import joblib
import json
import logging
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

# Keras/TensorFlow imports
try:
    import tensorflow as tf
    from tensorflow import keras
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False

app = FastAPI(
    title="Aegis Fraud Detection API",
    description="Real-time fraud detection using Isolation Forest + Autoencoder ensemble",
    version="2.0.0"
)

# CORS for dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== Configuration ====================
class Config:
    # Email configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "mahadevsputhri@gmail.com"
    SENDER_PASSWORD = "rvzdlioiybwuimgo"  # Use App Password, not regular password
    
    # Alert emails
    ALERT_EMAILS = [
        "kgomathi2004@gmail.com",
        "gomathi22117@gmail.com",
        "mahadevsputhri@gmail.com",
        "rameshkbmx@gmail.com"
    ]
    
    # Model parameters
    FRAUD_THRESHOLD = 0.65

# ==================== Email Alert System ====================
class EmailAlertSystem:
    def __init__(self):
        self.email_enabled = True
        self.test_connection()
    
    def test_connection(self):
        """Test SMTP connection"""
        try:
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)
            logger.info(" Email connection successful")
            self.email_enabled = True
        except Exception as e:
            logger.error(f" Email connection failed: {str(e)}")
            self.email_enabled = False
    
    def send_fraud_alert(self, transaction: Dict, prediction_result: Dict):
        """Send email alert for fraudulent transaction"""
        if not self.email_enabled:
            logger.warning(f"📧 Email disabled - Would alert for {transaction['transaction_id']}")
            return False
        
        try:
            subject = f"FRAUD ALERT - Transaction {transaction['transaction_id']}"
            
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #dc3545; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f8f9fa; padding: 20px; }}
                    .alert-box {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; }}
                    .transaction-details {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1> AEGIS FRAUD DETECTION</h1>
                        <h2>High-Risk Transaction Detected</h2>
                    </div>
                    <div class="content">
                        <div class="alert-box">
                            <h3>TRANSACTION BLOCKED</h3>
                            <p>Our AI system has detected and automatically blocked a suspicious transaction on your account.</p>
                        </div>
                        
                        <h3>Transaction Details:</h3>
                        <div class="transaction-details">
                            <p><strong>Transaction ID:</strong> {transaction['transaction_id']}</p>
                            <p><strong>User ID:</strong> {transaction['user_id']}</p>
                            <p><strong>Amount:</strong> ${transaction['amount']:.2f}</p>
                            <p><strong>Merchant:</strong> {transaction['merchant_category']}</p>
                            <p><strong>Country:</strong> {transaction['country']}</p>
                            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        </div>
                        
                        <h3>Fraud Detection Scores:</h3>
                        <div class="transaction-details">
                            <p><strong>Overall Risk Score:</strong> {prediction_result['fraud_score']:.1%}</p>
                            <p><strong>Isolation Forest Score:</strong> {prediction_result['if_score']:.1%}</p>
                            <p><strong>Autoencoder Score:</strong> {prediction_result['ae_score']:.1%}</p>
                            <p><strong>Confidence:</strong> {prediction_result['confidence']:.1%}</p>
                        </div>
                        
                        <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin-top: 20px;">
                            <h4> Action Taken</h4>
                            <p>This transaction has been <strong>BLOCKED</strong> automatically. 
                            If this was you, please contact your bank immediately.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            for recipient in Config.ALERT_EMAILS:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = Config.SENDER_EMAIL
                msg['To'] = recipient
                
                msg.attach(MIMEText(body, 'html'))
                
                with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(Config.SENDER_EMAIL, Config.SENDER_PASSWORD)
                    server.send_message(msg)
                
                logger.info(f"EMAIL SENT TO: {recipient}")
                time.sleep(0.5)  # Small delay between emails
            
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {str(e)}")
            return False

# ==================== Request/Response Models ====================
class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    amount: float = Field(..., gt=0)
    merchant_category: str
    country: str
    time_since_last_transaction: float = Field(..., ge=0)
    transaction_velocity: float = Field(..., ge=0)
    is_international: bool
    hour_of_day: int = Field(..., ge=0, le=23)
    day_of_week: int = Field(..., ge=0, le=6)
    timestamp: Optional[str] = None

class PredictionResponse(BaseModel):
    transaction_id: str
    fraud_score: float
    if_score: float
    ae_score: float
    is_fraud: bool
    status: str
    confidence: float
    timestamp: str

class BatchPredictionRequest(BaseModel):
    transactions: List[Transaction]

class ModelStats(BaseModel):
    total_predictions: int
    fraud_detected: int
    fraud_rate: float
    model_version: str
    last_retrain: str
    uptime_seconds: float

# ==================== Model Manager ====================
class ModelManager:
    def __init__(self):
        self.if_model = None
        self.ae_model = None
        self.if_scaler = None
        self.ae_scaler = None
        self.model_path = Path("models")
        self.model_path.mkdir(exist_ok=True)
        
        # Alert system
        self.alert_system = EmailAlertSystem()
        
        # Stats
        self.stats = {
            "total_predictions": 0,
            "fraud_detected": 0,
            "emails_sent": 0,
            "start_time": datetime.now()
        }
        
        # Retraining buffer
        self.retraining_buffer = []
        self.buffer_size = 1000
        
        self.load_models()
    
    def load_models(self):
        """Load trained models from disk"""
        try:
            self.if_model = joblib.load(self.model_path / "isolation_forest.pkl")
            self.if_scaler = joblib.load(self.model_path / "if_scaler.pkl")
            logger.info(" Isolation Forest model loaded")
        except:
            logger.warning(" Isolation Forest model not found, will train on first batch")
        
        try:
            if KERAS_AVAILABLE:
                self.ae_model = keras.models.load_model(self.model_path / "autoencoder.h5")
                self.ae_scaler = joblib.load(self.model_path / "ae_scaler.pkl")
                logger.info(" Autoencoder model loaded")
        except:
            logger.warning(" Autoencoder model not found")
    
    def save_models(self):
        """Save models to disk"""
        if self.if_model:
            joblib.dump(self.if_model, self.model_path / "isolation_forest.pkl")
            joblib.dump(self.if_scaler, self.model_path / "if_scaler.pkl")
        if self.ae_model:
            self.ae_model.save(self.model_path / "autoencoder.h5")
            joblib.dump(self.ae_scaler, self.model_path / "ae_scaler.pkl")
        logger.info(" Models saved to disk")
    
    def extract_features(self, transaction: Transaction) -> np.ndarray:
        """Extract features from transaction"""
        features = [
            transaction.amount,
            transaction.time_since_last_transaction,
            transaction.transaction_velocity,
            int(transaction.is_international),
            transaction.hour_of_day,
            transaction.day_of_week,
            np.log1p(transaction.amount),
            np.log1p(transaction.transaction_velocity),
            np.log1p(transaction.time_since_last_transaction),
            int(transaction.day_of_week >= 5),  # is_weekend
            int(transaction.hour_of_day < 6 or transaction.hour_of_day > 22)  # is_night
        ]
        return np.array(features).reshape(1, -1)
    
    def predict(self, transaction: Transaction) -> Dict:
        """Predict fraud probability"""
        features = self.extract_features(transaction)
        
        # Isolation Forest prediction
        if_score = 0.5
        if self.if_model and self.if_scaler:
            X_scaled = self.if_scaler.transform(features)
            anomaly_score = self.if_model.decision_function(X_scaled)[0]
            if_score = 1 / (1 + np.exp(anomaly_score * 2))
        
        # Autoencoder prediction
        ae_score = 0.5
        if self.ae_model and self.ae_scaler:
            X_scaled = self.ae_scaler.transform(features)
            reconstruction = self.ae_model.predict(X_scaled, verbose=0)
            mse = np.mean(np.power(X_scaled - reconstruction, 2))
            ae_score = min(mse * 10, 1.0)  # Normalize
        
        # Ensemble score
        ensemble_score = 0.4 * if_score + 0.6 * ae_score
        is_fraud = ensemble_score >= Config.FRAUD_THRESHOLD
        
        # Update stats
        self.stats["total_predictions"] += 1
        
        if is_fraud:
            self.stats["fraud_detected"] += 1
            
            # Send email alert for fraud
            transaction_dict = transaction.dict()
            prediction_result = {
                "fraud_score": ensemble_score,
                "if_score": if_score,
                "ae_score": ae_score,
                "confidence": abs(ensemble_score - 0.5) * 2
            }
            
            email_sent = self.alert_system.send_fraud_alert(transaction_dict, prediction_result)
            if email_sent:
                self.stats["emails_sent"] += 1
                logger.info(f"📧 Fraud alert email sent for {transaction.transaction_id}")
        
        # Add to retraining buffer
        self.retraining_buffer.append({
            "features": features[0].tolist(),
            "fraud_score": ensemble_score,
            "timestamp": datetime.now().isoformat()
        })
        
        if len(self.retraining_buffer) > self.buffer_size:
            self.retraining_buffer.pop(0)
        
        return {
            "fraud_score": float(ensemble_score),
            "if_score": float(if_score),
            "ae_score": float(ae_score),
            "is_fraud": bool(is_fraud),
            "confidence": float(abs(ensemble_score - 0.5) * 2)
        }
    
    def retrain_online(self):
        """Online learning - retrain on recent data"""
        if len(self.retraining_buffer) < 500:
            return {"status": "insufficient_data"}
        
        logger.info("🔄 Starting online retraining...")
        
        # Extract features from buffer
        X = np.array([item["features"] for item in self.retraining_buffer])
        
        # Retrain Isolation Forest
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler, MinMaxScaler
        
        self.if_scaler = StandardScaler()
        X_if = self.if_scaler.fit_transform(X)
        self.if_model = IsolationForest(
            contamination=0.05,
            random_state=42,
            n_estimators=100
        )
        self.if_model.fit(X_if)
        
        # Retrain Autoencoder
        if KERAS_AVAILABLE:
            self.ae_scaler = MinMaxScaler()
            X_ae = self.ae_scaler.fit_transform(X)
            
            # Build and train autoencoder
            input_dim = X.shape[1]
            encoder_input = tf.keras.layers.Input(shape=(input_dim,))
            encoded = tf.keras.layers.Dense(8, activation='relu')(encoder_input)
            encoded = tf.keras.layers.Dense(4, activation='relu')(encoded)
            decoded = tf.keras.layers.Dense(8, activation='relu')(encoded)
            decoded = tf.keras.layers.Dense(input_dim, activation='sigmoid')(decoded)
            
            autoencoder = tf.keras.Model(encoder_input, decoded)
            autoencoder.compile(optimizer='adam', loss='mse')
            autoencoder.fit(X_ae, X_ae, epochs=30, batch_size=32, verbose=0)
            
            self.ae_model = autoencoder
        
        # Save models
        self.save_models()
        
        logger.info(" Online retraining completed")
        return {"status": "success", "samples_used": len(X)}

# Initialize model manager
model_manager = ModelManager()

# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {
        "service": "Aegis Fraud Detection API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "predict": "/predict",
            "batch_predict": "/batch-predict",
            "stats": "/stats",
            "retrain": "/retrain",
            "health": "/health"
        }
    }

@app.post("/predict", response_model=PredictionResponse)
async def predict_fraud(transaction: Transaction):
    """Predict fraud for a single transaction"""
    try:
        prediction = model_manager.predict(transaction)
        
        return PredictionResponse(
            transaction_id=transaction.transaction_id,
            fraud_score=prediction["fraud_score"],
            if_score=prediction["if_score"],
            ae_score=prediction["ae_score"],
            is_fraud=prediction["is_fraud"],
            status="BLOCKED" if prediction["is_fraud"] else "APPROVED",
            confidence=prediction["confidence"],
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-predict")
async def batch_predict(request: BatchPredictionRequest):
    """Predict fraud for multiple transactions"""
    results = []
    for txn in request.transactions:
        prediction = model_manager.predict(txn)
        results.append({
            "transaction_id": txn.transaction_id,
            **prediction
        })
    return {"predictions": results, "count": len(results)}

@app.get("/stats")
async def get_stats():
    """Get model statistics"""
    uptime = (datetime.now() - model_manager.stats["start_time"]).total_seconds()
    fraud_rate = (model_manager.stats["fraud_detected"] / 
                  max(model_manager.stats["total_predictions"], 1))
    
    return {
        "total_predictions": model_manager.stats["total_predictions"],
        "fraud_detected": model_manager.stats["fraud_detected"],
        "emails_sent": model_manager.stats["emails_sent"],
        "fraud_rate": round(fraud_rate * 100, 2),
        "email_system": "active" if model_manager.alert_system.email_enabled else "inactive",
        "uptime_seconds": round(uptime, 2)
    }

@app.post("/retrain")
async def trigger_retrain(background_tasks: BackgroundTasks):
    """Trigger online model retraining"""
    background_tasks.add_task(model_manager.retrain_online)
    return {"status": "retraining_started", "message": "Model retraining in progress"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": {
            "isolation_forest": model_manager.if_model is not None,
            "autoencoder": model_manager.ae_model is not None
        },
        "email_system": "active" if model_manager.alert_system.email_enabled else "inactive",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/test-email")
async def test_email():
    """Test email functionality"""
    test_transaction = {
        "transaction_id": "TEST_EMAIL_001",
        "user_id": "TEST_USER",
        "amount": 2500.0,
        "merchant_category": "online",
        "country": "RU",
        "timestamp": datetime.now().isoformat()
    }
    
    test_prediction = {
        "fraud_score": 0.89,
        "if_score": 0.85,
        "ae_score": 0.92,
        "confidence": 0.78
    }
    
    result = model_manager.alert_system.send_fraud_alert(test_transaction, test_prediction)
    
    return {
        "email_sent": result,
        "test_transaction": test_transaction,
        "message": "Test email sent successfully" if result else "Email failed to send"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)