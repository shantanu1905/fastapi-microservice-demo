import smtplib, os, json
from email.message import EmailMessage
from dotenv import load_dotenv
from email.mime.text import MIMEText


load_dotenv()

def notification(message):
    try:
        message = json.loads(message)
        receiver_address = message["email"]
        subject = message["subject"]
        body = message["body"]
        other = message["other"]

        sender_address = os.environ.get("GMAIL_ADDRESS")
        sender_password = os.environ.get("GMAIL_PASSWORD")
        

        # Gmail SMTP server settings
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_address, sender_password)

        # Compose the email message
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_address
        msg['To'] = receiver_address

        server.sendmail(sender_address, receiver_address, msg.as_string())
        server.quit()

        print("Mail Sent")
    except Exception as e:
        print(f"Failed to send email: {e}")
