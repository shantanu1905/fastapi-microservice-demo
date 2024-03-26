import pika
import json
from utils import OCRService
from utils import send_email_notification
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
RABBITMQ_URL = os.environ.get("RABBITMQ_URL")
    



# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_URL))
channel = connection.channel()
channel.queue_declare(queue='ocr_service')

# Callback function to process OCR requests
def on_request(ch, method, props, body):
    # Initialize OCR service
    ocr_service = OCRService()
    # Process OCR request
    response = ocr_service.process_request(body)

    # Send email notification
    send_email_notification(response['user_email'], response['ocr_text'], channel)

    # Publish response to the reply queue
    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=json.dumps(response))
    # Acknowledge the message delivery
    ch.basic_ack(delivery_tag=method.delivery_tag)
# Set prefetch count to 1
channel.basic_qos(prefetch_count=1)
# Consume messages from the 'ocr_service' queue
channel.basic_consume(queue='ocr_service', on_message_callback=on_request)
# Start consuming messages
print(" [x] Awaiting RPC requests")
channel.start_consuming()
