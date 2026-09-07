import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from bridge import check_cdp_status, translate_image_flow

BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Nano Banana Pro Image Translator",
    description="Automated in-image text translation powered by Google Flow & Nano Banana Pro",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded and generated media
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

@app.get("/api/status")
async def get_status():
    """Returns the live connection status of Chrome DevTools Protocol."""
    status = check_cdp_status()
    return JSONResponse(content=status)

@app.post("/api/launch-chrome")
async def launch_chrome():
    """Convenience endpoint to launch Chrome with remote debugging enabled."""
    status = check_cdp_status()
    if status["connected"]:
        return {"success": True, "message": "Chrome is already connected."}

    # Possible Chrome executable locations on Windows
    chrome_paths = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"))
    ]

    chrome_bin = None
    for p in chrome_paths:
        if p.exists():
            chrome_bin = p
            break

    if not chrome_bin:
        raise HTTPException(
            status_code=404,
            detail="Google Chrome installation not found in standard paths."
        )

    profile_dir = Path("C:/chrome-flow-profile")
    cmd = [
        str(chrome_bin),
        "--remote-debugging-port=9222",
        f"--user-data-dir={profile_dir}",
        "https://labs.google/fx/tools/flow"
    ]

    try:
        subprocess.Popen(cmd, shell=False)
        return {
            "success": True,
            "message": "Chrome launched successfully on port 9222. Sign into Google Flow if prompted."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch Chrome: {str(e)}")

@app.post("/api/translate")
async def translate_image(
    file: UploadFile = File(...),
    target_language: str = Form("English"),
    custom_instructions: str = Form(""),
    preserve_style: bool = Form(True)
):
    """
    Accepts an uploaded image and translates its text into the target language
    using Nano Banana Pro on Google Flow.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    # Save uploaded file
    file_ext = Path(file.filename).suffix or ".png"
    safe_name = f"input_{Path(file.filename).stem[:30]}_{os.urandom(4).hex()}{file_ext}"
    input_path = UPLOADS_DIR / safe_name

    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Trigger translation via bridge
    result = await translate_image_flow(
        image_path=str(input_path),
        target_language=target_language,
        custom_instructions=custom_instructions,
        preserve_style=preserve_style,
        output_dir=str(OUTPUTS_DIR)
    )

    if not result.get("success"):
        return JSONResponse(status_code=500, content=result)

    result["input_url"] = f"/uploads/{safe_name}"
    result["output_url"] = f"/outputs/{result['output_filename']}"
    return JSONResponse(content=result)

@app.get("/api/history")
async def get_history():
    """Returns recently generated translated images."""
    files = sorted(OUTPUTS_DIR.glob("*.png"), key=os.path.getmtime, reverse=True)
    history = []
    for f in files[:20]:
        history.append({
            "filename": f.name,
            "url": f"/outputs/{f.name}",
            "created_at": os.path.getmtime(f)
        })
    return {"history": history}

# Serve web frontend
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting Nano Banana Pro Translator on http://localhost:8000 ...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
