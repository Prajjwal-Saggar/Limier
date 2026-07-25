
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Limier AML Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this later, fine for hackathon demo
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}