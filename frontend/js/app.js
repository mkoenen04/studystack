// Address of the backend API as seen from the browser
const API_URL = "http://localhost:8080";
const TOKEN_KEY = "studystack_token";

// ----- Small helpers -----
function setMessage(element, text, isError) {
  // textContent (not innerHTML) so server text can never inject HTML
  element.textContent = text;
  element.style.color = isError ? "crimson" : "green";
}

// *** NEW ***
function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

// *** NEW ***
function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

// *** NEW ***
function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// *** NEW ***
function showLoggedInView(email) {
  document.getElementById("user-email").textContent = email;
  document.getElementById("logged-out-view").hidden = true;
  document.getElementById("logged-in-view").hidden = false;
}

// *** NEW ***
function showLoggedOutView() {
  document.getElementById("logged-in-view").hidden = true;
  document.getElementById("logged-out-view").hidden = false;
}

// *** NEW ***
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
      showLoggedInView(user.email);
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

// *** NEW ***
// ----- Login form (MDT-11) -----
const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");

// *** NEW ***
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

// *** NEW ***
// ----- Log out -----
document.getElementById("logout-button").addEventListener("click", function () {
  clearToken();
  showLoggedOutView();
});

// *** NEW ***
// On page load, check whether a saved token is still valid
loadCurrentUser();