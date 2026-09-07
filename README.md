# 🍌 Nano Banana Pro — In-Image Translator

> Translate text inside images (manga, posters, UI mockups, packaging, infographics) seamlessly with **Nano Banana Pro** via **Google Flow** — with **$0 extra API fees** and **zero mouse movement**.

---

## 🌟 Why This Exists

1. **Google Flow Subscription Credits:** Google Flow subscriptions include generous daily image allowances powered by **Nano Banana Pro (Gemini 3 Pro Image)**.
2. **No Middleman Subscriptions:** Third-party APIs like `useapi.net` charge \$15/month + per-solve captcha fees.
3. **No Expensive Cloud Bills:** The official Gemini API on Google Cloud charges per-image and ignores your consumer Flow subscription.
4. **Zero Mouse Movement (CDP):** By connecting directly to Chrome via DevTools Protocol (CDP), requests execute at native memory speed in microseconds. Your physical mouse cursor is never touched, and you can keep Chrome minimized.

---

## 🚀 Features

- **Interactive Before/After Split Slider:** Compare the translated result directly over the original image with a draggable slider.
- **Side-by-Side & Result Views:** Multiple viewing modes for reviewing translations.
- **Deep Typography & Style Preservation:** Prompts Nano Banana Pro to match font families, colors, perspective, shadows, and textures.
- **Custom Prompts & Directions:** Add specific directives like reading manga bubbles right-to-left or keeping brand names untranslated.
- **Live Connection Monitor:** Real-time health indicator showing whether your Chrome session is ready.
- **1-Click Windows Launcher:** Fast, zero-hassle startup with `start.bat`.

---

## 🛠️ Quick Start Guide

### 1. Launch Chrome with Remote Debugging (One-time Setup)
Run this command in **PowerShell**:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome-flow-profile"
```

1. In the Chrome window that opens, visit [labs.google/fx/tools/flow](https://labs.google/fx/tools/flow).
2. Sign in with your Google account.
3. Select **Nano Banana Pro** as your default image model.
4. Minimize Chrome — it runs in the background.

---

### 2. Start the Translator Web App

Double-click **`start.bat`** or run in terminal:

```powershell
# Install requirements
pip install -r requirements.txt

# Start the server
python main.py
```

Open your browser to:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser UI                             │
│  - Drag & drop image upload (Manga, Posters, Infographics) │
│  - Target language selector (English, Japanese, etc.)       │
│  - Interactive Before/After Split Comparison Slider         │
│  - Live Chrome session connection status indicator         │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Server                   │
│  - Static frontend serving (index.html, app.js, style.css)  │
│  - /api/translate endpoint                                  │
│  - /api/status endpoint (checks Chrome connection)          │
│  - Image storage & processing pipeline                      │
└──────────────────────────────┬──────────────────────────────┘
                               │ CDP (Memory Speed, No Mouse)
┌──────────────────────────────▼──────────────────────────────┐
│             Local Chrome (port 9222)                        │
│  - Logged into labs.google/fx/tools/flow                    │
│  - Uses your active Google AI Pro subscription              │
│  - Solves reCAPTCHA v3 silently & for free                  │
│  - Nano Banana Pro generates translated image               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📄 License
MIT License. Built for creators and developers who want to maximize their Google Flow subscription.
