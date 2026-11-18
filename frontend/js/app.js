// Address of the backend API as seen from the browser
const API_URL = "http://localhost:8080";

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

// *** NEW ***
// ----- Registration form (MDT-7) -----
const registerForm = document.getElementById("register-form");
const registerMessage = document.getElementById("register-message");

// *** NEW ***
function showMessage(text, isError) {
  // textContent (not innerHTML) so server text can never inject HTML
  registerMessage.textContent = text;
  registerMessage.style.color = isError ? "crimson" : "green";
}

// *** NEW ***
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

// *** NEW ***
registerForm.addEventListener("submit", async function (event) {
  event.preventDefault();

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirm-password").value;

  // Checks that can be done in the browser, before calling the API
  if (email === "" || password === "") {
    showMessage("Please fill in your email and password.", true);
    return;
  }
  if (password !== confirmPassword) {
    showMessage("Passwords do not match.", true);
    return;
  }

  showMessage("Creating your account...", false);

  try {
    const response = await fetch(API_URL + "/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email, password: password }),
    });
    const data = await response.json();

    if (response.status === 201) {
      showMessage("Account created for " + data.email + ". You can log in once login is built.", false);
      registerForm.reset();
    } else if (response.status === 409) {
      showMessage(data.detail, true);
    } else if (response.status === 422) {
      showMessage(describeValidationErrors(data.detail), true);
    } else {
      showMessage("Something went wrong. Please try again.", true);
    }
  } catch (error) {
    showMessage("Could not reach the server. Is the backend running?", true);
  }
});