from contextlib import asynccontextmanager

# *** NEW ***
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# *** NEW ***
from sqlalchemy.orm import Session

# *** NEW ***
from app import models, schemas
from app.database import Base, engine, get_db
from app.security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables on startup if they don't exist yet
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="StudyStack",
    description="Study planner that tracks assignments and suggests a weekly schedule.",
    version="0.1.0",
    lifespan=lifespan,
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


# *** NEW ***
@app.post(
    "/auth/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    # Treat emails as case-insensitive
    email = user_in.email.lower()

    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = models.User(
        email=email,
        password_hash=hash_password(user_in.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user