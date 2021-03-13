from bs4 import BeautifulSoup
import requests
import re
from pathlib import Path
import os
from pdfkit import from_url as save_pdf
import time

HOST = "https://teara.govt.nz"
NUMBERED_PAGE_REGEX = r"/page-\d+"


def save_page(url, path):
    print("Saving " + str(path))
    # single_file_html = make_single_file_page(url)
    # with open(path, 'wb') as file:
    #     file.write(single_file_html.encode('utf-8'))
    save_pdf(url,
             path,
             options={
                 'print-media-type': None
             })


def make_path_name(name):
    # unfortunately macrons have to be stripped as they crash wkhtmltopdf if they're in the filename
    return name\
        .replace(" ", "_")\
        .replace(",", "")\
        .replace("’", "")\
        .replace(":", "")\
        .replace("ā", "a")\
        .replace("ē", "e")\
        .replace("ī", "i")\
        .replace("ō", "o")\
        .replace("ū", "u")\
        .replace("?", "")\
        .lower()


def check_if_numbered(url):
    return bool(re.search(NUMBERED_PAGE_REGEX, url))


def process_article(url, path, single_page):
    next_url = url
    while next_url:
        page_req = requests.get(HOST + next_url)
        page_soup = BeautifulSoup(page_req.text, 'html.parser')

        page_title = page_soup.title.text

        os.makedirs(path, exist_ok=True)
        save_page(HOST + next_url, path / (make_path_name(page_title) + '.pdf'))

        if single_page:
            break

        next_page_link = page_soup.find('a', class_='next-text') or page_soup.find('a', id='next-wrapper')
        if next_page_link:
            next_url = next_page_link['href']
        else:
            next_url = None


root_file_path = Path('./archive')

sitemap_req = requests.get("https://teara.govt.nz/en/site-map")
soup = BeautifulSoup(sitemap_req.text, 'html.parser')

section_titles = soup.find_all('h2', class_='', id='')
sections = soup.find_all('div', class_='theme-col')

for st, s in zip(section_titles, sections):
    section_title_text = st.text
    section_path = root_file_path / make_path_name(section_title_text)

    subsection_titles = s.find_all('div', class_='subtheme-col')
    subsection_entries = s.find_all('div', class_='entry-col')

    for sst, e in zip(subsection_titles, subsection_entries):
        subsection_title_text = sst.text
        subsection_path = section_path / make_path_name(subsection_title_text)

        article_links = e.find_all('a')

        for article in article_links:
            article_title_text = article.text

            article_url = article['href']

            is_numbered_url = check_if_numbered(article_url)
            if is_numbered_url:
                article_path = subsection_path
            else:
                article_path = subsection_path / make_path_name(article_title_text)
            process_article(article_url, article_path, is_numbered_url)
            time.sleep(1)
