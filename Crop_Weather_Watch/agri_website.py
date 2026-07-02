import requests
import pandas as pd
from bs4 import BeautifulSoup
# API URL
# /en/weather-watch → HTML webpage
# /en/getMOMDetail → API that returns the table
url = "https://agriwelfare.gov.in/en/getMOMDetail"

# Headers
headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}

# Data sent to the API
payload = {
    "Category": "Minutes Of Meeting",
    "Status": "Y"
}

# Send POST Request

response = requests.post(url, headers=headers, data=payload)

print("Status Code :", response.status_code)

# Convert response into JSON
json_data = response.json()

# Extract Records
records = json_data["data"]

rows = []

for i, item in enumerate(records, start=1):

    # Remove HTML tags from Details column
    details = BeautifulSoup(item["Details"], "html.parser").get_text(strip=True)

    # Create complete PDF URL
    pdf_link = "https://agriwelfare.gov.in" + item["document_path"]

    rows.append({
        "Sl. No.": i,
        "Title": item["Title"].strip(),
        "Publish Date": item["PublishDate"],
        "Details": details,
        "PDF Link": pdf_link
    })

# Create DataFrame
df = pd.DataFrame(rows)

print("\nFirst 5 Records\n")
print(df.head())

# Save Complete Data
df.to_csv(
    r"C:\Web scraping\Crop_Weather_Watch\CWWG_Minutes.csv",
    index=False
)
print("\nComplete CSV Saved Successfully!")

# SEARCH BETWEEN TWO DATES
# Convert Publish Date into datetime format
df["Publish Date"] = pd.to_datetime(
    df["Publish Date"],
    dayfirst=True
)

print("\nSearch PDFs Between Two Dates")

start_date = input("Enter Start Date (dd-mm-yyyy): ")
end_date = input("Enter End Date (dd-mm-yyyy): ")

start_date = pd.to_datetime(start_date, dayfirst=True)
end_date = pd.to_datetime(end_date, dayfirst=True)

# Filter Data
filtered_df = df[
    (df["Publish Date"] >= start_date) &
    (df["Publish Date"] <= end_date)
]

print("\nMatching Records\n")

if filtered_df.empty:
    print("No records found.")
else:
    print(filtered_df[["Publish Date", "Title", "PDF Link"]])

    filtered_df.to_csv(
        r"C:\Web scraping\Crop_Weather_Watch\Filtered_PDFs.csv",
        index=False
    )

    print("\nFiltered CSV Saved Successfully!")