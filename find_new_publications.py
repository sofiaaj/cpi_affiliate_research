import pandas as pd
import math
from serpapi import GoogleSearch
from scholarly import scholarly
from scholarly import ProxyGenerator
import re
import json
import pygsheets

CREDENTIALS_FILE = "scraper_keys.json"
AFFILIATE_INFO = "cpi_affiliates_publications.csv"
POTENTIAL_NEW_PUBS = "potential_new_pubs.csv"
ERROR_PUBS = "error_pubs.csv"
SERP_API_KEY = ""
GOOGLE_SHEET_KEY = "1CiV3WkPRUkFcCfxmZI3xcQYx3ng3sjy8AfodqW_UbuU"

pubs_df = {}
pubs_df['author'] = []
pubs_df['affiliation'] = []
pubs_df['emails'] = []
pubs_df['google_scholar_ID'] = []
pubs_df['cpi_ID'] = []
pubs_df['link'] = []
pubs_df['oldpub_title'] = []
pubs_df['newpub_title'] = []
pubs_df['pubyear'] = []
pubs_df['citation'] = []
pubs_df['result_id'] = []

def set_api_key():
    with open(CREDENTIALS_FILE) as f:
        tc = json.load(f)
    global SERP_API_KEY
    SERP_API_KEY = tc['serp_api_key']

def get_search_params(query,citation=False,link=False):
    params = {}
    engine = "google_scholar_cite" if(citation) else "google_scholar"
    scisbd = 0 if(citation or link) else 2
    params['engine'] = engine
    params["api_key"] = SERP_API_KEY
    params["scisbd"] = scisbd
    params["q"] = query    
    return(params)

def get_row_values(row,values):
    toreturn = []
    for val in values:
        toreturn.append(row[val])
    return toreturn

def add_entry(searchtype,row,pub,old_title,title,link="Missing",result_id="Missing",pubyear="Missing",citation="Missing"):
    value_names = ['cpi_ID','author','affiliation','emails','google_scholar_ID']
    values = get_row_values(row,value_names)
    if(searchtype == "scholarly"):
        pubyear = pub.get('pub_year')
        citation = pub.get('citation')
    else:
        link = pub.get('link')
        result_id = pub.get('result_id')
    for i in range(0,len(values)):
        pubs_df[value_names[i]].append(values[i])
    pubs_df['oldpub_title'].append(old_title)            
    pubs_df['newpub_title'].append(title)
    pubs_df['pubyear'].append(pubyear)    
    pubs_df['citation'].append(citation)
    pubs_df['link'].append(link)
    pubs_df['result_id'].append(result_id)

def getlink(author,title):
    query = "author:\"" + author + "\" " + title
    search = GoogleSearch(get_search_params(query,link=True))
    results = search.get_dict()
    pubs = results.get('organic_results')
    if pubs:
        curr = pubs[0]
        checktitle = curr.get('title')
        link = curr.get('link') 
        result_id = curr.get('result_id')
    else:
        link = "Missing"
        result_id = "Missing"
    return(link,result_id)

def get_affiliate_df():
    affils = pd.read_csv(AFFILIATE_INFO)
    potential_titles = pd.read_csv(POTENTIAL_NEW_PUBS)
    # We don't check new publications for affiliates with publications to verify. This is to avoid wasting API calls
    # to retrieve the same information again
    affils_not_check = potential_titles['cpi_ID'].tolist()
    affils = affils[~affils.cpi_ID.isin(affils_not_check)]
    return(affils)

def find_pubs_scholar_id(affils):
    df = affils[affils['google_scholar_ID'] != "Missing"]
    df = df.sample(n=5)
    for index, row in df.iterrows():
        author = row['author']
        sch_id = row['google_scholar_ID']
        google_scholar_ID = sch_id.replace("\"","")      
        old_title = re.sub(r'[^A-Za-z0-9 ]+', '', row['title'].lower())
        print("Retrieving publications by... " + author)
        found = False
        try:
            search = scholarly.search_author_id(google_scholar_ID)
            found = True
        except:
            print("No google scholar found")    
        if found:
            result = scholarly.fill(search,sections=['publications'],sortby="year",publication_limit=1)
            pub = result['publications'][0]
            pub_id = pub['author_pub_id']
            title = re.sub(r'[^A-Za-z0-9 ]+', '', pub['bib']['title'].lower())
            if(title != old_title):
                print("Updating database...")
                print("Old title: ", old_title)
                print("New title: ", title)
                add_entry("scholarly",row,pub['bib'],old_title,title)            

def find_pubs_no_scholar_id(affils):
    df = affils[affils['google_scholar_ID'] == "Missing"]
    df = df.sample(n=5)    
    for index, row in df.iterrows():
        author = row['author']
        old_title = re.sub(r'[^A-Za-z0-9 ]+', '', row['title'].lower())
        query = "author:\"" + author + "\""
        print("Searching for... " + author)
        search = GoogleSearch(get_search_params(query))
        results = search.get_dict()
        pubs = results.get('organic_results')
        if pubs:
            curr = pubs[0]
            title = re.sub(r'[^A-Za-z0-9 ]+', '', curr.get('title').lower())
            if(title != old_title):
                print("Updating database...")
                print("Old title: ", old_title)
                print("New title: ", title)
                add_entry("serp",row,curr,old_title,title)

def get_citation(result_id):
    year = "Missing"
    citation = "Missing"
    search = GoogleSearch(get_search_params(citation=True,query=result_id))    
    results = search.get_dict()
    citation = results["citations"][0].get('snippet')
    cite_pattern = '" (.+)'
    match = re.search(cite_pattern, citation)
    if match:
        citation = match.groups()[0]
    year_pattern = '\((\d+)\)'
    match = re.search(year_pattern, citation)
    if match:
        year = match.groups()[0]
    return(citation,year)

#We check error listed titles dataset to make sure it's not in there. 
#We make a new errors dataset with only those that gave a match.
def check_errorlist(newpubs):
    df = pd.read_csv(ERROR_PUBS)
    error_pubs = df['title'].tolist()
    newpub_list = newpubs['newpub_title'].tolist()
    #Remove title from new pub list if contained in error list
    verified = newpubs[~newpubs.newpub_title.isin(error_pubs)]
    #Only keep error titles that appeared again. This is just so error list doesn't get too long.
    df = df[df.title.isin(newpub_list)]
    df.to_csv(ERROR_PUBS)
    return(verified)

#For remaining matches, we fetch missing data (citation, link, etc). 
#Usually, missing data consists of the paper's URL for data obtained through scholarly. 
#Citation and year for data updated with SerpAPI. 
def fetch_missing_data(newpubs):
    for index, row in newpubs.iterrows():
        #If link is missing for SerpAPI searches, it just means there is no link
        if(row['link'] == "Missing" and row['cpi_ID'] != "Missing"):
            link, result_id = getlink(row['author'],row['newpub_title'])
            newpubs.loc[index,'link'] = link
            newpubs.loc[index,'result_id'] = result_id
        if((row['citation'] == "Missing" or row['citation'] == "") and row['result_id'] != "Missing"):
            citation, year = get_citation(row['result_id'])
            newpubs.loc[index,'citation'] = citation
            newpubs.loc[index,'pubyear'] = year
    return newpubs

#We add a tweet draft so it can be approved.
#We also add a categorical variable for "status" and set it to "Pending".
def add_tweet_status_vars(newpubs):
    tweets = []
    statuses = []
    for index, row in newpubs.iterrows():
        name = row['author']
        title = row['newpub_title']
        link = row['link']
        tweet = "New research from CPI affiliate, %s: \"%s\". Read at %s" % (name,title.title(),link)
        status = "PENDING"
        tweets.append(tweet)
        statuses.append(status)
    newpubs['tweet_draft'] = tweets
    newpubs['accurate'] = statuses
    return(newpubs)

def update_google_sheet(newpubs):
    #We don't make a new potential matches document, we add to it so as to keep anything that might still be pending.
    potential_titles = pd.read_csv(POTENTIAL_NEW_PUBS)
    potential_titles = potential_titles.append(newpubs)
    potential_titles.to_csv(POTENTIAL_NEW_PUBS,index=False)
    gc = pygsheets.authorize()
    sh = gc.open_by_key(GOOGLE_SHEET_KEY)
    gs = sh.sheet1
    gs.clear()
    gs.set_dataframe(potential_titles,(1,1))
    #sh.share("myFriend@gmail.com")

def main():
    set_api_key()
    year_pattern = '\((\d+)\)'
    affils = get_affiliate_df()
    find_pubs_scholar_id(affils)
    find_pubs_no_scholar_id(affils)
    newpubs = pd.DataFrame.from_dict(pubs_df)
    newpubs = check_errorlist(newpubs)
    newpubs = fetch_missing_data(newpubs)
    newpubs = add_tweet_status_vars(newpubs)
    update_google_sheet(newpubs)

if __name__ == "__main__":
    main()