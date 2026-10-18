from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List
from helper import call_llm
from db import get_input, get_output, save_input, save_output, save_scores, get_scores, conn
from fastapi import Query
from model_inference import get_model, InferenceInputError

app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "https://localhost",
    "http://localhost",
    "http://127.0.0.1",
    "https://winnerspovtechnica26.vercel.app/",
    "https://technica-2026-k3oz-au5a3apc0-testiz.vercel.app/",
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

class ScoreItem(BaseModel):
    candidate_name: str
    similarity_score: float

class ScoresCreate(BaseModel):
    input_id: int
    scores: List[ScoreItem]

#testing
@app.get("/")
def root():
    return {"Hello": "world"}

@app.post("/run-pipeline", status_code=status.HTTP_201_CREATED)
def run_pipeline(
    payload: InputCreate,
    top_k: int = Query(default=8, ge=1, le=50)
):
    try:
        input_id = save_input(payload.raw_assembly)
        
        assembly_text = get_input(input_id)

        prediction = get_model().predict(
            assembly_text,
            top_k=top_k
        )

        matches = [
            (r["candidate_name"], r["similarity_score"])
            for r in prediction["results"]
        ]

        save_scores(input_id, matches)
        
        gemini_result = call_llm(matches)
        
        save_output(gemini_result, input_id)
        
        return {
            "input_id": input_id,
            "message": "Pipeline ran and everything saved to DB successfully!"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/inputs", status_code=status.HTTP_201_CREATED)
def create_input(payload: InputCreate):
    try:
        input_id = save_input(payload.raw_assembly)
        return {"input_id": input_id, "Message": "Input saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inputs/{input_id}", status_code=status.HTTP_200_OK)
def fetch_input(input_id: int):
    try:
        raw_assembly = get_input(input_id)
        return {"input_id": input_id, "raw_assembly": raw_assembly}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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

@app.get("/outputs/{input_id}", status_code=status.HTTP_200_OK)
def fetch_output(input_id: int):
    try:
        llm_output = get_output(input_id)
        return {"input_id": input_id, "llm_output": llm_output}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/scores/{input_id}", status_code=status.HTTP_200_OK)
def fetch_scores(input_id: int):
    try:
        scores_list = get_scores(input_id)
        return {"scores": scores_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scores", status_code=status.HTTP_201_CREATED)
def create_scores(payload: ScoresCreate):
    try:
        matches = [(item.candidate_name, item.similarity_score) for item in payload.scores]
        save_scores(payload.input_id, matches)
        
        return {"message": "Scores saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))