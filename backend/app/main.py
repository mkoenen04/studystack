from fastapi import FastAPI

app = FastAPI(
    title="StudyStack",
    description="Study planner that tracks assignments and suggests a weekly schedule.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    # Used by Docker, Cloud Run, and you to confirm the app is alive
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Welcome to StudyStack"}