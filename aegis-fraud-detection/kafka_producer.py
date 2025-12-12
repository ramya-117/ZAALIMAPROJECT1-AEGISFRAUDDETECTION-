"""
Kafka Producer for Transaction Stream
Generates and sends realistic transaction data to Kafka
"""

from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TransactionGenerator:
    """Generates realistic transaction data"""
    
    def __init__(self):
        self.user_profiles = self._create_user_profiles()
        self.transaction_id = 1000
        self.user_last_transaction = {}
        
    def _create_user_profiles(self):
        """Create synthetic user profiles"""
        profiles = []
        countries = ['US', 'UK', 'CA', 'AU', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE']
        for i in range(150):
            profiles.append({
                'user_id': f'U{i:04d}',
                'home_country': random.choice(countries),
                'avg_transaction': random.uniform(30, 400),
                'transaction_frequency': random.uniform(1, 15),
                'preferred_merchants': random.sample(['retail', 'online', 'travel', 'food', 'entertainment'], 3)
            })
        return profiles
    
    def generate_transaction(self, fraud_probability: float = 0.12) -> Dict[str, Any]:
        """Generate a single transaction"""
        is_fraud = random.random() < fraud_probability
        user = random.choice(self.user_profiles)
        
        current_time = datetime.now()
        
        # Get time since last transaction for this user
        if user['user_id'] in self.user_last_transaction:
            time_since_last = (current_time - self.user_last_transaction[user['user_id']]).total_seconds() / 3600
        else:
            time_since_last = random.uniform(12, 72)
        
        self.user_last_transaction[user['user_id']] = current_time
        
        if is_fraud:
            # Fraudulent transaction characteristics
            amount = random.uniform(800, 5000)
            country = random.choice(['CN', 'RU', 'NG', 'BR', 'IN', 'PK', 'VN'])
            time_since_last = random.uniform(0.01, 0.8)  # Very quick succession
            velocity = random.uniform(8, 25)
            merchant = random.choice(['online', 'travel'])
            hour = random.choice([1, 2, 3, 4, 23, 22])  # Unusual hours
        else:
            # Normal transaction
            amount = user['avg_transaction'] * random.uniform(0.3, 2.5)
            country = user['home_country'] if random.random() > 0.15 else random.choice(['US', 'UK', 'CA', 'DE'])
            time_since_last = max(time_since_last, random.uniform(2, 48))
            velocity = random.uniform(0.3, 3.5)
            merchant = random.choice(user['preferred_merchants'])
            hour = current_time.hour
        
        transaction = {
            'transaction_id': f'TXN{self.transaction_id:08d}',
            'user_id': user['user_id'],
            'timestamp': current_time.isoformat(),
            'amount': round(amount, 2),
            'merchant_category': merchant,
            'country': country,
            'time_since_last_transaction': round(time_since_last, 2),
            'transaction_velocity': round(velocity, 2),
            'is_international': country != user['home_country'],
            'hour_of_day': hour,
            'day_of_week': current_time.weekday(),
            'actual_fraud': is_fraud  # Ground truth for evaluation
        }
        
        self.transaction_id += 1
        return transaction

class KafkaTransactionProducer:
    """Kafka producer for transaction data"""
    
    def __init__(self, bootstrap_servers: list = ['localhost:9092']):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,   # Retry on failure
            batch_size=16384,
            linger_ms=10
        )
        self.transaction_generator = TransactionGenerator()
        self.topic = 'transactions'
        
    def send_transaction(self, transaction: Dict[str, Any]):
        """Send a single transaction to Kafka"""
        try:
            future = self.producer.send(self.topic, transaction)
            # Optional: wait for confirmation
            # future.get(timeout=10)
            return True
        except Exception as e:
            logger.error(f"Failed to send transaction: {str(e)}")
            return False
    
    def start_streaming(self, interval: float = 2.0, max_transactions: int = None):
        """Start streaming transactions to Kafka"""
        logger.info(f"🚀 Starting Kafka transaction stream to topic: {self.topic}")
        logger.info(f"📊 Streaming interval: {interval} seconds")
        
        transaction_count = 0
        
        try:
            while True:
                if max_transactions and transaction_count >= max_transactions:
                    logger.info(f"Reached maximum transactions: {max_transactions}")
                    break
                
                # Generate transaction
                transaction = self.transaction_generator.generate_transaction()
                
                # Send to Kafka
                success = self.send_transaction(transaction)
                
                if success:
                    fraud_status = "🚨 FRAUD" if transaction['actual_fraud'] else "✅ NORMAL"
                    logger.info(f"📨 Sent {transaction['transaction_id']} - ${transaction['amount']:.2f} - {fraud_status}")
                    transaction_count += 1
                else:
                    logger.warning(f"⚠️ Failed to send {transaction['transaction_id']}")
                
                # Wait before next transaction
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Stopping Kafka producer...")
        except Exception as e:
            logger.error(f"❌ Producer error: {str(e)}")
        finally:
            self.producer.flush()
            self.producer.close()
            logger.info("✅ Kafka producer stopped")

def main():
    """Main function to start the producer"""
    producer = KafkaTransactionProducer()
    
    # Start streaming (remove max_transactions for continuous streaming)
    producer.start_streaming(interval=2.0, max_transactions=None)

if __name__ == "__main__":
    main()