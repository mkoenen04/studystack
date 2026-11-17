from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="StudyStack",
    description="Study planner that tracks assignments and suggests a weekly schedule.",
    version="0.1.0",
)

# Allow the frontend (served on port 3000) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    # Used by Docker, Cloud Run, and you to confirm the app is alive
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Welcome to StudyStack"}