from fastapi import FastAPI, HTTPException ,  File, UploadFile
import fastapi as _fastapi
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from jwt.exceptions import DecodeError
from pydantic import BaseModel
import requests
import base64
import pika
import logging
import os
import jwt
import rpc_client

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)

# Retrieve environment variables
JWT_SECRET = os.environ.get("JWT_SECRET")
AUTH_BASE_URL = os.environ.get("AUTH_BASE_URL")
RABBITMQ_URL = os.environ.get("RABBITMQ_URL")

# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_URL)) # add container name in docker
channel = connection.channel()
channel.queue_declare(queue='gatewayservice')
channel.queue_declare(queue='ocr_service')


# JWT token validation
async def jwt_validation(token: str = _fastapi.Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except DecodeError:
        raise HTTPException(status_code=401, detail="Invalid JWT token")



# Pydantic models for request body
class GenerateUserToken(BaseModel):
    username: str
    password: str
   

class UserCredentials(BaseModel):
    username: str
    password: str

class UserRegisteration(BaseModel):
    name: str
    email: str
    password: str

class GenerateOtp(BaseModel):
    email: str

class VerifyOtp(BaseModel):
    email: str
    otp: int


# Authentication routes
@app.post("/auth/login", tags=['Authentication Service'])
async def login(user_data: UserCredentials):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/token", json={"username": user_data.username, "password": user_data.password})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

@app.post("/auth/register", tags=['Authentication Service'])
async def registeration(user_data:UserRegisteration):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/users", json={"name":user_data.name,"email": user_data.email, "password": user_data.password})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

@app.post("/auth/generate_otp", tags=['Authentication Service'])
async def generate_otp(user_data:GenerateOtp):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/users/generate_otp", json={"email":user_data.email})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")

@app.post("/auth/verify_otp", tags=['Authentication Service'])
async def verify_otp(user_data:VerifyOtp):
    try:
        response = requests.post(f"{AUTH_BASE_URL}/api/users/verify_otp", json={"email":user_data.email ,"otp":user_data.otp})
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Authentication service is unavailable")



# ml microservice route - OCR route
@app.post('/ocr' ,  tags=['Machine learning Service'] )
def ocr(file: UploadFile = File(...),
        payload: dict = _fastapi.Depends(jwt_validation)):
    
    # Save the uploaded file to a temporary location
    with open(file.filename, "wb") as buffer:
        buffer.write(file.file.read())

    ocr_rpc = rpc_client.OcrRpcClient()

    with open(file.filename, "rb") as buffer:
        file_data = buffer.read()
        file_base64 = base64.b64encode(file_data).decode()
    
    request_json = {
        'user_name':payload['name'],
        'user_email':payload['email'],
        'user_id':payload['id'],
        'file': file_base64
    }
   
    # Call the OCR microservice with the request JSON
    response = ocr_rpc.call(request_json)

    # Delete the temporary image file
    os.remove(file.filename)

    return response



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5001, reload=True)