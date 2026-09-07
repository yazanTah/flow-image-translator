// DOM Elements
const dropzone = document.getElementById("dropzone");
const dropzoneEmpty = document.getElementById("dropzoneEmpty");
const dropzonePreview = document.getElementById("dropzonePreview");
const fileInput = document.getElementById("fileInput");
const sourcePreviewImg = document.getElementById("sourcePreviewImg");
const removeFileBtn = document.getElementById("removeFileBtn");
const fileNameSpan = document.getElementById("fileName");
const fileSizeSpan = document.getElementById("fileSize");

const targetLangSelect = document.getElementById("targetLang");
const customLangGroup = document.getElementById("customLangGroup");
const customLangInput = document.getElementById("customLang");
const preserveStyleCheckbox = document.getElementById("preserveStyle");
const customPromptInput = document.getElementById("customPrompt");
const translateBtn = document.getElementById("translateBtn");

const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const setupModal = document.getElementById("setupModal");

const progressTracker = document.getElementById("progressTracker");
const progressBarFill = document.getElementById("progressBarFill");
const progressPercent = document.getElementById("progressPercent");
const progressLogs = document.getElementById("progressLogs");

const viewerEmpty = document.getElementById("viewerEmpty");
const splitViewer = document.getElementById("splitViewer");
const sideBySideViewer = document.getElementById("sideBySideViewer");
const splitOriginalImg = document.getElementById("splitOriginalImg");
const splitResultImg = document.getElementById("splitResultImg");
const sideOriginalImg = document.getElementById("sideOriginalImg");
const sideResultImg = document.getElementById("sideResultImg");
const splitModifiedWrapper = document.getElementById("splitModifiedWrapper");
const sliderHandle = document.getElementById("sliderHandle");

const viewerActions = document.getElementById("viewerActions");
const downloadBtn = document.getElementById("downloadBtn");
const resetBtn = document.getElementById("resetBtn");
const resultMeta = document.getElementById("resultMeta");

const modeCompareBtn = document.getElementById("modeCompare");
const modeSideBtn = document.getElementById("modeSide");
const modeResultBtn = document.getElementById("modeResult");

let currentFile = null;
let currentOutputUrl = null;
let isDraggingSlider = false;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  checkStatus();
  setInterval(checkStatus, 5000);
  setupDropzone();
  setupSlider();
  setupModes();
});

// Check Chrome connection
async function checkStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.connected) {
      statusBadge.className = "status-badge online";
      statusText.textContent = data.flow_open ? "Chrome & Flow Connected" : "Chrome 9222 Ready";
    } else {
      statusBadge.className = "status-badge offline";
      statusText.textContent = "Chrome 9222 Offline";
    }
  } catch (err) {
    statusBadge.className = "status-badge offline";
    statusText.textContent = "Backend Offline";
  }
}

// Dropzone & File Handling
function setupDropzone() {
  ["dragenter", "dragover"].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach(event => {
    dropzone.addEventListener(event, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
  });

  removeFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearFile();
  });

  targetLangSelect.addEventListener("change", () => {
    if (targetLangSelect.value === "custom") {
      customLangGroup.classList.remove("hidden");
    } else {
      customLangGroup.classList.add("hidden");
    }
  });

  translateBtn.addEventListener("click", startTranslation);
  resetBtn.addEventListener("click", () => {
    clearFile();
    viewerEmpty.classList.remove("hidden");
    splitViewer.classList.add("hidden");
    sideBySideViewer.classList.add("hidden");
    viewerActions.classList.add("hidden");
  });
}

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please select an image file (PNG, JPG, or WEBP).");
    return;
  }

  currentFile = file;
  fileNameSpan.textContent = file.name;
  fileSizeSpan.textContent = (file.size / (1024 * 1024)).toFixed(2) + " MB";

  const reader = new FileReader();
  reader.onload = (e) => {
    sourcePreviewImg.src = e.target.result;
    dropzoneEmpty.classList.add("hidden");
    dropzonePreview.classList.remove("hidden");
    translateBtn.disabled = false;
  };
  reader.readAsDataURL(file);
}

function clearFile() {
  currentFile = null;
  fileInput.value = "";
  sourcePreviewImg.src = "";
  dropzoneEmpty.classList.remove("hidden");
  dropzonePreview.classList.add("hidden");
  translateBtn.disabled = true;
}

// Translation Execution
async function startTranslation() {
  if (!currentFile) return;

  const targetLang = targetLangSelect.value === "custom" 
    ? (customLangInput.value.trim() || "English") 
    : targetLangSelect.value;

  const instructions = customPromptInput.value.trim();
  const preserveStyle = preserveStyleCheckbox.checked;

  // UI state: translating
  translateBtn.disabled = true;
  translateBtn.querySelector(".btn-text").textContent = "Translating...";
  translateBtn.querySelector(".btn-spinner").classList.remove("hidden");
  progressTracker.classList.remove("hidden");
  progressLogs.innerHTML = "";

  addLog("1. Connecting to Chrome session on port 9222...");
  updateProgress(20, "Connecting...");

  const formData = new FormData();
  formData.append("file", currentFile);
  formData.append("target_language", targetLang);
  formData.append("custom_instructions", instructions);
  formData.append("preserve_style", preserveStyle);

  // Animate progress phases
  setTimeout(() => {
    addLog("2. Uploading image to Google Flow canvas...");
    updateProgress(45, "Uploading...");
  }, 1500);

  setTimeout(() => {
    addLog("3. Generating text translation with Nano Banana Pro...");
    updateProgress(70, "Generating...");
  }, 4000);

  try {
    const res = await fetch("/api/translate", {
      method: "POST",
      body: formData
    });

    const result = await res.json();

    if (!res.ok || !result.success) {
      throw new Error(result.error || "Translation failed. Check Chrome connection.");
    }

    addLog("4. Translation finished! Rendering comparison.");
    updateProgress(100, "Complete!");

    currentOutputUrl = result.output_url;
    renderResult(result.input_url, result.output_url, targetLang);

  } catch (err) {
    addLog(`Error: ${err.message}`);
    updateProgress(100, "Failed");
    alert(`Translation Error: ${err.message}\n\nPlease verify Chrome is open with remote debugging on port 9222.`);
  } finally {
    translateBtn.disabled = false;
    translateBtn.querySelector(".btn-text").textContent = "✨ Translate Image with Flow";
    translateBtn.querySelector(".btn-spinner").classList.add("hidden");
  }
}

function updateProgress(percent, label) {
  progressBarFill.style.width = `${percent}%`;
  progressPercent.textContent = label;
}

function addLog(text) {
  const div = document.createElement("div");
  div.className = "log-entry";
  div.textContent = text;
  progressLogs.appendChild(div);
  progressLogs.scrollTop = progressLogs.scrollHeight;
}

// Result Rendering & Comparison Slider
function renderResult(inputUrl, outputUrl, lang) {
  viewerEmpty.classList.add("hidden");
  splitViewer.classList.remove("hidden");
  viewerActions.classList.remove("hidden");

  splitOriginalImg.src = inputUrl;
  splitResultImg.src = outputUrl;
  sideOriginalImg.src = inputUrl;
  sideResultImg.src = outputUrl;

  resultMeta.textContent = `Translated into ${lang} · Nano Banana Pro`;

  downloadBtn.onclick = () => {
    const a = document.createElement("a");
    a.href = outputUrl;
    a.download = `translated_${lang.toLowerCase()}_${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };
}

function setupSlider() {
  const container = splitViewer;

  const onMove = (clientX) => {
    if (!isDraggingSlider) return;
    const rect = container.getBoundingClientRect();
    let x = clientX - rect.left;
    if (x < 0) x = 0;
    if (x > rect.width) x = rect.width;
    const percent = (x / rect.width) * 100;

    splitModifiedWrapper.style.width = `${percent}%`;
    sliderHandle.style.left = `${percent}%`;
  };

  sliderHandle.addEventListener("mousedown", () => { isDraggingSlider = true; });
  window.addEventListener("mouseup", () => { isDraggingSlider = false; });
  window.addEventListener("mousemove", (e) => onMove(e.clientX));

  sliderHandle.addEventListener("touchstart", () => { isDraggingSlider = true; });
  window.addEventListener("touchend", () => { isDraggingSlider = false; });
  window.addEventListener("touchmove", (e) => {
    if (e.touches.length > 0) onMove(e.touches[0].clientX);
  });
}

function setupModes() {
  modeCompareBtn.addEventListener("click", () => {
    setMode("compare");
  });
  modeSideBtn.addEventListener("click", () => {
    setMode("side");
  });
  modeResultBtn.addEventListener("click", () => {
    setMode("result");
  });
}

function setMode(mode) {
  [modeCompareBtn, modeSideBtn, modeResultBtn].forEach(b => b.classList.remove("active"));

  if (mode === "compare") {
    modeCompareBtn.classList.add("active");
    splitViewer.classList.remove("hidden");
    sideBySideViewer.classList.add("hidden");
    splitModifiedWrapper.style.width = "50%";
    sliderHandle.style.left = "50%";
    sliderHandle.classList.remove("hidden");
  } else if (mode === "side") {
    modeSideBtn.classList.add("active");
    splitViewer.classList.add("hidden");
    sideBySideViewer.classList.remove("hidden");
  } else if (mode === "result") {
    modeResultBtn.classList.add("active");
    splitViewer.classList.remove("hidden");
    sideBySideViewer.classList.add("hidden");
    splitModifiedWrapper.style.width = "100%";
    sliderHandle.classList.add("hidden");
  }
}

// Setup Modal
function openSetupModal() {
  setupModal.classList.remove("hidden");
}

function closeSetupModal() {
  setupModal.classList.add("hidden");
}

function copyLaunchCommand() {
  const cmd = `& "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe" --remote-debugging-port=9222 --user-data-dir="C:\\brave-flow-profile"`;
  navigator.clipboard.writeText(cmd);
  alert("Command copied to clipboard! Paste it into PowerShell.");
}

async function launchChrome() {
  const btn = document.getElementById("launchChromeBtn");
  btn.textContent = "Launching...";
  try {
    const res = await fetch("/api/launch-browser", { method: "POST" });
    const data = await res.json();
    alert(data.message || "Browser launched! Check your taskbar.");
    setTimeout(checkStatus, 2000);
  } catch (e) {
    alert("Could not automatically launch browser. Please run the PowerShell command manually.");
  } finally {
    btn.textContent = "🚀 1-Click Launch Brave";
  }
}

