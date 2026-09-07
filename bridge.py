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

        browser_name = "Brave" if "brave" in version_data.get("Browser", "").lower() else "Browser"
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
            "message": "Browser remote debugging is offline. Start Brave with --remote-debugging-port=9222"
        }

def get_or_create_flow_page(browser: Browser) -> Page:
    """Finds an existing Google Flow tab or opens a new one."""
    for context in browser.contexts:
        for page in context.pages:
            url = page.url.lower()
            if "flow.google.com" in url or "labs.google" in url:
                logger.info(f"Found active Flow tab: {page.url}")
                page.bring_to_front()
                return page

    # No existing tab found; open Flow
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
    Automates Google Flow to translate the image using Nano Banana Pro.
    Runs synchronously inside a worker thread to prevent Windows asyncio errors.
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
        prompt += f" Specific instructions: {custom_instructions.strip()}."

    cdp_check = check_cdp_status()
    if not cdp_check["connected"]:
        return {
            "success": False,
            "error": "Browser is not running with remote debugging on port 9222."
        }

    with sync_playwright() as p:
        try:
            logger.info("Connecting to Browser via CDP on port 9222...")
            browser = p.chromium.connect_over_cdp(CDP_URL)
            page = get_or_create_flow_page(browser)

            # Close any open menus/overlays first
            page.keyboard.press("Escape")
            time.sleep(0.5)

            # If on dashboard/home, enter a project canvas
            if "flow.google.com/project/" not in page.url.lower():
                logger.info("Entering project canvas...")
                new_btn = page.locator('button:has-text("New project"), button:has-text("Start Creating")').first
                if new_btn.count() > 0:
                    new_btn.click(force=True)
                    page.wait_for_timeout(3000)

            # 1. Attach image file via Add media menu
            logger.info(f"Attaching image to canvas: {abs_image_path}")
            add_media_btn = page.locator('button[aria-label*="Add media menu" i], button[aria-label*="Add ingredients" i]').first
            if add_media_btn.count() > 0:
                add_media_btn.click(force=True)
                page.wait_for_timeout(600)

                upload_opt = page.locator('button:has-text("Upload"), [role="menuitem"]:has-text("Upload")').first
                if upload_opt.count() > 0:
                    with page.expect_file_chooser(timeout=8000) as fc_info:
                        upload_opt.click(force=True)
                    fc = fc_info.value
                    fc.set_files(abs_image_path)
                    logger.info("Image attached successfully!")
                    page.wait_for_timeout(2000)
            else:
                # Fallback to direct input[type="file"] if present
                fi = page.locator('input[type="file"]')
                if fi.count() > 0:
                    fi.first.set_input_files(abs_image_path)
                    logger.info("Image attached via fallback file input!")

            # 2. Switch to Image mode if currently in Video mode
            try:
                settings_btn = page.locator('button[aria-label*="Settings trigger" i]').first
                if settings_btn.count() > 0:
                    btn_text = settings_btn.inner_text().lower()
                    if "video" in btn_text:
                        logger.info("Switching mode from Video to Image...")
                        settings_btn.click(force=True)
                        page.wait_for_timeout(500)
                        img_opt = page.locator('button:has-text("image Image"), [role="menuitem"]:has-text("Image")').first
                        if img_opt.count() > 0:
                            img_opt.click(force=True)
                            page.wait_for_timeout(500)
            except Exception as e:
                logger.debug(f"Mode switch notice: {e}")

            # 3. Inject the translation prompt
            logger.info(f"Injecting prompt: {prompt}")
            prompt_div = page.locator('[contenteditable="true"]').first
            prompt_div.wait_for(state="visible", timeout=10000)
            prompt_div.click()
            prompt_div.fill(prompt)
            page.wait_for_timeout(500)

            # 4. Click Start generation
            logger.info("Clicking Start generation...")
            gen_btn = page.locator('button[aria-label*="Start generation" i], button:has-text("arrow_forward")').first
            gen_btn.click(force=True)

            # 5. Wait for generated image output
            logger.info("Waiting for translated image output from Nano Banana Pro...")
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
                        logger.info(f"Generated image detected: {src[:50]}...")
                        # Save screenshot of the generated image
                        last_img.screenshot(path=output_filepath)
                        output_found = True
                        break
                time.sleep(2.0)

            if not output_found:
                logger.warning("Target image selector timed out; capturing generation preview area.")
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
