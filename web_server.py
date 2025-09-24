from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok", "service": "FomoFrog Bot"}

@app.get("/rank")
def rank():
    # 여기서 PostgresClient 불러서 DB 조회
    return {"rankings": ["frog1", "frog2"]}
