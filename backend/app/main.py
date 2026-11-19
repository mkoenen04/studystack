from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# *** NEW ***
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


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

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    # Reads the token from the "Authorization: Bearer <token>" header.
    # Add Depends(get_current_user) to any endpoint that requires a logged-in user.
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    return user


@app.get("/health")
def health_check():
    # Used by Docker, Cloud Run, and you to confirm the app is alive
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Welcome to StudyStack"}


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


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login_user(login_in: schemas.LoginRequest, db: Session = Depends(get_db)):
    email = login_in.email.lower()
    user = db.query(models.User).filter(models.User.email == email).first()

    # Same message for "no such email" and "wrong password" so attackers can't tell which emails exist
    if user is None or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    token = create_access_token(user.id, user.email)
    return schemas.TokenResponse(access_token=token)


@app.get("/auth/me", response_model=schemas.UserResponse)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    # Protected endpoint: only works with a valid token
    return current_user


# *** NEW ***
@app.post(
    "/courses",
    response_model=schemas.CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    course_in: schemas.CourseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Course names must be unique per user (ignoring upper/lower case)
    duplicate = (
        db.query(models.Course)
        .filter(
            models.Course.user_id == current_user.id,
            func.lower(models.Course.name) == course_in.name.lower(),
        )
        .first()
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a course with this name.",
        )

    course = models.Course(user_id=current_user.id, name=course_in.name)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


# *** NEW ***
@app.get("/courses", response_model=list[schemas.CourseResponse])
def list_courses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Only the logged-in user's own courses
    return (
        db.query(models.Course)
        .filter(models.Course.user_id == current_user.id)
        .order_by(models.Course.name)
        .all()
    )


# *** NEW ***
@app.post(
    "/assignments",
    response_model=schemas.AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    assignment_in: schemas.AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # The course must exist AND belong to this user; otherwise act as if it doesn't exist
    course = (
        db.query(models.Course)
        .filter(
            models.Course.id == assignment_in.course_id,
            models.Course.user_id == current_user.id,
        )
        .first()
    )
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )

    assignment = models.Assignment(
        user_id=current_user.id,
        course_id=course.id,
        title=assignment_in.title,
        due_date=assignment_in.due_date,
        estimated_hours=assignment_in.estimated_hours,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


# *** NEW ***
@app.get("/assignments", response_model=list[schemas.AssignmentResponse])
def list_assignments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Only the logged-in user's own assignments, earliest due date first
    return (
        db.query(models.Assignment)
        .filter(models.Assignment.user_id == current_user.id)
        .order_by(models.Assignment.due_date, models.Assignment.id)
        .all()
    )