from serpapi import GoogleSearch
import pandas as pd
import math
from scholarly import scholarly
import json
import string
import pygsheets
import random

CREDENTIALS_FILE = "scraper_keys.json"
AFFILIATE_INFO = "cpi_affiliates_publications.csv"
SERP_API_KEY = ""
GOOGLE_SHEET_KEY = "1cNlU1zKcTTitx630vwFqqCMD6sv90NvniddBRNnRdTc"

new_row = {}
new_row['cpi_ID'] = []
new_row['author'] = []
new_row['google_scholar_ID'] = []
new_row['affiliation'] = []
new_row['emails'] = []
new_row['title'] = []
new_row['pubyear'] = []
new_row['citation'] = []
new_row['link'] = []

def get_search_params(query):
    params = {}
    params['engine'] = "google_scholar"
    params["api_key"] = SERP_API_KEY
    params["q"] = query    
    return(params)

def set_api_key():
    with open(CREDENTIALS_FILE) as f:
        tc = json.load(f)
    global SERP_API_KEY
    SERP_API_KEY = tc['serp_api_key']

#try to get google scholar information using SerpAPI
def serp_search(name):
    print("Searching for... " + name)
    search = GoogleSearch(get_search_params(name))
    results = search.get_dict()
    profiles = results.get("profiles")
    if profiles:
        authors = profiles.get('authors')
        if authors:
            author = authors[0]
            google_scholar_id = author.get('author_id')
            affiliation = author.get('affiliations')
            emails = author.get('email')
            author = name
    values = [author,google_scholar_id,affiliation,emails]
    return values

#We try to fill the remaining values using scholarly
def scholarly_search(author):
    search = scholarly.search_author(author)
    print("Searching for... " + author)
    try:
        curr = next(search)
        info = scholarly.fill(curr,sections=['publications'],sortby="year",publication_limit=1)
        scholar_id = info.get('scholar_id')
        email = info.get('email_domain')
        affil = info.get('affiliation')
        author = info.get('name')
    except StopIteration:
        print("No results for... " + author)
        scholar_id = "Missing"
        email = "Missing"
        affil = "Missing"
        author = author
    values = [author,scholar_id,affil,email]
    return values

def get_google_sheet():
    gc = pygsheets.authorize()
    sh = gc.open_by_key(GOOGLE_SHEET_KEY)
    gs = sh.sheet1
    df = gs.get_as_df()
    return(df)

def add_entry(values):
    value_names = ['author','google_scholar_ID','affiliation','emails','cpi_ID']
    missing_names = ['title','pubyear','citation','link']
    for i in range(0,len(values)):
        new_row[value_names[i]].append(values[i])
    for name in missing_names:
        new_row[name] = "Missing"

def main():
    set_api_key()
    df = get_google_sheet()
    for name in df['author'].tolist():
        values = serp_search(name)
        if len(values) == 0:
            values = scholarly_search(name)
        cpi_ID = ''.join(random.choices(string.ascii_uppercase, k=3)) + ''.join(random.choices(string.digits,k=1))
        values.append(cpi_ID)
        print(values)
        add_entry(values)
    affils = pd.read_csv(AFFILIATE_INFO)
    affils = affils.append(pd.DataFrame.from_dict(new_row))
    affils.to_csv(AFFILIATE_INFO,index=False)

if __name__ == "__main__":
    main()