import configparser
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from collections import deque
import re
import logging
import config

logging.basicConfig(format=config.CONFIG.FORMAT_STRING)
log = logging.getLogger(__name__)
log.setLevel(config.CONFIG.LOGLEVEL)

config = configparser.ConfigParser()
# Reading the configuration
config.read('dinakaran.ini')
print(config.sections())
URL = config['URL']['Address']
DELAY = config['URL']['Delay']
ROOT_PAGE = config['URL']['Page']
OUTPUT_FILENAME = config['URL']['OutputFileName']
LINKS_FILENAME = config['URL']['LinksFileName']
print(URL, DELAY)

link_dict = defaultdict(list)
link_visited = []
paragraphs = []
prev_len = len(link_dict)
web_link = deque()
active_link = URL
MAX_COUNT = 1000000000000
processed_page = 0
skipped_link = []

"""
TODO Enable the logging to the function and store the time spent in each request
TODO Multithread request to scrape the content faster
TODO Rewrite the implementation in OOP style, current implementation looks procedural 
"""

# scrape web pages
def scrape_page(url):
    global processed_page
    """
    Scrape the page content
    :param url: address to be scraped
    :return: return page content as string
    """
    page_request = requests.get(url)
    # Returns only proper html page, resources such as img, gif might present
    # Dinakaran website does not specify the encoding type so utf-8 check removed
    if page_request.status_code == 200 and page_request.headers.get("Content-Type") == "text/html":
        # by default system assumed 'ISO-8859-1' default HTML4 so reading as byte steam
        # Decoding it as utf-8
        content = page_request.content
        try:
            content = content.decode("utf-8")
        except:
            skipped_link.append(url)
            print("Skipped Scrape Page Content", url, page_request.status_code, page_request.headers.get("Content-Type"),
                  "processed_page", processed_page)
            return None
        link_visited.append(url)
        processed_page += 1
        print("Scrape Page Content", url, page_request.status_code, page_request.headers.get("Content-Type"), "processed_page",processed_page)
        return content
    else:
        None


# parse web pages
def parse_as_html(content):
    """
    Given string is parsed into html object for further operation on it
    :param content: string
    :return: ht
    """
    html_content = BeautifulSoup(content, 'html.parser')
    return html_content


def extract_content_from_tag(html_content, tag):
    tag_content = html_content.find(tag)
    return tag_content


def extract_paragraph(html_contents):
    """
    Extract the text present in the paragraph tag in HTML page
    :param html_contents: html page content
    :return: return nothing, appends to global variable paragraphs
    """
    list_of_para = html_contents.find_all('p')
    for item in list_of_para:
        link_text = item.text
        if link_text != '' and link_text is not None:
            # Skipping english character a-z, number 0-9 an and special character ,-
            link_text = re.sub("[a-zA-Z0-9,-]", '', link_text)
            paragraphs.append(link_text)


def extract_heading(html_contents):
    """
    Extract the text present in the h1 tag in the html page
    :param html_contents: html page content
    :return: return nothing, appends to global variable paragraphs
    """
    list_of_para = html_contents.find_all('h1')
    for item in list_of_para:
        link_text = item.text
        if link_text != '' and link_text is not None:
            # Skipping english character a-z, number 0-9 an and special character ,-
            link_text = re.sub("[a-zA-Z0-9,-]", '', link_text)
            paragraphs.append(link_text)


def validate_link(link_href):
    """
    Helps to validate the link and identify the link type to apply further rule
    1. check whether it is absolute, relative, in page reference
    2. Absolute url checked whether it belongs to parent domain to avoid scraping/storing other page content
    3. Relative url are appended with root url to help scraper
    4. In page reference are skipped along email address found
    5. If url containing resource such as jpg and png are skipped
    TODO move the resource checking list to configuration file
    TODO Move the constant to config file
    :param link_href: url collected from the web page
    :return: modified url or not valid if condition is not satisfied
    """
    if link_href is None or link_href == '':
        return "NOT_VALID"
    # check whether it absolute link
    urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', link_href)
    # Absolute if list is of length 1
    if len(urls) == 1:
        # domain which are not relevant checked
        if urls[0].find('dinakaran') == -1:
            return "NOT_VALID"
        # skip the page with same page reference and which contains email address
    elif link_href == "#" or link_href.find("@") != -1:
        return "NOT_VALID"
    elif not (link_href.startswith('http://www.dinakaran.com') or link_href.startswith('https://www.dinakaran.com')):
        link_href = ROOT_PAGE + link_href
    # to handle relative URL
    # to skip page with image/resources
    if (link_href not in link_visited and link_href not in skipped_link
            and not link_href.endswith(".jpg") and not link_href.endswith(".png")
            and not link_href.endswith(".jpeg")):
        return link_href
    else:
        return "NOT_VALID"


def collect_links(html_contents):
    """
    Collects the href present in the html page content
    :param html_contents: html page content
    :return: list of url collected from the given page
    """
    list_of_link = html_contents.find_all('a')
    # collect all the href - link from the page
    link_dict_local = []
    for item in list_of_link:
        # link_text = item.text
        link_href = item.attrs.get('href')
        # Avoiding other domain, collecting link from same  site
        link = validate_link(link_href)
        if link != "NOT_VALID":
            link_dict_local.append(link)
    return link_dict_local


def add_web_link(links):
    web_link.extend(links)


def get_link(url):
    """
    act as main function which helps to scrape web page, parse html, links, text based on url
    :param url: uniform resource location, page address
    :return: send the links present in the given web page
    """
    page_content = scrape_page(url)
    if page_content is not None:
        html_content = parse_as_html(page_content)
        body_content = extract_content_from_tag(html_content, 'body')
        extract_paragraph(body_content)
        extract_heading(body_content)
        return collect_links(body_content)
    else:
        return list()


def write_to_file():
    """
    Stores the links visited by scraper
    Stores the link skipped by scraper => later inspection, find reason and overcome in next iteration
    :return: return nothing
    """
    link_file_obj = open(LINKS_FILENAME, 'w')
    link_file_obj.write("\n".join(link_visited))
    skipped_link_obj = open("/home/hari/scraped_data/skipped.txt", 'w')
    skipped_link_obj.write("\n".join(skipped_link))
    link_file_obj.flush()
    skipped_link_obj.flush()
    link_file_obj.close()
    skipped_link_obj.close()


def write_paragraph():
    file_obj = open(OUTPUT_FILENAME, 'a')
    file_obj.write("\n".join(paragraphs))
    file_obj.flush()
    file_obj.close()


# Main Driver
try:
    while True:
        prev_len = len(link_dict)
        links_from_web_scraping = get_link(active_link)
        # storing in main links
        # link_dict[active_link] = links_from_web_scraping
        add_web_link(links_from_web_scraping)
        # if this condition fails, then there is no link to process further
        if len(web_link) != 0:
            active_link = web_link.pop()
        else:
            print("No Links to Process Further")
        # batching to avoid memory/heap growth
        if len(paragraphs) > 1000:
            write_paragraph()
            paragraphs = []
        # break the loop when limit reaches
        if processed_page == MAX_COUNT or web_link == 0:
            write_to_file()
            write_paragraph()
            break
except KeyboardInterrupt as e:
    print(active_link)
    print("Keyboard Exception Raised")
    write_to_file()
    write_paragraph()
    print(e)
except Exception as e:
    print(active_link)
    print("Exception Raised")
    write_to_file()
    write_paragraph()
    print(e)
