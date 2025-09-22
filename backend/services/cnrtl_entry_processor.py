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

for row in rows[1010:1011]:
    query = row[1]

    page = requests.get(f"{CNRTL_URL}/definition/{query}")
    if page.status_code == 200:
        # Get content of the CNRTL entry and find title
        soup = BeautifulSoup(page.content, "html.parser")
        title = soup.find("title").get_text().split()[-1].lower()
        # content_raw_text = soup.get_text().strip()
        lexicontent = soup.find(id="lexicontent")
        definitions = soup.find_all("span", class_="tlf_cdefinition")

        definition_list = [definition.get_text() for definition in definitions]

        # Save the entry as a text file
        definition_text = "\n".join(definition_list)
        txt_file_name = f"{title}.txt"
        txt_file_path = f"../data/cnrtl_entries/{txt_file_name}"
        with open(txt_file_path, 'w') as f:
            f.write(definition_text)

        # word = soup.find(id="vtoolbar")
        # print(word)
        # print(soup)

        # with open('../data/{}')

        # print(cnrtl_entry_text)
