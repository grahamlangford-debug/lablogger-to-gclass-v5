import os
import re
import sys
import json
import requests
import traceback
from datetime import datetime
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("LABLOGGER_EMAIL")
PASSWORD = os.environ.get("LABLOGGER_PASSWORD")
WEB_APP_URL = os.environ.get("WEB_APP_URL")

def scrape_lablogger():
    print("🚀 Step 1: Validating environment variables...")
    
    missing = []
    if not EMAIL: missing.append("LABLOGGER_EMAIL")
    if not PASSWORD: missing.append("LABLOGGER_PASSWORD")
    if not WEB_APP_URL: missing.append("WEB_APP_URL")
    
    if missing:
        print(f"❌ Error: Missing GitHub Secrets: {', '.join(missing)}")
        sys.exit(1)

    lessons = []

    try:
        with sync_playwright() as p:
            print("🌐 Step 2: Launching Playwright browser...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("🔑 Step 3: Logging into LabLogger...")
            page.goto("https://www.lablogger.co.uk/login", wait_until="domcontentloaded", timeout=60000)
            
            page.wait_for_selector("input[name='email']", timeout=15000)
            page.fill("input[name='email']", EMAIL)
            page.fill("input[name='password']", PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_timeout(3000)

            print("📅 Step 4: Opening Timetable page...")
            page.goto("https://www.lablogger.co.uk/timetable", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            def extract_lessons():
                found = []
                try:
                    cards = page.locator(".timetable-event, .booking-card, tr.event, .event-card, .booking, .event").all()
                except Exception as e:
                    print(f"⚠️ Warning during card lookup: {e}")
                    return []

                for card in cards:
                    try:
                        text = card.inner_text().strip()
                        if not text:
                            continue

                        date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
                        time_match = re.search(r"(\d{1,2}:\d{2})\s*(?:am|pm)?", text, re.IGNORECASE)
                        class_match = re.search(r"(\d{1,2}[A-Z]+(?:/[A-Za-z]+)?)", text)

                        if class_match and time_match:
                            class_name = class_match.group(1) if class_match else None
                            start_time = time_match.group(1) if time_match else None

                            if not class_name or not start_time:
                                continue

                            try:
                                formatted_time = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
                            except ValueError:
                                formatted_time = start_time

                            lines = [line.strip() for line in text.split("\n") if line.strip()]
                            title = lines[0] if lines else "Science Lesson"
                            date_str = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

                            found.append({
                                "className": class_name,
                                "title": title,
                                "date": date_str,
                                "startTime": formatted_time
                            })
                    except Exception:
                        continue
                return found

            print("🔎 Step 5: Scraping initial timetable week...")
            current_lessons = extract_lessons()
            print(f"   Extracted {len(current_lessons)} lessons from current week view.")
            lessons.extend(current_lessons)

            for week_ahead in range(1, 3):
                try:
                    next_btn = page.get_by_text("Next", exact=False).first
                    if next_btn and next_btn.is_visible():
                        print(f"➡️ Step 6: Advancing forward to Week +{week_ahead}...")
                        next_btn.click()
                        page.wait_for_timeout(3000)
                        next_lessons = extract_lessons()
                        print(f"   Extracted {len(next_lessons)} lessons from Week +{week_ahead}.")
                        lessons.extend(next_lessons)
                    else:
                        print("ℹ️ No 'Next' button detected. Finishing timetable scan.")
                        break
                except Exception as nav_err:
                    print(f"⚠️ Navigation stopped: {nav_err}")
                    break

            browser.close()

    except Exception as err:
        print(f"❌ CRITICAL ERROR during scraping execution:")
        print(traceback.format_exc())
        sys.exit(1)

    print(f"📦 Step 7: Preparing payload with {len(lessons)} total lessons...")

    if lessons:
        try:
            response = requests.post(
                WEB_APP_URL,
                json={"lessons": lessons},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            print("📋 Google Apps Script Web App Response:")
            print(response.text)
        except Exception as req_err:
            print(f"❌ Failed to deliver payload to Google Web App URL: {req_err}")
            sys.exit(1)
    else:
        print("⚠️ Zero lessons were extracted across all scanned timetable weeks.")

if __name__ == "__main__":
    scrape_lablogger()
