from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
from db import get_input, get_output, save_input, save_output, conn

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "https://localhost",
    "http://localhost",
    "https://winnerspovtechnica26.vercel.app/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class InputBase(BaseModel):
    raw_assembly: str

class InputCreate(InputBase):
    pass

class OutputBase(BaseModel):
    input_id: int
    llm_output: str

class OutputCreate(OutputBase):
    pass

#testing
@app.get("/")
def root():
    return {"Hello": "world"}

@app.post("/inputs", status_code=status.HTTP_201_CREATED)
def create_input(payload: InputCreate):
    try:
        input_id = save_input(payload.raw_assembly)
        return {"input_id": input_id, "Message": "Input saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint 2: Save LLM / Gemini output (Step 4 of your pipeline)
@app.post("/outputs", status_code=status.HTTP_201_CREATED)
def create_output(payload: OutputCreate):
    try:
        save_output(payload.llm_output, payload.input_id)
        return {"message": "Output saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/outputs/{input_id}")
def fetch_output(input_id: int):
    try:
        llm_output = get_output(input_id)
        return {"input_id": input_id, "llm_output": llm_output}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scores/{input_id}")
def fetch_scores(input_id: int):
    try:
        with conn() as c:
            rows = c.execute(
                "SELECT candidate_name, similarity_score FROM scores WHERE input_id = ? ORDER BY similarity_score DESC;",
                (input_id,)
            ).fetchall()
            
            scores_list = [dict(row) for row in rows]
            return {"scores": scores_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))