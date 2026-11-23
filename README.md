# StudyStack

A study planner for college students. StudyStack tracks courses and assignments, lets students enter the times they are free to study each week, and generates a 7-day study schedule built around those real free times.

- **Live app:** https://studystack-frontend-758742302139.us-central1.run.app
- **API docs (live):** https://studystack-backend-758742302139.us-central1.run.app/docs

> **Note:** the live demo uses a Google Cloud free-trial database that lasts 30 days. After the trial ends and the database is removed, the deployed app may stop working. The whole app runs locally with one command (see [Running locally](#running-locally)).

## Project status

**Sprint 1 (MVP) is complete: 8 user stories, 38 story points.**

| Feature | Status |
|---|---|
| Registration and login (bcrypt password hashing, JWT tokens) | Done |
| Courses and assignments (each user sees only their own data) | Done |
| Availability settings (weekly time blocks, several per day, overlapping blocks rejected) | Done |
| Schedule generator (earliest deadline first, shows work that does not fit) | Done for the MVP |
| Weekly calendar view and navigation (Schedule, Assignments, Availability) | Done |
| Docker and docker-compose (backend, frontend, and database start with one command) | Done |
| Manual deployment to Google Cloud Run with a Cloud SQL database | Done |
| Assignment priority field, spreading work evenly across days | Planned |
| Marking assignments complete, editing and deleting | Planned |
| Dashboard of upcoming deadlines and progress | Planned (Sprint 3) |
| Automated testing and CI/CD with GitHub Actions | Planned (Sprint 2) |

## Screenshots

**Weekly schedule** with the navbar, the 7-day calendar, and work that did not fit:

![Weekly schedule view](docs/screenshots/schedule.png)

**Assignments** (add a course, add an assignment, and list them by due date):

![Assignments view](docs/screenshots/assignments.png)

**Availability** (weekly time blocks, with overlap checking):

![Availability view](docs/screenshots/availability.png)

## How the schedule generator works

1. Each weekly availability block is repeated on its matching dates across a 7-day window. Blocks that touch (for example 09:00 to 11:00 and 11:00 to 12:00) are merged into one free slot.
2. Free slots are filled in time order. In each slot, the incomplete assignment with the earliest due date that still needs time and can still be finished by its due date gets the time first.
3. Work is split across slots when needed. Overdue assignments are scheduled first and may use any slot.
4. Work that does not fit is reported as hours short, so the student can see the shortfall instead of a silently incomplete plan.

The scheduling logic lives in `backend/app/scheduler.py`, separate from the web code, and is covered by 22 unit tests.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Plain HTML, CSS, and JavaScript, served by nginx |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL (16 in docker-compose, Cloud SQL PostgreSQL 18 in the cloud) |
| Authentication | bcrypt password hashing, JWT tokens |
| Tests | pytest |
| Containers | Docker, docker-compose |
| Hosting | Google Cloud Run, Artifact Registry, Cloud Build, Cloud SQL |
| Project management | Jira (stories, epics, sprints) and Confluence (documentation) |
| AI development tools | Claude (see [AI tool usage](#ai-tool-usage)) |

## Architecture

```
Browser
   |
   v
Frontend: nginx serving static HTML/JS      (Cloud Run)
   |  calls the API with a login token
   v
Backend: FastAPI                            (Cloud Run)
   |  Cloud SQL connection
   v
PostgreSQL                                  (Cloud SQL)
```

## Running locally

Requirements: [Docker Desktop](https://www.docker.com/products/docker-desktop/) and Git.

```bash
git clone https://github.com/mkoenen04/studystack.git
cd studystack
docker compose up --build
```

Then open:

- App: http://localhost:3000
- API docs: http://localhost:8080/docs

Stop everything with `docker compose down`. Add `-v` to also delete the local database data. If the page looks out of date after an update, hard refresh the browser (Ctrl+Shift+R).

The passwords and the secret key in `docker-compose.yml` are for local development only.

## Running the tests

With the stack running:

```bash
docker compose exec backend python -m pytest -q
```

The 22 tests cover free-slot computation (`backend/tests/test_scheduler.py`) and the scheduling algorithm (`backend/tests/test_build_schedule.py`).

## Project structure

```
studystack/
|-- backend/
|   |-- app/
|   |   |-- main.py         API endpoints and login check
|   |   |-- models.py       Database tables (users, courses, assignments, availability_blocks)
|   |   |-- schemas.py      Request and response shapes
|   |   |-- security.py     Password hashing and JWT tokens
|   |   |-- scheduler.py    Free slots and the scheduling algorithm
|   |   `-- database.py     Database connection
|   |-- tests/              Unit tests for the scheduler
|   |-- Dockerfile
|   `-- requirements.txt
|-- frontend/
|   |-- index.html          Single page with the three views and the navbar
|   |-- js/app.js           Page logic and API calls
|   |-- nginx/default.conf.template
|   `-- Dockerfile
|-- docker-compose.yml
`-- README.md
```

## API endpoints

All endpoints except `/health`, `/`, `/auth/register`, and `/auth/login` need an `Authorization: Bearer <token>` header.

| Method and path | Purpose |
|---|---|
| `GET /health` | Health check |
| `POST /auth/register` | Create an account (409 if the email is taken) |
| `POST /auth/login` | Log in and receive a token |
| `GET /auth/me` | The logged-in user |
| `POST /courses`, `GET /courses` | Add and list the user's courses |
| `POST /assignments`, `GET /assignments` | Add and list the user's assignments (sorted by due date) |
| `POST /availability`, `GET /availability` | Add and list weekly time blocks (409 on overlap) |
| `DELETE /availability/{id}` | Remove a time block |
| `GET /schedule?start=YYYY-MM-DD` | The 7-day plan and the work that did not fit |

## Configuration

Settings come from environment variables, so no addresses or secrets are written in the code.

| Service | Variable | Purpose | Default (local) |
|---|---|---|---|
| Backend | `DATABASE_URL` | Database connection | Local PostgreSQL |
| Backend | `SECRET_KEY` | Signs login tokens | A development-only value |
| Backend | `ALLOWED_ORIGINS` | Frontend addresses allowed to call the API (comma separated) | `http://localhost:3000` |
| Backend and frontend | `PORT` | Port to listen on | `8080` |
| Frontend | `API_URL` | Address of the backend, served to the page as `/js/config.js` | `http://localhost:8080` |

## Deployment to Google Cloud Run (manual)

The first deployment was done by hand from Cloud Shell. Replace `PROJECT_ID` with your project ID.

1. Create a project and enable the APIs: `gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com`
2. Create an image repository:
   `gcloud artifacts repositories create studystack --repository-format=docker --location=us-central1`
3. Create a Cloud SQL PostgreSQL instance named `studystack-db`, a database named `studystack`, and a user named `studystack` with a generated password. Keep the password out of Git.
4. Build and store both images:
   ```bash
   gcloud builds submit backend --tag us-central1-docker.pkg.dev/PROJECT_ID/studystack/backend:v1
   gcloud builds submit frontend --tag us-central1-docker.pkg.dev/PROJECT_ID/studystack/frontend:v1
   ```
5. Deploy the backend with the database attached. The settings go in a temporary file that is never committed:
   ```yaml
   # backend-env.yaml
   DATABASE_URL: "postgresql+psycopg2://studystack:<password>@/studystack?host=/cloudsql/PROJECT_ID:us-central1:studystack-db"
   SECRET_KEY: "<long random value>"
   ALLOWED_ORIGINS: "http://localhost:3000"
   ```
   ```bash
   gcloud run deploy studystack-backend \
     --image us-central1-docker.pkg.dev/PROJECT_ID/studystack/backend:v1 \
     --region us-central1 --allow-unauthenticated \
     --add-cloudsql-instances PROJECT_ID:us-central1:studystack-db \
     --env-vars-file backend-env.yaml
   ```
6. Deploy the frontend, pointing it at the backend's address:
   ```bash
   gcloud run deploy studystack-frontend \
     --image us-central1-docker.pkg.dev/PROJECT_ID/studystack/frontend:v1 \
     --region us-central1 --allow-unauthenticated \
     --set-env-vars API_URL=<backend address>
   ```
7. Allow the frontend to call the backend. Each Cloud Run service has two web addresses, so include both:
   ```bash
   gcloud run services update studystack-backend --region us-central1 \
     --update-env-vars "^@^ALLOWED_ORIGINS=<frontend address 1>,<frontend address 2>"
   ```

## Git workflow

- Every story is built on a feature branch (`feature/MDT-<number>-<name>`) and merged into `main` through a pull request.
- Commit messages start with the Jira ticket they belong to, for example `MDT-33: add earliest-deadline-first scheduling algorithm with unit tests`.

| Pull request | Story |
|---|---|
| #1 | MDT-39: Containerization in Docker |
| #2 | MDT-4: User registration |
| #3 | MDT-8: User login |
| #4 | MDT-20: Course and assignment entry |
| #5 | MDT-27: Availability settings |
| #6 | MDT-31: Weekly schedule generator |
| #7 | MDT-43: Initial Cloud Run deployment |
| #8 | MDT-13: Basic navigation |

## AI tool usage

I used Claude as a pair programmer throughout Sprint 1. It drafted code and setup steps. I ran everything, tested each piece, and decided what to keep. Each use is also logged, with dates, on the Confluence page **AI Tool Usage Log**.

| Area | What AI was used for | How I checked and changed it |
|---|---|---|
| Docker and compose (MDT-39) | Dockerfiles for the backend and frontend, docker-compose with PostgreSQL | Built and ran the containers; fixed empty files caused by unsaved edits |
| Registration and login (MDT-4, MDT-8) | Database model, password hashing, token creation, protected route, forms | Confirmed in PostgreSQL that passwords are stored as bcrypt hashes; tested valid, tampered, and missing tokens; fixed a database driver error (`psycopg` vs `psycopg2`) |
| Courses and assignments (MDT-20) | Models, endpoints, forms, and the assignment list | Tested validation and duplicates; tested with two users to confirm each sees only their own data |
| Availability (MDT-27) | Model, endpoints, form, and overlap validation | Noticed the first model (hours per day) could not support the planned overlap rule and had it replaced with time blocks; tested overlapping, touching, and contained blocks |
| Schedule generator (MDT-31) | Proposed the scheduling approach; wrote the algorithm, tests, endpoint, and calendar view | Approved the approach before any code; calculated a test scenario by hand and compared it with the API result; 22 unit tests |
| Navigation (MDT-13) | Pointed out the Jira subtasks assumed React and adapted them to plain JavaScript; wrote the views and navbar | Tested view switching, back, refresh, logged-out access, and logout |
| Cloud deployment (MDT-43) | Step-by-step Google Cloud setup, the configuration changes, and deploy commands | Checked costs before creating the database and set a budget alert; diagnosed the two-addresses CORS problem; replaced a database password that appeared in a screenshot |

Where AI output needed correcting: the database driver name, the first availability design, the Jira-versus-React mismatch, and browser caching that made a working change look broken.

## Known limitations and next steps

- The scheduler does not yet spread work evenly across days or weight assignments by priority.
- Assignments cannot be edited, deleted, or marked complete yet.
- Slots earlier today that have already passed are still used.
- Login tokens are kept in the browser's `localStorage` for simplicity; httpOnly cookies would be safer.
- Secrets are stored as Cloud Run environment variables; Secret Manager would be better.
- Next sprint: automated tests and deployment with GitHub Actions.

## Project documentation

- Jira board: https://meredithkoenen.atlassian.net/jira/software/projects/MDT/boards/35/backlog
- Confluence documentation: https://studystack-moderntech.atlassian.net/wiki/external/OGI0NDZmM2JmNjMzNDc2ZGI0OWEyYzRiNGNkZmExYWY
