import configparser
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from collections import deque
import re

config = configparser.ConfigParser()
# Reading the configuration
config.read('configuration.ini')
print(config.sections())
URL = config['URL']['Address']
DELAY = config['URL']['Delay']
PAGE = config['URL']['Page']
OUTPUT_FILENAME = config['URL']['OutputFileName']
print(URL, DELAY)
link_dict = defaultdict(list)
link_visited = []
paragraphs = []
prev_len = len(link_dict)
web_link = deque()
active_link = URL


# scrape web pages
def scrape_page(url):
    page_request = requests.get(url)
    if page_request.status_code == 200 and page_request.headers.get("Content-Type") == "text/html; charset=UTF-8":
        content = page_request.text
        # print(content)
        link_visited.append(url)
        print("Scrape Page Content", url, page_request.status_code, page_request.headers.get("Content-Type"))
        return content
    else:
        None


# parse web pages
def parse_as_html(content):
    html_content = BeautifulSoup(content, 'html.parser')
    return html_content


def extract_content_from_tag(html_content, tag):
    tag_content = html_content.find(tag)
    return tag_content


def extract_paragraph(html_contents):
    list_of_para = html_contents.find_all('p')
    for item in list_of_para:
        link_text = item.text
        if link_text != '' and link_text is not None:
            # Skipping english character a-z, number 0-9 an and special character ,-
            link_text = re.sub("[a-zA-Z0-9,-]", '', link_text)
            paragraphs.append(link_text)


def validate_link(link_text, link_href):
    if (link_href is not None and link_href.startswith(PAGE)
            and link_text != '' and link_href not in link_visited
            and not link_href.endswith(".jpg") and not link_href.endswith(".png")
            and not link_href.endswith(".jpeg")):
        return True
    else:
        return False


def collect_links(url,html_contents):
    list_of_link = html_contents.find_all('a')
    # collect all the href - link from the page
    link_dict_local = []
    for item in list_of_link:
        link_text = item.text
        link_href = item.attrs.get('href')
        # Avoiding other domain, collecting link from same  site
        if validate_link(link_text, link_href):
            link_dict_local.append(link_href)
    return link_dict_local


def get_link(url):
    page_content = scrape_page(url)
    if page_content is not None:
        html_content = parse_as_html(page_content)
        body_content = extract_content_from_tag(html_content, 'body')
        extract_paragraph(body_content)
        return collect_links(URL, body_content)
    else:
        return list()


def add_web_link(links):
    for each in links:
        web_link.append(each)


def write_to_file():
    file_obj = open(OUTPUT_FILENAME, 'w')
    for each in paragraphs:
        file_obj.write(str(each))
    file_obj.flush()
    file_obj.close()


# Main Driver
try:
    while True:
        prev_len = len(link_dict)
        links_from_web_scraping = get_link(active_link)
        # storing in main links
        link_dict[active_link] = links_from_web_scraping
        add_web_link(links_from_web_scraping)
        # if this condition fails, then there is no link to process further
        if len(web_link) != 0:
            active_link = web_link.pop()
        else:
            print("No Links to Process Further")
        # break the loop when there is no more growth at dictionary
        if prev_len == len(link_dict):
            write_to_file()
            break
except Exception as e:
    write_to_file()
    print("Exception Raised")
    print(e)
