from bs4 import BeautifulSoup
import requests
import re
from pathlib import Path
import os
from pdfkit import from_url as save_pdf
from multiprocessing import pool, cpu_count, Lock
from unidecode import unidecode
from weasyprint import HTML

HOST = "https://teara.govt.nz"
NUMBERED_PAGE_REGEX = r"/page-\d+"


def save_page(url, path):
    HTML(url).write_pdf(str(path))


def make_path_name(name):
    # unfortunately macrons have to be stripped as they crash wkhtmltopdf if they're in the filename
    return unidecode(name)\
        .replace(" ", "_")\
        .replace("/", "_")\
        .replace(",", "")\
        .replace("’", "")\
        .replace(":", "")\
        .replace("?", "")\
        .lower()


def check_if_numbered(url):
    return bool(re.search(NUMBERED_PAGE_REGEX, url))


def get_root_page(url):
    return re.sub(NUMBERED_PAGE_REGEX, "", url)


def process_article(url, path, title):
    print(
        f"Saving: {url}\n",
        f"at path: {path / (make_path_name(title) + '.pdf')}"
    )
    local_lock = Lock()

    local_lock.acquire()
    try:
        print(f"Making directory {path} ...")
        path.mkdir(parents=True, exist_ok=True)
        print(f"{path} exists: {str(os.path.isdir(path))}")
    finally:
        if os.path.isdir(path):
            local_lock.release()
    
    local_lock.acquire()
    try:
        save_page(HOST + url + '/print', path / (make_path_name(title) + '.pdf'))
    finally:
        local_lock.release()


def dedupe(params_list):
    seen = []
    for param_item in params_list:
        if param_item[0] in [i[0] for i in seen]:
            seen.append(param_item)
        else:
            continue
    return seen


if __name__ == '__main__':
    root_file_path = Path('./archive')

    sitemap_req = requests.get("https://teara.govt.nz/en/site-map")
    soup = BeautifulSoup(sitemap_req.text, 'html.parser')

    section_titles = soup.find_all('h2', class_='', id='')
    sections = soup.find_all('div', class_='theme-col')

    to_process = []

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
                    params = (get_root_page(article_url), section_path, subsection_title_text)
                else:
                    params = (article_url, subsection_path, article_title_text)
                to_process.append(params)

    to_process = dedupe(to_process)

    with pool.Pool(processes=cpu_count()) as p:
        p.starmap(process_article, to_process)
