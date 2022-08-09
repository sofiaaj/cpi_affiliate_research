# cpi_affiliate_research
Our goal is to keep track of new publications by CPI affiliates which will be announced through daily tweets and a weekly newsletter. Because there are over 500 affiliates, we created an automated system using Google Scholar to help us do this.

## Code and data files

* get_google_scholar_id.py: Finds relevant information for new affiliates including their scholar id and affiliations. It accesses list of new affiliates from ‘new affiliates’ google sheet.
* find_new_publications.py: Goes through every affiliate in our database, finds their latest publication available on Google Scholar, and compares it to our previously stored publication to determine if it’s new. The script then uploads potential new publications to ‘new publications’ google sheet.
* process_new_publications.py: This script grabs google sheet and processes publications based on the status assigned by human verifier. If a new publication is accurate, the script creates a new tweet announcing the publication and updates existing affiliate database to reflect newest publication. If it’s not accurate, the script adds the title to an on-going list of “error” publications to avoid in the future.
* new_affiliates (google sheet): Every morning, we will pull from this google sheet to see if there are any new affiliates to add to our database. As such, any new members can be incorporated by writing their name into the file.
* new_publications (google sheet): The sheet will contain the new publications we found. Because mistakes in the scraping will be common, a person will access this sheet and update the ‘accurate’ row to indicate if the find was correct or not.
* cpi_affiliates_publications.csv: Sheet containing all information from CPI affiliates including their latest publication.
* error_pubs.csv: These are publications which previously yielded a false positive result. We check this data to make sure new publications we find haven’t already been flagged as inaccurate.
* potential_new_pubs.csv: List of potential new publications which we use to build out ‘new publications’ google sheet.

## Code overview

**Pre-processing**: The first step in the process was to obtain the Google Scholar ID of every CPI affiliate. This ID is useful because IDs are unique, names are not. Using the correct ID is much more likely to yield accurate search results. We used SerpAPI to do an organic search of each affiliate’s name and retrieve the corresponding ID. For those affiliates we couldn’t find an ID for, we do a second check using Scholarly. We were able to find a Scholar ID for over 70% of CPI affiliates. 

The second step is to create a database with the latest publication by each CPI affiliate. This data is essential because we will determine if a publication is “new” by comparing the latest title retrieved with the one in the database. We retrieve the latest publication for affiliates with a Google Scholar ID using Scholarly and fetch the rest using SerpAPI. 

After creating this database, we carried out a manual check to verify the results made sense. If, for example, we obtained a publication from an Electrical Engineering journal for an education researcher, we inspected the result to ensure we had the correct google scholar ID. 

**Daily tasks**: Every morning, we run a script to automatically:
1.	Open and read the file affiliate_publications.csv containing the list of publications for every affiliate
2.	Open and read the file tentative_titles.csv which contains the list of publications found on previous days which have not been reviewed by a person (status = pending).
3.	Run a script to fetch the latest publication for each affiliate on Google Scholar. 
a.	We will only fetch publications from affiliates not found in the tentative titles document. This is because we know these affiliates have new pubs and we don’t want to waste API calls fetching information from them again.
4.	We compare the title obtained to the title in our file. If the titles don’t match, this becomes a “tentative” new publication which we append to the tentative_titles.csv file.
5.	Open and read the file error_publications.csv containing publications a human reader has flagged as wrong (more on this below). We remove publications contained in this list from our tentative titles dataset.
a.	We also remove articles from error_publications.csv if they didn’t show up in the new publications list. This would indicate that the search for the author or author ID no longer returned the problematic result, and we can stop tracking it. We do this check so our error publications dataset does not become infinitely long with time. 
6.	For all remaining publications, we fill in any missing data:
a.	For each article, we get the following information: article title, publisher, and URL.
b.	Articles obtained using Scholarly don’t have an associated URL so we use SerpAPI to obtain it.
c.	Articles obtained using SerpAPI don’t have an associated journal/publisher. We have to use a different SerpAPI query to obtain it.
7.	Finally, we save and export the tentative titles file.

At this point, our process requires human intervention. These are the steps:
1.	Data from the tentative titles file is exported into a google sheet owned by the CPI bot google account I created (account information below). However, the sheet can also be shared with whoever will be editing it every day.
2.	The Google Sheet contains all information about the publication including the author, title, URL, journal, and Tweet draft. It also contains a column titled “accurate” which will be set to PENDING.
3.	Because there might be some false hits (e.g., pubs authored by a non-affiliate with the same name), a human will need to verify each row and update the “accurate” column to either TRUE or FALSE based on their assessment. 
4.	For accurate publications, a Tweet will be created with information from the publication. An example using data retrieved 08/07/2022:
a.	"New research from CPI affiliate, David Neumark: "Help Really Wanted? The Impact of Age Stereotypes in Job Ads on Applications from Older Workers". Read at https://www.nber.org/papers/w30287"
b.	The human reader will be able to directly edit the tweet draft in the Google Sheet if they want to make changes or replace the draft with the word “False” if they don’t want any tweets related to the publication. For inaccurate tweets, it is not necessary to edit the tweet as all drafts will be automatically discarded.
5.	The next morning, we will fetch the verified data from Google Drive. For each article, we will check its status and take one of three steps:
a.	If the publication hit is accurate, we use the Twitter API client to create a tweet on the CPI account announcing each publication. We also update our main affiliate information document to reflect the latest found publication. QUESTION: should we tweet all publications out at once or space them out?
b.	If the publication hit is inaccurate, we append it to the database error_publications.csv. We have this database because we know our search will likely return the same error file again (as we are doing the same search each time) and we want to avoid adding it to the list of potential titles and making the same mistake twice. 
c.	If a publication is still pending, we keep it in the potential titles database. This way, the publication will be included in the next day’s Google Sheet for another chance to get verified.
i.	This step is just safeguarding in case a person does not edit the Google Sheet that day or does not finish going through all rows. 
