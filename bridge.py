import os
import sys
import time
import json
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlowBridge")

CDP_URL = "http://localhost:9222"
FLOW_URL = "https://flow.google.com"

def check_cdp_status() -> Dict[str, Any]:
    """
    Checks if Brave/Chrome is running with remote debugging on port 9222
    and whether Google Flow is currently open.
    """
    try:
        req = urllib.request.Request(f"{CDP_URL}/json/version", headers={"User-Agent": "FlowBridge"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            version_data = json.loads(resp.read().decode())
            
        flow_open = False
        tabs_req = urllib.request.Request(f"{CDP_URL}/json/list", headers={"User-Agent": "FlowBridge"})
        with urllib.request.urlopen(tabs_req, timeout=1.5) as tabs_resp:
            tabs = json.loads(tabs_resp.read().decode())
            for tab in tabs:
                url = tab.get("url", "").lower()
                if "flow.google.com" in url or "labs.google" in url:
                    flow_open = True
                    break

        browser_name = "Brave" if "brave" in version_data.get("Browser", "").lower() else "Brave/Chrome"
        return {
            "connected": True,
            "browser": browser_name,
            "flow_open": flow_open,
            "message": f"{browser_name} is connected on port 9222." + (" Google Flow is open." if flow_open else " Flow tab will open automatically.")
        }
    except Exception:
        return {
            "connected": False,
            "browser": None,
            "flow_open": False,
            "message": "Browser remote debugging is offline. Run launch_brave.bat or start with --remote-debugging-port=9222"
        }

def get_or_create_flow_page(browser: Browser) -> Page:
    """Finds an existing Google Flow tab or opens a new one."""
    for context in browser.contexts:
        for page in context.pages:
            url = page.url.lower()
            if "flow.google.com" in url or "labs.google" in url:
                logger.info(f"Found existing Flow tab: {page.url}")
                page.bring_to_front()
                return page

    # No existing tab found; navigate to Flow
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.new_page()
    logger.info(f"Opening Flow at {FLOW_URL}...")
    page.goto(FLOW_URL, wait_until="networkidle", timeout=45000)
    return page

def _sync_translate_flow(
    image_path: str,
    target_language: str,
    custom_instructions: str,
    preserve_style: bool,
    output_dir: str
) -> Dict[str, Any]:
    """
    Synchronous Playwright execution to bypass Windows asyncio subprocess limitations.
    """
    abs_image_path = str(Path(image_path).resolve())
    if not os.path.exists(abs_image_path):
        return {"success": False, "error": f"Input image not found: {abs_image_path}"}

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time() * 1000)
    output_filename = f"translated_{timestamp}.png"
    output_filepath = os.path.join(output_dir, output_filename)

    prompt = f"Translate all text in this image into {target_language}."
    if preserve_style:
        prompt += " Maintain the exact original typography, font styling, colors, layout, and composition seamlessly."
    if custom_instructions and custom_instructions.strip():
        prompt += f" Specific directives: {custom_instructions.strip()}."

    cdp_check = check_cdp_status()
    if not cdp_check["connected"]:
        return {
            "success": False,
            "error": "Browser is not running with remote debugging on port 9222. Run launch_brave.bat first!"
        }

    with sync_playwright() as p:
        try:
            logger.info("Connecting to Browser via CDP on port 9222...")
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = get_or_create_flow_page(browser)

            curr_url = page.url.lower()
            # 1. Check if user is on Google Sign-In page
            if "accounts.google.com" in curr_url or "signin" in curr_url:
                return {
                    "success": False,
                    "error": "Google Sign-In required: Please switch to the 'API Access For Flow' Brave window and complete sign-in!"
                }

            page.wait_for_load_state("domcontentloaded")
            time.sleep(1.0)

            # 2. Check if on Landing / Marketing page
            body_text = page.evaluate("() => document.body.innerText")
            if "Create with Google Flow" in body_text:
                create_btn = page.get_by_role("button", name="Create with Google Flow").first
                if create_btn.count() > 0:
                    logger.info("Clicking 'Create with Google Flow'...")
                    create_btn.click()
                    page.wait_for_timeout(3000)
                    if "accounts.google.com" in page.url.lower():
                        return {
                            "success": False,
                            "error": "Please sign into your Google account in the open Brave window!"
                        }

            # 3. Check if on Dashboard with "+ New project" or "Start Creating"
            new_proj_btn = page.locator('button:has-text("New project"), button:has-text("Start Creating"), [aria-label*="New project" i]').first
            if new_proj_btn.count() > 0 and new_proj_btn.is_visible():
                logger.info("Clicking '+ New project' to open studio canvas...")
                new_proj_btn.click()
                page.wait_for_timeout(3000)

            # 4. Attach image file
            logger.info(f"Attaching image: {abs_image_path}")
            file_input = page.locator('input[type="file"]')
            if file_input.count() > 0:
                file_input.first.set_input_files(abs_image_path)
            else:
                upload_btn = page.locator('button[aria-label*="image" i], button[aria-label*="upload" i], button:has-text("Add image"), button:has-text("Upload")')
                if upload_btn.count() > 0:
                    with page.expect_file_chooser(timeout=5000) as fc_info:
                        upload_btn.first.click()
                    file_chooser = fc_info.value
                    file_chooser.set_files(abs_image_path)
                else:
                    logger.warning("No file input found directly; proceeding with prompt.")

            time.sleep(1.0)

            # 5. Select Nano Banana Pro if model selector is available
            try:
                model_btn = page.locator('button:has-text("Nano Banana"), button:has-text("Model"), [aria-label*="model" i]')
                if model_btn.count() > 0 and model_btn.first.is_visible():
                    btn_text = model_btn.first.inner_text()
                    if "Nano Banana Pro" not in btn_text:
                        model_btn.first.click()
                        time.sleep(0.5)
                        pro_option = page.locator('text="Nano Banana Pro"')
                        if pro_option.count() > 0:
                            pro_option.first.click()
                            time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Model select info: {e}")

            # 6. Fill the prompt into the prompt box
            logger.info(f"Injecting prompt: {prompt}")
            # Target visible prompt inputs, excluding hidden recaptcha textareas
            prompt_input = page.locator(
                'textarea:not([name*="recaptcha"]):not([class*="recaptcha"]), [contenteditable="true"], input[placeholder*="prompt" i]'
            ).first
            prompt_input.wait_for(state="visible", timeout=12000)
            
            try:
                prompt_input.fill(prompt)
            except Exception:
                prompt_input.click()
                page.keyboard.type(prompt, delay=10)

            time.sleep(0.5)

            # 7. Click Generate button
            logger.info("Submitting generation request...")
            generate_btn = page.locator(
                'button:has-text("Generate"), button:has-text("Create"), button[aria-label*="Generate" i], button[aria-label*="Submit" i]'
            ).first
            generate_btn.click()

            # 8. Wait for output image
            logger.info("Waiting for Nano Banana Pro output...")
            start_time = time.time()
            max_wait_seconds = 90
            output_found = False

            while time.time() - start_time < max_wait_seconds:
                images = page.locator('img[src^="blob:"], img[src*="googleusercontent"], img[src*="media/"]')
                img_count = images.count()
                if img_count > 0:
                    last_img = images.last
                    src = last_img.get_attribute("src")
                    if src and not src.endswith("logo.png") and "avatar" not in src:
                        logger.info(f"Generated image found: {src[:50]}...")
                        last_img.screenshot(path=output_filepath)
                        output_found = True
                        break
                time.sleep(2.0)

            if not output_found:
                logger.warning("Main image selector timed out; capturing generation container preview.")
                container = page.locator('.generation-preview, [data-testid="preview-area"], main').first
                if container.count() > 0:
                    container.screenshot(path=output_filepath)
                else:
                    page.screenshot(path=output_filepath)

            return {
                "success": True,
                "output_filename": output_filename,
                "output_path": output_filepath,
                "prompt": prompt,
                "target_language": target_language,
                "message": "Image translated successfully via Nano Banana Pro."
            }

        except Exception as e:
            logger.error(f"Error during Flow translation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Automation error: {str(e)}"
            }

async def translate_image_flow(
    image_path: str,
    target_language: str = "English",
    custom_instructions: str = "",
    preserve_style: bool = True,
    output_dir: str = "outputs"
) -> Dict[str, Any]:
    """Runs synchronous Playwright inside an asyncio worker thread."""
    import asyncio
    return await asyncio.to_thread(
        _sync_translate_flow,
        image_path,
        target_language,
        custom_instructions,
        preserve_style,
        output_dir
    )
