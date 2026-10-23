# -------------------------------------------------------------
    # SAFE PAYLOAD DELIVERY
    # -------------------------------------------------------------
    print(f"📦 Step 5: Sending {len(lessons)} total lessons to Google Apps Script...")
    
    if not WEB_APP_URL or not WEB_APP_URL.startswith("http"):
        print("❌ Error: WEB_APP_URL is missing or invalid in GitHub Secrets!")
        return

    if lessons:
        try:
            response = requests.post(
                WEB_APP_URL, 
                json={"lessons": lessons}, 
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            print("📋 Response from Google Apps Script:")
            print(response.text)
        except Exception as req_err:
            print(f"❌ Failed to deliver payload to Web App URL: {req_err}")
    else:
        print("⚠️ No lessons extracted. Check if your LabLogger timetable has visible bookings.")

if __name__ == "__main__":
    scrape_lablogger()
