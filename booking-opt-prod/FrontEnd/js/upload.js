// Base URL for API calls; set in index.html via window.API_BASE_URL
const API_BASE_URL = window.API_BASE_URL || "";

// Maximum allowed file size (in bytes) for client‑side check
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
// Polling interval for checking if PNG is ready (ms)
const POLL_INTERVAL = 2000;
// Maximum number of polls before giving up
const MAX_POLLS = 30;
// Maximum number of files allowed in a single upload
const MAX_FILES = 10;

/** Toggle visibility of the upload spinner. */
function setLoading(on) {
  document.getElementById("uploadSpinner")
          .classList.toggle("hidden", !on);
}

/**
 * Render a text message into an element.
 * @param {string} id – element ID
 * @param {string} msg – text to display
 * @param {boolean} isError – if true, apply error styling
 */
function renderMessage(id, msg, isError = false) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.color = isError ? "crimson" : "inherit";
}

/**
 * Append an anchor link to the given container element.
 * @param {HTMLElement} containerElement – The HTML element to append the link to.
 * @param {string} href – URL to link to
 * @param {string} text – link text
 */
function appendLink(containerElement, href, text) {
  const a = document.createElement("a");
  a.href = href;
  a.target = "_blank";
  a.textContent = text;
  a.style.display = "block"; // Make each link appear on a new line
  a.style.marginTop = "5px"; // Add some space between links
  containerElement.appendChild(a);
}

/**
 * Polls /api/result with the given fileName until ready or timeout.
 * @param {string} fileName – the JSON filename token returned from /api/upload
 * @returns {Promise<object>} resolves to { ready, jsonUrl, imageUrl } from /api/result
 */
async function pollForImage(fileName) {
  for (let i = 0; i < MAX_POLLS; i++) {
    const resp = await fetch(
      `${API_BASE_URL}/api/result?fileName=${encodeURIComponent(fileName)}`
    );
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || `Result check failed (${resp.status})`);
    }
    const data = await resp.json();
    if (data.ready) {
      return data;  // { ready: true, jsonUrl, imageUrl, expiresInMinutes, problemId }
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
  throw new Error("Timed out waiting for plotted image");
}

/**
 * Processes a single file: uploads, then polls for results.
 * @param {File} file - The file object to process.
 * @param {FormData} formData - The FormData object containing the file.
 * @param {string} statusDivId - The ID of the div element used to display status for this file.
 */
async function processSingleFile(file, formData, statusDivId) {
  const statusDiv = document.getElementById(statusDivId);

  try {
    setLoading(true); // Global spinner for any activity
    statusDiv.textContent = `Uploading ${file.name}...`;
    statusDiv.style.color = "inherit";

    const resp = await fetch(`${API_BASE_URL}/api/upload`, {
      method: "POST",
      body: formData
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed for ${file.name} (${resp.status})`);
    }
    
    const { fileName, problemId } = await resp.json();
    statusDiv.textContent = `ProblemID ${problemId} (${file.name}) submitted. Processing... ⏳`;

    const { jsonUrl, imageUrl } = await pollForImage(fileName);
    
    statusDiv.innerHTML = ""; // Clear processing message
    const successMsg = document.createElement("span");
    successMsg.textContent = `🎉 File ready: ${file.name}`;
    statusDiv.appendChild(successMsg);
    
    appendLink(statusDiv, jsonUrl, `View Optimized JSON for ${file.name}`);
    appendLink(statusDiv, imageUrl, `View Plot (PNG) for ${file.name}`);

  } catch (err) {
    statusDiv.textContent = `Error for ${file.name}: ${err.message}`;
    statusDiv.style.color = "crimson";
    console.error(`Error processing ${file.name}:`, err);
  } finally {
    // Consider a counter if you want to turn off spinner only when ALL files are done
    // For now, any single file completion (success or error) might turn it off if not careful.
    // A simple approach is to leave setLoading(true) at start of handleUpload and setLoading(false) at its very end.
    // However, processSingleFile is async. The current setLoading(true) is in processSingleFile.
    // This means the spinner will turn on for each file and off when that file is done.
    // If multiple files are processing, it might flicker.
    // For now, let's use a global counter for active uploads.
    activeUploads--;
    if (activeUploads === 0) {
      setLoading(false);
    }
  }
}

let activeUploads = 0; // Counter for active file processing operations

/**
 * Main upload handler (wired to #uploadForm submit).
 */
async function handleUpload(e) {
  e.preventDefault();
  renderMessage("uploadError", ""); // Clear global error message
  const uploadResultContainer = document.getElementById("uploadResult");
  uploadResultContainer.innerHTML = ""; // Clear previous results container

  const input = document.getElementById("jsonFile");
  const files = input.files;

  if (!files.length) {
    return renderMessage("uploadError", "Please select one or more files.", true);
  }

  if (files.length > MAX_FILES) {
    return renderMessage("uploadError", `You can only upload a maximum of ${MAX_FILES} files at a time.`, true);
  }
  
  activeUploads = 0; // Reset counter

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    const statusDivId = `status-${file.name.replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}`; // Make ID more robust

    const fileStatusDiv = document.createElement("div");
    fileStatusDiv.id = statusDivId;
    fileStatusDiv.className = "file-status-entry"; // For potential styling
    fileStatusDiv.textContent = `Validating ${file.name}...`;
    uploadResultContainer.appendChild(fileStatusDiv);

    // Client-side validation for each file
    if (file.type !== "application/json" && !file.name.toLowerCase().endsWith(".json")) {
      fileStatusDiv.textContent = `Unsupported file type for ${file.name}. Please choose .json files.`;
      fileStatusDiv.style.color = "crimson";
      continue; // Next file
    }
    if (file.size > MAX_FILE_SIZE) {
      fileStatusDiv.textContent = `File ${file.name} too large. Maximum is ${(MAX_FILE_SIZE/1024/1024).toFixed(1)} MB.`;
      fileStatusDiv.style.color = "crimson";
      continue; // Next file
    }

    const formData = new FormData();
    formData.append("file", file);
    
    activeUploads++;
    if (activeUploads === 1) { // Turn on spinner only for the first active upload
        setLoading(true);
    }
    // Asynchronously process each file
    processSingleFile(file, formData, statusDivId); 
  }
  
  // Reset file input to allow re-uploading the same files if needed
  input.value = ""; 
}

// Wire up form listener once the DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("uploadForm")
          .addEventListener("submit", handleUpload);
  
  // Also handle echo form if it exists
  const echoForm = document.getElementById("echoForm");
  if (echoForm) {
    echoForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      renderMessage("echoError", "");
      document.getElementById("echoResult").textContent = "";
      const input = document.getElementById("echoInput").value;
      try {
        const resp = await fetch(`${API_BASE_URL}/api/echo`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: input,
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || `Echo failed (${resp.status})`);
        }
        const data = await resp.json();
        document.getElementById("echoResult").textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        renderMessage("echoError", err.message, true);
      }
    });
  }
});