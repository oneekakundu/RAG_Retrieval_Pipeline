import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
# API URL
# /en/weather-watch → HTML webpage
# /en/getMOMDetail → API that returns the table

# API URL
url = "https://agriwelfare.gov.in/en/getMOMDetail"

headers = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest"
}

payload = {
    "Category": "Minutes Of Meeting",
    "Status": "Y"
}

# Get Data

response = requests.post(url, headers=headers, data=payload)
print("Status Code :", response.status_code)
json_data = response.json()
records = json_data["data"]

# Store Data

rows = []
for item in records:
    details = BeautifulSoup(item["Details"], "html.parser").get_text(strip=True)
    pdf_link = "https://agriwelfare.gov.in" + item["document_path"]
    rows.append({
        "Title": item["Title"],
        "Publish Date": item["PublishDate"],
        "Details": details,
        "PDF Link": pdf_link
    })

# Create DataFrame

df = pd.DataFrame(rows)
print(df.head())

# Save Metadata

df.to_csv(
    r"C:\Web scraping\Crop_Weather_Watch\Metadata.csv",
    index=False
)

print("\nMetadata Saved Successfully!")

# Search Between Dates

df["Publish Date"] = pd.to_datetime(df["Publish Date"], dayfirst=True)

start_date = input("\nEnter Start Date (dd-mm-yyyy): ")
end_date = input("Enter End Date (dd-mm-yyyy): ")

start_date = pd.to_datetime(start_date, dayfirst=True)
end_date = pd.to_datetime(end_date, dayfirst=True)

filtered_df = df[
    (df["Publish Date"] >= start_date) &
    (df["Publish Date"] <= end_date)
]

print("\nMatching PDFs\n")
print(filtered_df[["Publish Date", "Title"]])

# Save Filtered Metadata

filtered_df.to_csv(
    r"C:\Web scraping\Crop_Weather_Watch\Filtered_Metadata.csv",
    index=False
)

# Download PDFs

download_folder = r"C:\Web scraping\Crop_Weather_Watch\PDFs"

os.makedirs(download_folder, exist_ok=True)

download_headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://agriwelfare.gov.in/en/weather-watch"
}

print("\nDownloading PDFs...\n")

for index, row in filtered_df.iterrows():

    pdf_url = row["PDF Link"]

    pdf = requests.get(pdf_url, headers=download_headers)

    if pdf.status_code == 200:

        filename = row["Title"] + ".pdf"

        # Remove invalid filename characters
        filename = filename.replace("/", "-")
        filename = filename.replace(":", "-")

        filepath = os.path.join(download_folder, filename)

        with open(filepath, "wb") as file:
            file.write(pdf.content)

        print(filename, "Downloaded")

    else:
        print("Failed :", row["Title"])

print("\nAll PDFs Downloaded!")