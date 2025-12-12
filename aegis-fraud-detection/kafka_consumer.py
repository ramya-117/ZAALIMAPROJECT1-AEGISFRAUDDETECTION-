"""
Kafka Consumer for Fraud Detection
Consumes transactions from Kafka and calls the fraud detection API
"""

from kafka import KafkaConsumer
import requests
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FraudDetectionConsumer:
    """Kafka consumer that processes transactions through fraud detection API"""
    
    def __init__(self, 
                 bootstrap_servers: list = ['localhost:9092'],
                 api_url: str = 'http://localhost:8000'):
        self.consumer = KafkaConsumer(
            'transactions',
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='fraud-detection-group',
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,
            auto_commit_interval_ms=1000
        )
        self.api_url = api_url
        self.stats = {
            'total_processed': 0,
            'fraud_detected': 0,
            'api_errors': 0,
            'kafka_errors': 0,
            'start_time': datetime.now()
        }
    
    def call_fraud_api(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Call the fraud detection API"""
        try:
            # Convert timestamp string to proper format if needed
            api_transaction = transaction.copy()
            
            # Remove actual_fraud field as it's not in the API schema
            api_transaction.pop('actual_fraud', None)
            
            response = requests.post(
                f"{self.api_url}/predict",
                json=api_transaction,
                timeout=10  # 10 second timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                self.stats['api_errors'] += 1
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            self.stats['api_errors'] += 1
            return None
        except Exception as e:
            logger.error(f"Unexpected API error: {str(e)}")
            self.stats['api_errors'] += 1
            return None
    
    def process_transaction(self, transaction: Dict[str, Any]):
        """Process a single transaction"""
        try:
            # Call fraud detection API
            prediction = self.call_fraud_api(transaction)
            
            if prediction:
                self.stats['total_processed'] += 1
                
                if prediction['is_fraud']:
                    self.stats['fraud_detected'] += 1
                    logger.warning(
                        f"🚨 FRAUD DETECTED - {transaction['transaction_id']} - "
                        f"Score: {prediction['fraud_score']:.1%} - "
                        f"Amount: ${transaction['amount']:.2f}"
                    )
                else:
                    logger.info(
                        f"✅ APPROVED - {transaction['transaction_id']} - "
                        f"Score: {prediction['fraud_score']:.1%} - "
                        f"Amount: ${transaction['amount']:.2f}"
                    )
                
                # Log detailed prediction info every 10 transactions
                if self.stats['total_processed'] % 10 == 0:
                    logger.info(
                        f"📊 Processed: {self.stats['total_processed']} | "
                        f"Fraud: {self.stats['fraud_detected']} | "
                        f"API Errors: {self.stats['api_errors']}"
                    )
            
        except Exception as e:
            logger.error(f"Transaction processing error: {str(e)}")
            self.stats['kafka_errors'] += 1
    
    def start_consuming(self):
        """Start consuming messages from Kafka"""
        logger.info("🚀 Starting Kafka consumer for fraud detection...")
        logger.info(f"📡 Connecting to Kafka: {self.consumer.config['bootstrap_servers']}")
        logger.info(f"🔗 API endpoint: {self.api_url}")
        logger.info("⏳ Waiting for messages...")
        
        try:
            for message in self.consumer:
                try:
                    transaction = message.value
                    self.process_transaction(transaction)
                    
                except Exception as e:
                    logger.error(f"Message processing error: {str(e)}")
                    self.stats['kafka_errors'] += 1
                    
        except KeyboardInterrupt:
            logger.info("🛑 Stopping Kafka consumer...")
        except Exception as e:
            logger.error(f"❌ Consumer error: {str(e)}")
        finally:
            self.consumer.close()
            self.log_final_stats()
    
    def log_final_stats(self):
        """Log final statistics when consumer stops"""
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        fraud_rate = (self.stats['fraud_detected'] / self.stats['total_processed']) if self.stats['total_processed'] > 0 else 0
        
        logger.info("📈 Final Statistics:")
        logger.info(f"   Total Processed: {self.stats['total_processed']}")
        logger.info(f"   Fraud Detected: {self.stats['fraud_detected']}")
        logger.info(f"   Fraud Rate: {fraud_rate:.2%}")
        logger.info(f"   API Errors: {self.stats['api_errors']}")
        logger.info(f"   Kafka Errors: {self.stats['kafka_errors']}")
        logger.info(f"   Uptime: {uptime:.2f} seconds")
        logger.info(f"   Processing Rate: {self.stats['total_processed'] / uptime:.2f} tx/sec")

def check_api_health(api_url: str) -> bool:
    """Check if the API is healthy"""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def main():
    """Main function to start the consumer"""
    
    # Wait for API to be ready
    logger.info("🔍 Checking API health...")
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        if check_api_health('http://localhost:8000'):
            logger.info("✅ API is healthy!")
            break
        else:
            retry_count += 1
            logger.warning(f"⚠️ API not ready, retrying... ({retry_count}/{max_retries})")
            time.sleep(2)
    else:
        logger.error("❌ API not available after maximum retries")
        return
    
    # Start consumer
    consumer = FraudDetectionConsumer()
    consumer.start_consuming()

if __name__ == "__main__":
    main()