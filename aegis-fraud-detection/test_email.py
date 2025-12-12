import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_email_system():
    print("🔧 Testing Email System...")
    
    # Your configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "example1@gmail.com"
    SENDER_PASSWORD = "XXXX XXXX XXXX XXXX"  # This should be an App Password
    
    RECIPIENTS = [
        "user1@gmail.com",
        "user2@gmail.com",
        "user3@gmail.com"
    ]
    
    try:
        print("1. Testing SMTP connection...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.ehlo()
        server.starttls()
        server.ehlo()
        print("✅ SMTP connection successful")
        
        print("2. Testing login...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        print("✅ Login successful")
        
        print("3. Sending test email...")
        
        for recipient in RECIPIENTS:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "TEST: Aegis Fraud Detection System"
            msg['From'] = SENDER_EMAIL
            msg['To'] = recipient
            
            html = f"""
            <html>
            <body>
                <h2 style="color: #dc3545;">🛡️ AEGIS TEST EMAIL</h2>
                <p>This is a test email from your fraud detection system.</p>
                <p><strong>Time:</strong> {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>If you receive this, your email system is working! </p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            server.send_message(msg)
            print(f"Email sent to: {recipient}")
        
        server.quit()
        print("\n ALL EMAILS SENT SUCCESSFULLY!")
        
    except Exception as e:
        print(f" ERROR: {str(e)}")
        print("\n TROUBLESHOOTING:")
        print("1. Make sure you're using an App Password, not your regular Gmail password")
        print("2. Enable 2-Factor Authentication in your Google Account")
        print("3. Generate App Password: Google Account → Security → App passwords")
        print("4. Check if 'Less secure app access' is enabled (though App Password is better)")

if __name__ == "__main__":
    test_email_system()