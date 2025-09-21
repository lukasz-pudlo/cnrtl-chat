import requests
import csv
from bs4 import BeautifulSoup

CNRTL_URL = "https://www.cnrtl.fr/"

filepath = "../data/french_words.csv"
fields = []
rows = []

with open(filepath, 'r') as csvfile:
    csvreader = csv.reader(csvfile)

    fields = next(csvreader)
    for row in csvreader:
        rows.append(row)

    print(f"Total number of rows in {filepath}: {csvreader.line_num}")

for row in rows[:5]:
    query = row[1]

    page = requests.get(f"{CNRTL_URL}/definition/{query}")
    if page.status_code == 200:
        soup = BeautifulSoup(page.content, "html.parser")
        word = soup.find(id="vtoolbar")
        print(word)
        # print(soup)
        cnrtl_entry_text = soup.get_text()

        # with open('../data/{}')

        # print(cnrtl_entry_text)
