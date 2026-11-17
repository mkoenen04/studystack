// Address of the backend API as seen from the browser
const API_URL = "http://localhost:8080";

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