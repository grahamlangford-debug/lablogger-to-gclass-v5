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
        print("❌ Missing required GitHub secrets!")
        return

    lessons = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🔑 Logging into LabLogger...")
        page.goto("https://www.lablogger.co.uk/login")
        page.fill("input[name='email']", EMAIL)
        page.fill("input[name='password']", PASSWORD)
        page.click("button[type='submit']")
        page.wait_for_timeout(3000)

        print("📅 Opening Timetable...")
        page.goto("https://www.lablogger.co.uk/timetable")
        page.wait_for_timeout(3000)

        def extract_lessons():
            found = []
            events = page.query_selector_all(".timetable-event, .booking-card, tr.event, .event-card, .booking")
            for event in events:
                text = event.inner_text().strip()
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
            return found

        # 1. Scrape current week view
        current_lessons = extract_lessons()
        print(f"🔎 Found {len(current_lessons)} lessons in current week view.")
        lessons.extend(current_lessons)

        # 2. Safely navigate forward up to 2 weeks
        for week_ahead in range(1, 3):
            try:
                next_btn = page.query_selector("a:has-text('Next'), .next-week, button:has-text('Next'), a[title*='Next']")
                if next_btn and next_btn.is_visible():
                    print(f"➡️ Navigating forward to Week +{week_ahead}...")
                    next_btn.click()
                    page.wait_for_timeout(3000)
                    next_lessons = extract_lessons()
                    print(f"🔎 Found {len(next_lessons)} lessons in Week +{week_ahead}.")
                    lessons.extend(next_lessons)
            except Exception as e:
                print(f"⚠️ Could not advance week further: {e}")
                break

        browser.close()

    print(f"📦 Found {len(lessons)} total lessons across scanned weeks. Sending to Google Apps Script...")
    
    response = requests.post(WEB_APP_URL, json={"lessons": lessons})
    print("📋 Response from Google Apps Script:")
    print(response.text)

if __name__ == "__main__":
    scrape_lablogger()
