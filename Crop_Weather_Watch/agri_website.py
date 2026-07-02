from bs4 import BeautifulSoup
import pandas
import requests

url = "https://agriwelfare.gov.in/en/weather-watch"

headers = {
    "User-Agent": "Mozilla/5.0"
}

page = requests.get(url, headers=headers)
soup = BeautifulSoup(page.text, "html.parser")

print(soup)

