import pandas as pd
import math
import re
import pygsheets
import tweepy
import json

CREDENTIALS_FILE = "twitter_keys.json"
ERROR_PUBS = "error_pubs.csv"
AFFILIATE_INFO = "cpi_affiliates_publications.csv"
POTENTIAL_NEW_PUBS = "potential_new_pubs.csv"
GOOGLE_SHEET_KEY = "1CiV3WkPRUkFcCfxmZI3xcQYx3ng3sjy8AfodqW_UbuU"

def create_tweet(tweet,tc):
    consumer_key = tc['twitter_consumer_key']
    consumer_secret = tc['twitter_consumer_secret']
    access_token_key = tc['twitter_access_token_key']
    access_token_secret = tc['twitter_access_token_secret']
    auth=tweepy.OAuthHandler(consumer_key,consumer_secret)
    auth.set_access_token(access_token_key,access_token_secret)
    api=tweepy.API(auth)
    try:
        resp = api.update_status(tweet)
        print("The following was tweeted: ")
        print(tweet)
    except:
        print("An error occured")

#Create tweet with new publications unless otherwise specified
#Update cpi_affiliates_full_info.csv with latest pub for those that were accurate
def process_accurate(df,tc,affiliate_info):
    true_pubs = df[df['accurate'] == 'TRUE']
    for index,row in true_pubs.iterrows():
        tweet = row['tweet_draft']
        if tweet != "False":
            create_tweet(tweet,tc)   
    true_pubs = true_pubs.drop(['result_id',
                'accurate',
                'tweet_draft',
                'oldpub_title'],axis=1).rename(columns={'newpub_title':'title'})
    remove_cpi_id = true_pubs['cpi_ID'].tolist()
    new_affil_info = affiliate_info[~affiliate_info.cpi_ID.isin(remove_cpi_id)]
    new_affil_info = new_affil_info.append(true_pubs)
    new_affil_info.to_csv(AFFILIATE_INFO,index=False)

def process_inaccurate(df,error_pubs):
    curr_error_pubs = df[df['accurate'] == "FALSE"]
    curr_error_pubs = curr_error_pubs.drop(['result_id',
                                        'accurate',
                                        'tweet_draft',
                                        'oldpub_title'],axis=1).rename(columns={'newpub_title':'title'})
    new_error_pubs = error_pubs.append(curr_error_pubs)
    new_error_pubs.to_csv(ERROR_PUBS,index=False)

#Update potential_titles.csv by only keeping those in pending status. In case person was not able to get
#through all of them
def process_pending(df):
    pending = df[df['accurate'] == "PENDING"]
    pending.to_csv(POTENTIAL_NEW_PUBS,index=False)

def get_google_sheet():
    gc = pygsheets.authorize()
    sh = gc.open_by_key(GOOGLE_SHEET_KEY)
    gs = sh.sheet1
    df = gs.get_as_df()
    #If any rows have a status other than PENDING, TRUE, or FALSE, change to PENDING:
    valid_status = ["FALSE","TRUE","PENDING"]
    df.loc[~df['accurate'].isin(valid_status),'accurate'] = "PENDING"
    return df

def main():
	error_pubs = pd.read_csv(ERROR_PUBS)
	affiliate_info = pd.read_csv(AFFILIATE_INFO)
	with open(CREDENTIALS_FILE) as f:
		tc = json.load(f)
	df = get_google_sheet()
	process_accurate(df,tc,affiliate_info)
	process_inaccurate(df,error_pubs)
	process_pending(df)

if __name__ == "__main__":
    main()