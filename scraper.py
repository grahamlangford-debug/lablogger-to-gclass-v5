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

        print("📅 Scraping weekly timetable...")
        page.goto("https://www.lablogger.co.uk/timetable")
        page.wait_for_timeout(3000)

        # Find all schedule entries on the timetable
        events = page.query_selector_all(".timetable-event, .booking-card, tr.event")

        for event in events:
            text = event.inner_text().strip()
            if not text:
                continue

            # Extract date, class code, lesson title, start time
            # Expected pattern example: "10TTQ/Ph - Energy Changes - 11:20"
            date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)
            time_match = re.search(r"(\d{1,2}:\d{2})\s*(?:am|pm)?", text, re.IGNORECASE)
            class_match = re.search(r"(\d{1,2}[A-Z]+(?:/[A-Za-z]+)?)", text)

            if class_match and time_match:
                class_name = class_match.group(1)
                start_time = time_match.group(1)
                
                # Format start time to 24-hour HH:MM
                try:
                    formatted_time = datetime.strptime(start_time, "%H:%M").strftime("%H:%M")
                except ValueError:
                    formatted_time = start_time

                # Extract lesson title lines
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                title = lines[0] if lines else "Science Lesson"

                date_str = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

                lessons.append({
                    "className": class_name,
                    "title": title,
                    "date": date_str,
                    "startTime": formatted_time
                })

        browser.close()

    print(f"📦 Found {len(lessons)} lessons. Sending to Google Apps Script...")
    
    # Send scraped lessons to Google Apps Script Web App
    response = requests.post(WEB_APP_URL, json={"lessons": lessons})
    print("📋 Response from Google Apps Script:")
    print(response.text)

if __name__ == "__main__":
    scrape_lablogger()
