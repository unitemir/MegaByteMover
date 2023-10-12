from fastapi import FastAPI, UploadFile, HTTPException, Depends, File
import boto3
from starlette.middleware.cors import CORSMiddleware
import logging

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
CHUNK_SIZE = 1024 * 1024

s3 = boto3.client('s3',
                  endpoint_url='http://localhost:9000',
                  aws_access_key_id='minioadmin',
                  aws_secret_access_key='minioadmin',
                  config=boto3.session.Config(signature_version='s3v4'))


class FileWrapper:
    def __init__(self, file, chunk_size=1024*1024):
        self._file = file
        self._chunk_size = chunk_size
        self._buffer = b""

    def read(self, size=-1):
        while size > len(self._buffer):
            chunk = self._file.read(self._chunk_size)
            if not chunk:
                break
            self._buffer += chunk

        part = self._buffer[:size]
        self._buffer = self._buffer[size:]
        return part


@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    logger.info(f"Starting upload for file: {file.filename}")

    try:
        wrapped_file = FileWrapper(file.file)
        s3.upload_fileobj(wrapped_file, BUCKET_NAME, file.filename)

        logger.info(f"Successfully uploaded file: {file.filename}")
        return {"filename": file.filename, "status": "uploaded"}

    except Exception as e:
        logger.error(f"Failed to upload file: {file.filename}. Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
