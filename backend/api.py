from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "https://localhost",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#testing
@app.get("/")
def root():
    return {"Hello": "world"}