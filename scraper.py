import os
import re
import json
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright

EMAIL = os.environ.get("LABLOGGER_EMAIL")
PASSWORD = os.environ.get("LABLOGGER_PASSWORD")
WEB_APP_URL = os.environ.get("WEB_APP_URL")

def scrape_lablogger():
    if not EMAIL or not PASSWORD or not WEB_APP_URL:
        print("❌ Missing required GitHub secrets! Check LABLOGGER_EMAIL, LABLOGGER_PASSWORD, and WEB_APP_URL.")
        return

    lessons = []

    with sync_playwright() as p:
        print("🌐 Launching Chromium browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()

        try:
            print("🔑 Step 1: Navigating to LabLogger login...")
            page.goto("https://www.lablogger.co.uk/login", wait_until="networkidle")
            
            page.fill("input[name='email']", EMAIL)
            page.fill("input[name='password']", PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_timeout(3000)

            print("📅 Step 2: Navigating to Timetable...")
            page.goto("https://www.lablogger.co.uk/timetable", wait_until="networkidle")
            page.wait_for_timeout(3000)

            def extract_lessons():
                found = []
                # Find all potential booking cards/rows
                elements = page.locator(".timetable-event, .booking-card, tr.event, .event-card, .booking, .event").all()
                
                for elem in elements:
                    try:
                        text = elem.inner_text().strip()
                        if not text:
                            continue

                        date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
                        time_match = re.search(r"(\d{1,2}:\d{2})\s*(?:am|pm)?", text, re.IGNORECASE)
                        class_match = re.search(r"(\d{1,2}[A-Z]+(?:/[A-Za-z]+)?)", text)

                        if class_match and time_match:
                            class_name = class_match.group(1)
                            start_time = time_match.group(1)

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
                    except Exception as e:
                        continue
                return found

            # Scrape current week
            print("🔎 Step 3: Scraping current week...")
            current_lessons = extract_lessons()
            print(f"   Found {len(current_lessons)} lessons in current week view.")
            lessons.extend(current_lessons)

            # Safely navigate to future weeks
            for week_ahead in range(1, 3):
                try:
                    # Look for Next button using flexible text matching
                    next_btn = page.get_by_text("Next", exact=False).first
                    if next_btn and next_btn.is_visible():
                        print(f"➡️ Step 4: Navigating forward to Week +{week_ahead}...")
                        next_btn.click()
                        page.wait_for_timeout(3000)
                        next_lessons = extract_lessons()
                        print(f"   Found {len(next_lessons)} lessons in Week +{week_ahead}.")
                        lessons.extend(next_lessons)
                    else:
                        print("ℹ️ No 'Next' button visible. Stopping week navigation.")
                        break
                except Exception as nav_err:
                    print(f"⚠️ Navigation warning (non-fatal): {nav_err}")
                    break

        except Exception as main_err:
            print(f"❌ Error during scraping session: {main_err}")
        finally:
            browser.close()

    print(f"📦 Step 5: Sending {len(lessons)} lessons to Google Apps Script...")
    
    if lessons:
        try:
            response = requests.post(WEB_APP_URL, json={"lessons": lessons}, timeout=30)
            print("📋 Response from Google Apps Script:")
            print(response.text)
        except Exception as req_err:
            print(f"❌ Failed to reach Web App URL: {req_err}")
    else:
        print("⚠️ No lessons were extracted. Check if your LabLogger timetable has bookings listed.")

if __name__ == "__main__":
    scrape_lablogger()
