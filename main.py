from fastapi import FastAPI, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
import boto3

logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:63342"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = 'fastapi-fileuploader-2023'

s3 = boto3.client('s3',
                  endpoint_url='http://localhost:9000',
                  aws_access_key_id='admin',
                  aws_secret_access_key='password',
                  config=boto3.session.Config(signature_version='s3v4'))

class Part(BaseModel):
    PartNumber: int
    ETag: str


class CompleteUploadRequest(BaseModel):
    filename: str
    upload_id: str
    parts: List[Part]


@app.post("/upload/")
async def upload_part(filename: str, part_number: int, upload_id: str, file: UploadFile = File(...)):
    logger.info(f"Initiating upload for file: {filename}, part number: {part_number}, upload ID: {upload_id}")
    part = file.file.read()

    response = s3.upload_part(
        Body=part,
        Bucket=BUCKET_NAME,
        Key=filename,
        PartNumber=part_number,
        UploadId=upload_id
    )

    logger.info(f"Part uploaded. ETag: {response['ETag']}")
    return {"etag": response["ETag"]}


@app.post("/upload/initiate/")
def initiate_upload(filename: str):
    logger.info(f"Initiating multipart upload for file: {filename}")
    response = s3.create_multipart_upload(Bucket=BUCKET_NAME, Key=filename)
    logger.info(f"Multipart upload initiated with ID: {response['UploadId']}")
    return {"upload_id": response["UploadId"]}


@app.post("/upload/complete/")
def complete_upload(request: CompleteUploadRequest):
    logger.info(
        f"Received request for complete_upload with filename: {request.filename}, upload_id: {request.upload_id}, parts: {request.parts}")
    parts_as_dicts = [{'PartNumber': part.PartNumber, 'ETag': part.ETag} for part in request.parts]

    try:
        s3.complete_multipart_upload(
            Bucket=BUCKET_NAME,
            Key=request.filename,
            UploadId=request.upload_id,
            MultipartUpload={"Parts": parts_as_dicts}
        )
        logger.info("Multipart upload completed successfully.")
        return {"status": "completed"}
    except Exception as e:
        logger.error(f"Error while completing multipart upload: {e}")
        raise e
