@echo off
chcp 65001 >nul
title 🛡️ Aegis Fraud Detection System
echo.
echo ===============================================
echo            AEGIS FRAUD DETECTION SYSTEM
echo ===============================================
echo.

echo ✅ Step 1: Activating Virtual Environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ❌ Virtual environment activation failed!
    echo 🔧 Creating new virtual environment...
    python -m venv venv
    call venv\Scripts\activate
)

echo ✅ Step 2: Installing Dependencies...
pip install -r requirements.txt

echo ✅ Step 3: Checking Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker not found! Please install Docker Desktop first.
    pause
    exit /b 1
)

echo ✅ Step 4: Starting Kafka & Zookeeper...
docker-compose down >nul 2>&1
docker-compose up -d

echo ⏳ Waiting for Kafka to start (30 seconds)...
timeout /t 30 /nobreak

echo ✅ Step 5: Checking if models exist...
if not exist "models\isolation_forest.pkl" (
    echo 🔧 Training initial models...
    python train_models.py
) else (
    echo ✅ Models already trained
)

echo ✅ Step 6: Starting FastAPI Backend (Port 8000)...
start cmd /k "title AEGIS-API && uvicorn api_service:app --reload --host 0.0.0.0 --port 8000"

echo ✅ Step 7: Starting Kafka Consumer...
timeout /t 3 /nobreak
start cmd /k "title AEGIS-Kafka-Consumer && python kafka_consumer.py"

echo ✅ Step 8: Starting Streamlit Dashboard (Port 8501)...
timeout /t 5 /nobreak
start cmd /k "title AEGIS-Dashboard && streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0"

echo.
echo ===============================================
echo 🎉 SYSTEM STARTED SUCCESSFULLY!
echo ===============================================
echo.
echo 📊 Live Dashboard: http://localhost:8501
echo 🔧 API Documentation: http://localhost:8000/docs
echo 📧 Test Email System: http://localhost:8000/test-email
echo 🐳 Kafka UI: http://localhost:8080
echo.
echo ⚠️  Please wait 1-2 minutes for all services to fully start
echo 📝 Check all command windows for any startup errors
echo.
echo Press any key to close this window...
pause >nul