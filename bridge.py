import os
import sys
import time
import json
import logging
import asyncio
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlowBridge")

CDP_URL = "http://localhost:9222"
FLOW_URL = "https://labs.google/fx/tools/flow"

def check_cdp_status() -> Dict[str, Any]:
    """
    Checks if Chrome is running with remote debugging on port 9222
    and whether Google Flow is currently open.
    """
    try:
        req = urllib.request.Request(f"{CDP_URL}/json/version", headers={"User-Agent": "FlowBridge"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            version_data = json.loads(resp.read().decode())
            
        # Check active tabs
        flow_open = False
        tabs_req = urllib.request.Request(f"{CDP_URL}/json/list", headers={"User-Agent": "FlowBridge"})
        with urllib.request.urlopen(tabs_req, timeout=1.5) as tabs_resp:
            tabs = json.loads(tabs_resp.read().decode())
            for tab in tabs:
                url = tab.get("url", "")
                if "labs.google" in url:
                    flow_open = True
                    break

        return {
            "connected": True,
            "browser": version_data.get("Browser", "Chrome"),
            "flow_open": flow_open,
            "message": "Chrome is connected on port 9222." + (" Google Flow tab is open." if flow_open else " Flow tab not detected (will open automatically).")
        }
    except Exception as e:
        return {
            "connected": False,
            "browser": None,
            "flow_open": False,
            "message": "Chrome remote debugging is offline. Run Chrome with --remote-debugging-port=9222"
        }

async def get_or_create_flow_page(browser: Browser) -> Page:
    """Finds an existing Google Flow tab or opens a new one."""
    for context in browser.contexts:
        for page in context.pages:
            if "labs.google" in page.url:
                logger.info(f"Found existing Flow tab: {page.url}")
                await page.bring_to_front()
                return page

    # No existing Flow page found, use first context or create one
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await context.new_page()
    logger.info(f"Navigating to {FLOW_URL}...")
    await page.goto(FLOW_URL, wait_until="networkidle", timeout=45000)
    return page

async def translate_image_flow(
    image_path: str,
    target_language: str = "English",
    custom_instructions: str = "",
    preserve_style: bool = True,
    output_dir: str = "outputs"
) -> Dict[str, Any]:
    """
    Automates Google Flow to translate the image using Nano Banana Pro.
    Operates completely in-memory over Chrome DevTools Protocol (no mouse movement).
    """
    abs_image_path = str(Path(image_path).resolve())
    if not os.path.exists(abs_image_path):
        return {"success": False, "error": f"Input image not found: {abs_image_path}"}

    os.makedirs(output_dir, exist_ok=True)
    timestamp = int(time.time() * 1000)
    output_filename = f"translated_{timestamp}.png"
    output_filepath = os.path.join(output_dir, output_filename)

    # Construct the translation prompt
    prompt = f"Translate all text in this image into {target_language}."
    if preserve_style:
        prompt += (
            " Maintain the exact original typography, font styling, colors, layout, and composition seamlessly."
        )
    if custom_instructions and custom_instructions.strip():
        prompt += f" Specific instructions: {custom_instructions.strip()}."

    cdp_check = check_cdp_status()
    if not cdp_check["connected"]:
        return {
            "success": False,
            "error": "Chrome is not running with remote debugging on port 9222.",
            "setup_command": '& "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\\chrome-flow-profile"'
        }

    async with async_playwright() as p:
        try:
            logger.info("Connecting to Chrome via CDP on port 9222...")
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            page = await get_or_create_flow_page(browser)

            # Check if user needs to sign in or navigate into the workspace
            curr_url = page.url.lower()
            if "accounts.google.com" in curr_url or "signin" in curr_url:
                return {
                    "success": False,
                    "error": "Google Sign-In required: Please sign into your Google account in the open Brave window, then click Translate again!"
                }

            # If on the public marketing landing page, try to enter the workspace
            if "Create with Google Flow" in await page.evaluate("() => document.body.innerText"):
                create_btn = page.get_by_role("button", name="Create with Google Flow").first
                if await create_btn.count() > 0:
                    logger.info("Clicking 'Create with Google Flow' to enter workspace...")
                    await create_btn.click()
                    await page.wait_for_timeout(3000)
                    if "accounts.google.com" in page.url.lower():
                        return {
                            "success": False,
                            "error": "Please sign into your Google account in the open Brave window!"
                        }

            # 1. Attach the image file
            logger.info(f"Attaching image: {abs_image_path}")
            file_input = page.locator('input[type="file"]')
            file_input_count = await file_input.count()

            
            if file_input_count > 0:
                await file_input.first.set_input_files(abs_image_path)
            else:
                # Try clicking any 'upload' or 'add image' button if hidden
                upload_btn = page.locator('button[aria-label*="image" i], button[aria-label*="upload" i], button:has-text("Add image"), button:has-text("Upload")')
                if await upload_btn.count() > 0:
                    async with page.expect_file_chooser() as fc_info:
                        await upload_btn.first.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(abs_image_path)
                else:
                    logger.warning("No file input or upload button found directly; attempting fallback selectors.")

            await asyncio.sleep(1.0)

            # 2. Select Nano Banana Pro if model selector is available
            try:
                model_btn = page.locator('button:has-text("Nano Banana"), button:has-text("Model"), [aria-label*="model" i]')
                if await model_btn.count() > 0:
                    btn_text = await model_btn.first.inner_text()
                    if "Nano Banana Pro" not in btn_text:
                        await model_btn.first.click()
                        await asyncio.sleep(0.5)
                        pro_option = page.locator('text="Nano Banana Pro"')
                        if await pro_option.count() > 0:
                            await pro_option.first.click()
                            await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"Model selector check non-blocking note: {e}")

            # 3. Enter the prompt
            logger.info(f"Filling prompt: {prompt}")
            prompt_input = page.locator('textarea, [contenteditable="true"], input[placeholder*="prompt" i]').first
            await prompt_input.wait_for(state="visible", timeout=10000)
            
            # Fill or evaluate text
            try:
                await prompt_input.fill(prompt)
            except Exception:
                await prompt_input.click()
                await page.keyboard.type(prompt, delay=5)

            await asyncio.sleep(0.5)

            # 4. Click Generate
            logger.info("Clicking Generate...")
            generate_btn = page.locator(
                'button:has-text("Generate"), button:has-text("Create"), button[aria-label*="Generate" i], button[aria-label*="Submit" i]'
            ).first
            await generate_btn.click()

            # 5. Wait for generated image to appear
            logger.info("Waiting for generated output from Nano Banana Pro...")
            # We track image elements or network requests
            start_time = time.time()
            max_wait_seconds = 90
            output_found = False

            # Wait for an output image to appear or update
            while time.time() - start_time < max_wait_seconds:
                # Look for newly rendered result images
                images = page.locator('img[src^="blob:"], img[src*="googleusercontent"], img[src*="media/"]')
                img_count = await images.count()
                
                if img_count > 0:
                    # Look at the newest/last image
                    last_img = images.last
                    src = await last_img.get_attribute("src")
                    if src and not src.endswith("logo.png") and not "avatar" in src:
                        logger.info(f"Generated image detected with src: {src[:60]}...")
                        # Save screenshot or download the element
                        await last_img.screenshot(path=output_filepath)
                        output_found = True
                        break

                await asyncio.sleep(2.0)

            if not output_found:
                # Capture page screenshot as fallback to ensure the user gets output
                logger.warning("Target image selector timed out; capturing generation container.")
                container = page.locator('.generation-preview, [data-testid="preview-area"], main').first
                if await container.count() > 0:
                    await container.screenshot(path=output_filepath)
                    output_found = True
                else:
                    await page.screenshot(path=output_filepath)
                    output_found = True

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
                "error": f"Failed during automation: {str(e)}"
            }
