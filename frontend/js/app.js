// Address of the backend API as seen from the browser
const API_URL = "http://localhost:8080";
const TOKEN_KEY = "studystack_token";

// Day numbers match the backend: 0 = Monday ... 6 = Sunday
const DAY_NAMES = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// ----- Small helpers -----
function setMessage(element, text, isError) {
  // textContent (not innerHTML) so server text can never inject HTML
  element.textContent = text;
  element.style.color = isError ? "crimson" : "green";
}

function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// *** NEW ***
// Date helpers. Dates are handled as "YYYY-MM-DD" text and built from their parts,
// so the browser's time zone can never shift a date by a day.
function toIsoDate(dateObject) {
  const month = String(dateObject.getMonth() + 1).padStart(2, "0");
  const day = String(dateObject.getDate()).padStart(2, "0");
  return dateObject.getFullYear() + "-" + month + "-" + day;
}

// *** NEW ***
function parseIsoDate(text) {
  const parts = text.split("-");
  return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
}

// *** NEW ***
function addDaysIso(isoDate, offset) {
  const dateObject = parseIsoDate(isoDate);
  dateObject.setDate(dateObject.getDate() + offset);
  return toIsoDate(dateObject);
}

// *** NEW ***
function formatDayLabel(isoDate) {
  // Example: "Mon 11/23". JavaScript's getDay() starts on Sunday, so shift it to start on Monday.
  const dateObject = parseIsoDate(isoDate);
  const dayIndex = (dateObject.getDay() + 6) % 7;
  return DAY_NAMES[dayIndex].slice(0, 3) + " " + (dateObject.getMonth() + 1) + "/" + dateObject.getDate();
}

// Course names by id, so the assignment list can show names instead of numbers
let coursesById = {};

async function authFetch(path, options) {
  // Sends a request with the saved token; logs the user out if the token is rejected
  const settings = options || {};
  const headers = Object.assign({}, settings.headers, {
    Authorization: "Bearer " + getToken(),
  });
  const response = await fetch(API_URL + path, Object.assign({}, settings, { headers: headers }));
  if (response.status === 401) {
    clearToken();
    showLoggedOutView();
  }
  return response;
}

async function loadCourses() {
  const select = document.getElementById("assignment-course");
  select.replaceChildren();
  coursesById = {};

  try {
    const response = await authFetch("/courses");
    if (!response.ok) {
      return;
    }
    const courses = await response.json();

    if (courses.length === 0) {
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = "Add a course first";
      select.appendChild(placeholder);
      return;
    }

    for (const course of courses) {
      coursesById[course.id] = course.name;
      const option = document.createElement("option");
      option.value = String(course.id);
      option.textContent = course.name;
      select.appendChild(option);
    }
  } catch (error) {
    // Leave the dropdown empty; the user can refresh
  }
}

function renderAssignments(assignments) {
  const tableBody = document.getElementById("assignment-rows");
  const table = document.getElementById("assignment-table");
  const emptyText = document.getElementById("assignment-empty");
  tableBody.replaceChildren();

  if (assignments.length === 0) {
    table.hidden = true;
    emptyText.hidden = false;
    return;
  }

  table.hidden = false;
  emptyText.hidden = true;

  for (const assignment of assignments) {
    const row = document.createElement("tr");
    const cells = [
      assignment.title,
      coursesById[assignment.course_id] || "Unknown course",
      assignment.due_date,
      assignment.estimated_hours + " h",
    ];
    for (const text of cells) {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.appendChild(cell);
    }
    tableBody.appendChild(row);
  }
}

async function loadAssignments() {
  try {
    const response = await authFetch("/assignments");
    if (!response.ok) {
      return;
    }
    renderAssignments(await response.json());
  } catch (error) {
    // Leave the list as it is; the user can refresh
  }
}

function formatTime(timeText) {
  // The server sends "09:00:00"; show "09:00"
  return timeText.slice(0, 5);
}

const availabilityMessage = document.getElementById("availability-message");

// *** NEW ***
const scheduleMessage = document.getElementById("schedule-message");

async function removeAvailabilityBlock(blockId) {
  try {
    const response = await authFetch("/availability/" + blockId, { method: "DELETE" });
    if (response.status === 204) {
      setMessage(availabilityMessage, "Time block removed.", false);
    } else if (response.status === 404) {
      setMessage(availabilityMessage, "That time block no longer exists.", true);
    } else if (response.status !== 401) {
      setMessage(availabilityMessage, "Something went wrong. Please try again.", true);
    }
    await loadAvailability();
    // *** NEW ***
    await loadSchedule();
  } catch (error) {
    setMessage(availabilityMessage, "Could not reach the server. Is the backend running?", true);
  }
}

function renderAvailability(blocks) {
  const tableBody = document.getElementById("availability-rows");
  const table = document.getElementById("availability-table");
  const emptyText = document.getElementById("availability-empty");
  tableBody.replaceChildren();

  if (blocks.length === 0) {
    table.hidden = true;
    emptyText.hidden = false;
    return;
  }

  table.hidden = false;
  emptyText.hidden = true;

  for (const block of blocks) {
    const row = document.createElement("tr");
    const cells = [
      DAY_NAMES[block.day_of_week],
      formatTime(block.start_time),
      formatTime(block.end_time),
    ];
    for (const text of cells) {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.appendChild(cell);
    }

    const actionCell = document.createElement("td");
    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = "Remove";
    removeButton.addEventListener("click", function () {
      removeAvailabilityBlock(block.id);
    });
    actionCell.appendChild(removeButton);
    row.appendChild(actionCell);

    tableBody.appendChild(row);
  }
}

async function loadAvailability() {
  try {
    const response = await authFetch("/availability");
    if (!response.ok) {
      return;
    }
    renderAvailability(await response.json());
  } catch (error) {
    // Leave the list as it is; the user can refresh
  }
}

// *** NEW ***
function renderSchedule(data) {
  const header = document.getElementById("schedule-header");
  const body = document.getElementById("schedule-body");
  const gridWrap = document.getElementById("schedule-scroll");
  const summary = document.getElementById("schedule-summary");
  const unscheduledSection = document.getElementById("schedule-unscheduled-section");
  const unscheduledList = document.getElementById("schedule-unscheduled");

  header.replaceChildren();
  body.replaceChildren();
  unscheduledList.replaceChildren();

  if (data.sessions.length === 0 && data.unscheduled.length === 0) {
    gridWrap.hidden = true;
    unscheduledSection.hidden = true;
    summary.textContent = "Nothing to schedule yet. Add assignments and availability times below.";
    return;
  }

  gridWrap.hidden = false;

  // One column per day of the 7-day plan
  for (let offset = 0; offset < 7; offset++) {
    const dayKey = addDaysIso(data.start_date, offset);

    const headerCell = document.createElement("th");
    headerCell.textContent = formatDayLabel(dayKey);
    header.appendChild(headerCell);

    const bodyCell = document.createElement("td");
    const daySessions = data.sessions.filter(function (session) {
      return session.day === dayKey;
    });

    if (daySessions.length === 0) {
      bodyCell.textContent = "-";
    }

    for (const session of daySessions) {
      const sessionBox = document.createElement("div");
      sessionBox.className = "session";
      let text =
        formatTime(session.start_time) +
        " to " +
        formatTime(session.end_time) +
        ": " +
        session.title +
        " (" +
        session.course_name +
        ")";
      if (session.is_overdue) {
        text += " - overdue";
        sessionBox.classList.add("overdue");
      }
      sessionBox.textContent = text;
      bodyCell.appendChild(sessionBox);
    }

    body.appendChild(bodyCell);
  }

  let summaryText =
    "Scheduled " + data.scheduled_hours + " hours between " + data.start_date + " and " + data.end_date + ".";
  if (data.unscheduled.length === 0) {
    summaryText += " Everything fits in your available time.";
  }
  summary.textContent = summaryText;

  // Work that did not fit
  unscheduledSection.hidden = data.unscheduled.length === 0;
  for (const item of data.unscheduled) {
    const listItem = document.createElement("li");
    let text =
      item.title + " (" + item.course_name + "), due " + item.due_date + ": " + item.hours_short + " h short";
    if (item.is_overdue) {
      text += " - overdue";
      listItem.classList.add("overdue");
    }
    listItem.textContent = text;
    unscheduledList.appendChild(listItem);
  }
}

// *** NEW ***
async function loadSchedule() {
  const startInput = document.getElementById("schedule-start");
  if (startInput.value === "") {
    // The server may be a day ahead of the user, so default to the browser's own "today"
    startInput.value = toIsoDate(new Date());
  }

  try {
    const response = await authFetch("/schedule?start=" + encodeURIComponent(startInput.value));
    const data = await response.json();

    if (response.status === 200) {
      setMessage(scheduleMessage, "", false);
      renderSchedule(data);
    } else if (response.status === 422) {
      setMessage(scheduleMessage, "Please choose a valid start date.", true);
    } else if (response.status !== 401) {
      setMessage(scheduleMessage, "Could not load the schedule. Please try again.", true);
    }
  } catch (error) {
    setMessage(scheduleMessage, "Could not reach the server. Is the backend running?", true);
  }
}

async function showLoggedInView(email) {
  document.getElementById("user-email").textContent = email;
  document.getElementById("logged-out-view").hidden = true;
  document.getElementById("logged-in-view").hidden = false;
  // Courses first, so the assignment list can show course names
  await loadCourses();
  await loadAssignments();
  await loadAvailability();
  // *** NEW ***
  await loadSchedule();
}

function showLoggedOutView() {
  document.getElementById("logged-in-view").hidden = true;
  document.getElementById("logged-out-view").hidden = false;
  // Don't leave one user's data on the page after logging out
  document.getElementById("assignment-rows").replaceChildren();
  document.getElementById("assignment-course").replaceChildren();
  document.getElementById("availability-rows").replaceChildren();
  // *** NEW ***
  document.getElementById("schedule-header").replaceChildren();
  document.getElementById("schedule-body").replaceChildren();
  document.getElementById("schedule-unscheduled").replaceChildren();
  document.getElementById("schedule-summary").textContent = "";
  document.getElementById("schedule-message").textContent = "";
  document.getElementById("schedule-start").value = "";
  coursesById = {};
}

async function loadCurrentUser() {
  // Asks the backend who the saved token belongs to; falls back to the logged-out view
  const token = getToken();
  if (!token) {
    showLoggedOutView();
    return;
  }
  try {
    const response = await fetch(API_URL + "/auth/me", {
      headers: { Authorization: "Bearer " + token },
    });
    if (response.ok) {
      const user = await response.json();
      await showLoggedInView(user.email);
    } else {
      // Token is invalid or expired
      clearToken();
      showLoggedOutView();
    }
  } catch (error) {
    showLoggedOutView();
  }
}

// ----- API connection check (from MDT-41) -----
const checkButton = document.getElementById("check-api");
const statusText = document.getElementById("api-status");

checkButton.addEventListener("click", async function () {
  statusText.textContent = "Checking...";
  try {
    const response = await fetch(API_URL + "/health");
    const data = await response.json();
    statusText.textContent = "Backend says: " + data.status;
  } catch (error) {
    statusText.textContent = "Could not reach the backend.";
  }
});

// ----- Registration form (MDT-7) -----
const registerForm = document.getElementById("register-form");
const registerMessage = document.getElementById("register-message");

function describeValidationErrors(detailList) {
  // FastAPI sends a list of problems for 422 responses; turn them into plain sentences
  const messages = [];
  for (const item of detailList) {
    const field = item.loc[item.loc.length - 1];
    if (field === "email") {
      messages.push("Please enter a valid email address.");
    } else if (field === "password") {
      messages.push("Password must be between 8 and 72 characters.");
    } else {
      messages.push(item.msg);
    }
  }
  return messages.join(" ");
}

registerForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  if (email === "" || password === "") {
    setMessage(registerMessage, "Please fill in your email and password.", true);
    return;
  }
  if (password !== confirmPassword) {
    setMessage(registerMessage, "Passwords do not match.", true);
    return;
  }

  setMessage(registerMessage, "Creating your account...", false);

  try {
    const response = await fetch(API_URL + "/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    });
    const data = await response.json();

    if (response.status === 201) {
      setMessage(registerMessage, "Account created for " + data.email + ". You can log in now.", false);
      registerForm.reset();
    } else if (response.status === 409) {
      setMessage(registerMessage, data.detail, true);
    } else if (response.status === 422) {
      setMessage(registerMessage, describeValidationErrors(data.detail), true);
    } else {
      setMessage(registerMessage, "Something went wrong. Please try again.", true);
    }
  } catch (error) {
    setMessage(registerMessage, "Could not reach the server. Is the backend running?", true);
  }
});

// ----- Login form (MDT-11) -----
const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");

loginForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  if (email === "" || password === "") {
    setMessage(loginMessage, "Please enter your email and password.", true);
    return;
  }

  setMessage(loginMessage, "Logging in...", false);

  try {
    const response = await fetch(API_URL + "/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    });
    const data = await response.json();

    if (response.status === 200) {
      saveToken(data.access_token);
      loginForm.reset();
      setMessage(loginMessage, "", false);
      await loadCurrentUser();
    } else if (response.status === 401) {
      setMessage(loginMessage, data.detail, true);
    } else if (response.status === 422) {
      setMessage(loginMessage, "Please enter a valid email and password.", true);
    } else {
      setMessage(loginMessage, "Something went wrong. Please try again.", true);
    }
  } catch (error) {
    setMessage(loginMessage, "Could not reach the server. Is the backend running?", true);
  }
});

// ----- Log out -----
document.getElementById("logout-button").addEventListener("click", function () {
  clearToken();
  showLoggedOutView();
});

// ----- Add course form (MDT-23) -----
const courseForm = document.getElementById("course-form");
const courseMessage = document.getElementById("course-message");

courseForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const name = document.getElementById("course-name").value.trim();
  if (name === "") {
    setMessage(courseMessage, "Please enter a course name.", true);
    return;
  }

  try {
    const response = await authFetch("/courses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name }),
    });
    const data = await response.json();

    if (response.status === 201) {
      setMessage(courseMessage, "Added course: " + data.name, false);
      courseForm.reset();
      await loadCourses();
    } else if (response.status === 409) {
      setMessage(courseMessage, data.detail, true);
    } else if (response.status === 422) {
      setMessage(courseMessage, "Course name must be 1 to 100 characters.", true);
    } else if (response.status !== 401) {
      setMessage(courseMessage, "Something went wrong. Please try again.", true);
    }
  } catch (error) {
    setMessage(courseMessage, "Could not reach the server. Is the backend running?", true);
  }
});

// ----- Add assignment form (MDT-23) -----
const assignmentForm = document.getElementById("assignment-form");
const assignmentMessage = document.getElementById("assignment-message");

assignmentForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const courseId = document.getElementById("assignment-course").value;
  const title = document.getElementById("assignment-title").value.trim();
  const dueDate = document.getElementById("assignment-due").value;
  const hours = parseFloat(document.getElementById("assignment-hours").value);

  // Checks that can be done in the browser, before calling the API
  if (courseId === "") {
    setMessage(assignmentMessage, "Please add and select a course first.", true);
    return;
  }
  if (title === "") {
    setMessage(assignmentMessage, "Please enter a title.", true);
    return;
  }
  if (dueDate === "") {
    setMessage(assignmentMessage, "Please choose a due date.", true);
    return;
  }
  if (Number.isNaN(hours) || hours <= 0 || hours > 100) {
    setMessage(assignmentMessage, "Estimated hours must be more than 0 and at most 100.", true);
    return;
  }

  try {
    const response = await authFetch("/assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_id: Number(courseId),
        title: title,
        due_date: dueDate,
        estimated_hours: hours,
      }),
    });
    const data = await response.json();

    if (response.status === 201) {
      setMessage(assignmentMessage, "Added assignment: " + data.title, false);
      document.getElementById("assignment-title").value = "";
      document.getElementById("assignment-due").value = "";
      document.getElementById("assignment-hours").value = "";
      await loadAssignments();
      // *** NEW ***
      await loadSchedule();
    } else if (response.status === 404) {
      setMessage(assignmentMessage, data.detail, true);
    } else if (response.status === 422) {
      setMessage(assignmentMessage, "Please check the title, due date, and hours.", true);
    } else if (response.status !== 401) {
      setMessage(assignmentMessage, "Something went wrong. Please try again.", true);
    }
  } catch (error) {
    setMessage(assignmentMessage, "Could not reach the server. Is the backend running?", true);
  }
});

// ----- Add availability form (MDT-29, overlap message from MDT-30) -----
const availabilityForm = document.getElementById("availability-form");

availabilityForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const day = document.getElementById("availability-day").value;
  const startTime = document.getElementById("availability-start").value;
  const endTime = document.getElementById("availability-end").value;

  // Checks that can be done in the browser, before calling the API
  if (startTime === "" || endTime === "") {
    setMessage(availabilityMessage, "Please choose a start time and an end time.", true);
    return;
  }
  if (endTime <= startTime) {
    setMessage(availabilityMessage, "End time must be after start time.", true);
    return;
  }

  try {
    const response = await authFetch("/availability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        day_of_week: Number(day),
        start_time: startTime,
        end_time: endTime,
      }),
    });
    const data = await response.json();

    if (response.status === 201) {
      setMessage(
        availabilityMessage,
        "Added " + DAY_NAMES[data.day_of_week] + " " + formatTime(data.start_time) + " to " + formatTime(data.end_time) + ".",
        false
      );
      document.getElementById("availability-start").value = "";
      document.getElementById("availability-end").value = "";
      await loadAvailability();
      // *** NEW ***
      await loadSchedule();
    } else if (response.status === 409) {
      setMessage(availabilityMessage, data.detail, true);
    } else if (response.status === 422) {
      setMessage(availabilityMessage, "Please check the day and times. The end time must be after the start time.", true);
    } else if (response.status !== 401) {
      setMessage(availabilityMessage, "Something went wrong. Please try again.", true);
    }
  } catch (error) {
    setMessage(availabilityMessage, "Could not reach the server. Is the backend running?", true);
  }
});

// *** NEW ***
// ----- Schedule form (MDT-35) -----
const scheduleForm = document.getElementById("schedule-form");

// *** NEW ***
scheduleForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  if (document.getElementById("schedule-start").value === "") {
    setMessage(scheduleMessage, "Please choose a start date.", true);
    return;
  }
  await loadSchedule();
});

// On page load, check whether a saved token is still valid
loadCurrentUser();