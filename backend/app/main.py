from contextlib import asynccontextmanager

import os

from datetime import date, timedelta

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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

from app.scheduler import build_schedule, compute_free_slots

# *** NEW ***
# Day numbers match the database: 0 = Monday ... 6 = Sunday
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


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

# *** NEW ***
# Addresses allowed to call this API from a browser, separated by commas.
# Locally the default is the frontend on port 3000; in the cloud this is set to the frontend's address.
allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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


@app.post(
    "/availability",
    response_model=schemas.AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability_block(
    block_in: schemas.AvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # *** NEW ***
    # Two blocks overlap when each one starts before the other ends.
    # Blocks that only touch (one ends exactly when the next starts) are allowed.
    overlapping_block = (
        db.query(models.AvailabilityBlock)
        .filter(
            models.AvailabilityBlock.user_id == current_user.id,
            models.AvailabilityBlock.day_of_week == block_in.day_of_week,
            models.AvailabilityBlock.start_time < block_in.end_time,
            models.AvailabilityBlock.end_time > block_in.start_time,
        )
        .first()
    )
    if overlapping_block is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This overlaps with your existing "
                + DAY_NAMES[overlapping_block.day_of_week]
                + " block from "
                + overlapping_block.start_time.strftime("%H:%M")
                + " to "
                + overlapping_block.end_time.strftime("%H:%M")
                + "."
            ),
        )

    block = models.AvailabilityBlock(
        user_id=current_user.id,
        day_of_week=block_in.day_of_week,
        start_time=block_in.start_time,
        end_time=block_in.end_time,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@app.get("/availability", response_model=list[schemas.AvailabilityResponse])
def list_availability_blocks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Only the logged-in user's own blocks, ordered by day and then start time
    return (
        db.query(models.AvailabilityBlock)
        .filter(models.AvailabilityBlock.user_id == current_user.id)
        .order_by(
            models.AvailabilityBlock.day_of_week,
            models.AvailabilityBlock.start_time,
        )
        .all()
    )


@app.delete("/availability/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability_block(
    block_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # The block must belong to this user; otherwise act as if it doesn't exist
    block = (
        db.query(models.AvailabilityBlock)
        .filter(
            models.AvailabilityBlock.id == block_id,
            models.AvailabilityBlock.user_id == current_user.id,
        )
        .first()
    )
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability block not found.",
        )
    db.delete(block)
    db.commit()


# *** NEW ***
def _session_minutes(session) -> int:
    start_minutes = session.start.hour * 60 + session.start.minute
    end_minutes = session.end.hour * 60 + session.end.minute
    return end_minutes - start_minutes


# *** NEW ***
@app.get("/schedule", response_model=schemas.ScheduleResponse)
def get_schedule(
    start: date | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # start is the first day of the 7-day plan; the page sends the user's local "today"
    if start is not None and not (date(2000, 1, 1) <= start <= date(2100, 12, 31)):
        raise HTTPException(
            status_code=422,
            detail="Start date must be between 2000 and 2100.",
        )
    start_date = start or date.today()
    plan_days = 7

    # Only this user's data, and only assignments that are not completed
    assignments = (
        db.query(models.Assignment)
        .filter(
            models.Assignment.user_id == current_user.id,
            models.Assignment.is_completed.is_(False),
        )
        .order_by(models.Assignment.due_date, models.Assignment.id)
        .all()
    )
    course_names = {
        course.id: course.name
        for course in db.query(models.Course)
        .filter(models.Course.user_id == current_user.id)
        .all()
    }
    blocks = (
        db.query(models.AvailabilityBlock)
        .filter(models.AvailabilityBlock.user_id == current_user.id)
        .all()
    )

    slots = compute_free_slots(blocks, start_date, days=plan_days)
    result = build_schedule(assignments, slots, start_date)

    assignments_by_id = {assignment.id: assignment for assignment in assignments}

    sessions = []
    for session in result.sessions:
        assignment = assignments_by_id[session.assignment_id]
        sessions.append(
            schemas.ScheduleSessionResponse(
                assignment_id=assignment.id,
                title=assignment.title,
                course_name=course_names.get(assignment.course_id, "Unknown course"),
                due_date=assignment.due_date,
                is_overdue=assignment.due_date < start_date,
                day=session.day,
                start_time=session.start,
                end_time=session.end,
            )
        )

    unscheduled = []
    for item in result.unscheduled:
        assignment = assignments_by_id[item.assignment_id]
        unscheduled.append(
            schemas.UnscheduledWorkResponse(
                assignment_id=assignment.id,
                title=assignment.title,
                course_name=course_names.get(assignment.course_id, "Unknown course"),
                due_date=assignment.due_date,
                is_overdue=assignment.due_date < start_date,
                hours_short=round(item.minutes / 60, 2),
            )
        )

    scheduled_minutes = sum(_session_minutes(session) for session in result.sessions)
    return schemas.ScheduleResponse(
        start_date=start_date,
        end_date=start_date + timedelta(days=plan_days - 1),
        scheduled_hours=round(scheduled_minutes / 60, 2),
        sessions=sessions,
        unscheduled=unscheduled,
    )