from datetime import datetime
import re

import requests
from bs4 import BeautifulSoup, element
import pandas as pd


def scrape(search_term: str) -> pd.DataFrame:

    # replace spaces with "+" for url
    search_term = replace_spaces(search_term=search_term)

    # request the page
    webpage = request_webpage(search_term=search_term)

    # convert webpage to soup
    soup = convert_to_soup(webpage=webpage)

    # get number of pages to scrape
    last_page_number = get_last_page(soup=soup)

    # create empty Dataframe to store contents in
    contents = pd.DataFrame(columns=[
            "name",
            "link",
            "icon",
            "number_of_comments",
            "seeds",
            "leeches",
            "date",
            "size_in_mb",
            "uploader"])

    # iterate over each found page from 1 to last page number
    for page_number in range(1, last_page_number+1):
        
        # get the webpage
        webpage = request_webpage(
            search_term=search_term,
            page_number=page_number)
        
        # convert to soup
        soup = convert_to_soup(webpage=webpage)
       
        # get the contents
        page_contents = get_page_contents(soup)

        # concat page DataFrame to all pages DataFrame
        contents = pd.concat(
            objs=[contents, page_contents],
            ignore_index=True,
            copy=False,
            axis=0)

    return contents


def replace_spaces(search_term: str) -> str:
    return search_term.replace(" ", "+")


def request_webpage(search_term: str, page_number: int = 1):

    # set headers
    headers = {
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:88.0) Gecko/20100101 Firefox/88.0',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'upgrade-insecure-requests': '1',
        'te': 'trailers'}

    # build URL
    url = f"https://1337x.to/search/{search_term}/{page_number}/"

    # send request
    r = requests.get(url=url, headers=headers)

    return r.text


def convert_to_soup(webpage) -> BeautifulSoup:
    return BeautifulSoup(webpage, "html.parser")


def get_last_page(soup) -> int:

    # get link with text "Last"
    last_str = soup.find("a", string="Last")["href"]
    
    return int(last_str.split("/")[-2])


def get_page_contents(soup: BeautifulSoup) -> pd.DataFrame:

    # initialize pd.DataFrame for this page
    page_df = pd.DataFrame(columns=[
            "name",
            "link",
            "icon",
            "number_of_comments",
            "seeds",
            "leeches",
            "date",
            "size_in_mb",
            "uploader"])

    # get all rows of the table
    table_rows = soup.find_all("tr")

    # iterate over table rows and
    for table_row in table_rows[1:]:

        # get the data from this row
        row_data = get_row_data(table_row=table_row)

        # append this data to the DataFrame
        page_df = pd.concat(
            objs=[page_df, row_data],
            ignore_index=True,
            copy=False,
            axis=0)

    return page_df


def get_row_data(table_row: element.Tag) -> pd.DataFrame:

    # initialize pandas DataFrame
    row_data = pd.DataFrame()
    
    # get the name
    row_data.loc[0, "name"] = table_row.find("td", "name").text

    # get the link
    row_data.loc[0, "link"] = f"https://1337x.to{table_row.find_all('a')[1]['href']}"

    # get the icon
    row_data.loc[0, "icon"] = f"https://1337x.to{table_row.find('a', 'icon')['href']}"

    # get the number of comments
    row_data.loc[0, "number_of_comments"] = get_number_of_comments(table_row=table_row)

    # get the seeds
    row_data.loc[0, "seeds"] = int(table_row.find("td", "seeds").text)

    # get the leeches
    row_data.loc[0, "leeches"] = int(table_row.find("td", "leeches").text)

    # get the date
    row_data.loc[0, "date"] = get_date(table_row=table_row)

    # get the size in MB
    row_data.loc[0, "size_in_mb"] = get_size(table_row=table_row)

    # get uploader
    row_data.loc[0, "uploader"] = table_row.find(
        "td",
        re.compile("^vip|^user|^uploader|^trial-uploader")).text

    return row_data


def get_number_of_comments(table_row: element.Tag) -> int:

    try:
        return int(table_row.find(class_="comments").text)
    except AttributeError:
        return 0


def get_date(table_row: element.Tag) -> datetime | str:

    # find date string
    date_str = table_row.find("td", "coll-date").text

    # replace "st", "nd", ... form 1st, 2nd, ...
    date_str = re.sub("st|nd|rd|th|", "", date_str)

    # replace "'" in "'21" with "20"
    date_str = re.sub("'", "20", date_str)

    # convert to datetime
    try:
        return datetime.strptime(date_str, "%b. %d %Y")
    except ValueError:
        return date_str


def get_size(table_row: element.Tag) -> float:

    # find size string
    size_str = table_row.find("td", "size").text

    # remove "," from string
    size_str = size_str.replace(",", "")

    # find the match for MB or GB
    match = re.search("KB|MB|GB", size_str)

    # get the size as float
    size = float(size_str[:match.start()])

    # multiply with 1000 if matched "GB" 
    # or divide by 1000 if matched "KB"
    # to convert to MB
    if match.group() == "GB":
        size *= 1000
    elif match.group() == "KB":
        size /= 1000

    return size
