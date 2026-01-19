from fastapi import FastAPI
from app.api import documents, processing

app = FastAPI()

app.include_router(documents.router)
app.include_router(processing.router)

@app.get("/")
def health():
    return {"status": "ok"}
