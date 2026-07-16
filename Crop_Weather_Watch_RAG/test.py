import requests

pdf_url = "https://agriwelfare.gov.in/Documents/CWWGDATA/CWWG_Weeklyreport_11052026.pdf"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://agriwelfare.gov.in/en/weather-watch"
}

r = requests.get(pdf_url, headers=headers)

print(r.status_code)