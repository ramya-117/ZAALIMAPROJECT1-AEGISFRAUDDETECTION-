
## 📁 **deploy_to_github.bat** (Auto GitHub Upload)

```bat
@echo off
title Deploy Aegis to GitHub
echo.
echo 🚀 Deploying Aegis to GitHub...
echo.

echo ✅ Initializing Git...
git init

echo ✅ Adding files to Git...
git add .

echo ✅ Making first commit...
git commit -m "feat: Aegis Fraud Detection System v2.0 - Complete production-ready system with real-time ML fraud detection, Kafka streaming, and email alerts"

echo.
echo 📝 Please create a new repository on GitHub.com named: aegis-fraud-detection
echo 📝 Then run these commands:
echo.
echo    git remote add origin https://github.com/ramya-117/ZAALIMA-PROJECT1.git
echo    git branch -M main
echo    git push -u origin main
echo.

echo 🔗 Or use GitHub Desktop to push your repository
echo.
echo ✅ Local Git repository ready for GitHub!
pause