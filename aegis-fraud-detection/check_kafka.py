"""
Kafka Health Check Script
"""

from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
import json

def check_kafka_health():
    print("🔍 Checking Kafka Health...")
    
    try:
        # Test producer connection
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("✅ Producer connected successfully")
        
        # Test consumer connection  
        consumer = KafkaConsumer(
            'transactions',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='earliest',
            enable_auto_commit=False
        )
        print("✅ Consumer connected successfully")
        
        # List topics
        admin_client = KafkaAdminClient(bootstrap_servers=['localhost:9092'])
        topics = admin_client.list_topics()
        print(f"✅ Topics found: {list(topics)}")
        
        # Send test message
        test_message = {"test": "health_check", "timestamp": "now"}
        producer.send('transactions', test_message)
        producer.flush()
        print("✅ Test message sent successfully")
        
        print("\n🎉 Kafka is working perfectly!")
        
    except Exception as e:
        print(f"❌ Kafka error: {str(e)}")

if __name__ == "__main__":
    check_kafka_health()