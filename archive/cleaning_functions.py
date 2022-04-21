# general imports
import pandas as pd
import numpy as np
from time import time, sleep
import json
import requests
import random
random.seed(11)

# IMPORT JSONS
import os
import glob
from lxml import html

start = time()
jsons_as_series = []
file_list = glob.glob('data/scotus_opinions/*.json')

for filename in file_list:
    with open(filename) as json_data:
        json_1 = json.load(json_data)
        jsons_as_series.append(pd.Series(json_1))

scotus_df = pd.DataFrame(jsons_as_series)
print("Elapsed opinion loading time:", round((time()-start)/60, 1), 'minutes')


# REMOVE DISMISSALS (coextensive with non-per-curiam, short texts with no majority opinion)
# -- mostly denial of certiorari, but some misc. dismissals
scotus_df['per_curiam'] = scotus_df.per_curiam.astype(bool)
dismissals_index = scotus_df[
    (~scotus_df.per_curiam)
    & (scotus_df.html_with_citations.map(lambda x: len(x) < 5000))
    & (scotus_df.html_with_citations.map(lambda x: x.lower().find('delivered the opinion of the court.') == -1))
].index
scotus_df = scotus_df.drop(dismissals_index)

# LOAD AND LINK CLUSTERS
# first, convert all http URLs to https (we'll need this for consistency of merging, and user convenience)
def to_https(url):
    if url[:5] != 'https':
        url = 'https' + url[4:]
    if url[:32] == 'https://www.courtlistener.com:80': # fix erroneous :80 urls
        url = 'https://www.courtlistener.com' + url[32:]
    return url

scotus_df['cluster'] = scotus_df['cluster'].map(to_https)

start = time()
jsons_as_series = []
file_list = glob.glob('data/scotus_clusters/*.json')

for filename in file_list:
    with open(filename) as json_data:
        json_1 = json.load(json_data)
        jsons_as_series.append(pd.Series(json_1))

clusters_df = pd.DataFrame(jsons_as_series)
clusters_df['resource_uri'] = clusters_df.resource_uri.map(to_https)
print("Elapsed cluster loading time:", round((time()-start)/60, 1), 'minutes')

# merge info from clusters_df into opinions_df
cases_df = pd.merge(scotus_df,
                       clusters_df[['case_name',
                                    'date_filed',
                                    'federal_cite_one',
                                    'resource_uri',
                                    'scdb_id',
                                    'scdb_decision_direction',
                                    'scdb_votes_majority',
                                    'scdb_votes_minority'
                                   ]],
                       how='left',
                       left_on='cluster',
                       right_on='resource_uri')

# winnow down to the relevant columns (note: we'll drop the few cases of plain_text for consistency's sake)
cases_df = cases_df[[
    'case_name',
    'author_str',
    'date_filed',
    'federal_cite_one',
    'per_curiam',
    'author',
    'cluster',
    'absolute_url',
    'html_with_citations',
    'scdb_id',
    'scdb_decision_direction',
    'scdb_votes_majority',
    'scdb_votes_minority'
]]

# PARSE HTML
start = time()
cases_df['html_with_citations'] = cases_df.html_with_citations.astype(str)
cases_df = cases_df[cases_df.html_with_citations.map(lambda x: len(x) > 1)] # eliminate one empty string
cases_df['absolute_url'] = 'https://www.courtlistener.com' + cases_df.absolute_url
def extract_text(raw_html):
    return html.fromstring(raw_html).text_content().strip()
cases_df['plain_text'] = cases_df.html_with_citations.map(lambda x: extract_text(x))
is_empty_now = cases_df.plain_text.isnull()
print('Total html parsing time:', round((time()-start)/60, 1), 'minutes')
print("After parsing html, there are {} empty opinions remaining".format(sum(is_empty_now)))
cases_df = cases_df[~cases_df.per_curiam.isnull()]

# remove remaining certiorari and misc. non-decisions: no listed decision direction, and no majority opinion
non_decision_index = cases_df[(~cases_df.per_curiam)
         & (cases_df.scdb_decision_direction.isnull())
         & (cases_df.plain_text.map(
             lambda x: x.lower().find('delivered the opinion of the court.')==-1))
        ].index
cases_df = cases_df.drop(non_decision_index)

# remove duplicate cases
cases_df = cases_df.drop_duplicates(subset='federal_cite_one')

# convert dates to datetime
import datetime
cases_df['date_filed'] = pd.to_datetime(cases_df.date_filed)
cases_df['year_filed'] = cases_df.date_filed.map(lambda x: x.year)
cases_df['year_filed'] = cases_df.year_filed.astype(int)
# filter by date here if desired:
# cases_df = cases_df[cases_df.year_filed >= 1970]

# SANITY CHECK: do dates and titles match texts?
checks = [83,1065,4508]
for c in checks:
    i = cases_df.index[c]
    print(
        '\n\n***SANITY CHECK {}***: \n',
        'CASE NAME:', cases_df.case_name[i], '\n',
        'CASE DATE:', cases_df.date_filed[i], '\n', '\n',
        'CASE TEXT:\n', cases_df.plain_text[i][:500])

# PARSE plain text into separate opinions
def find_author_listed_before(text, index):
    '''
    Returns first justice name preceding INDEX in the same sentence of TEXT.  If no justice named
    between INDEX and the end of the previous sentence, returns None.
    '''
    text = text[:index].lower().replace('mr.','mr ')
    start_index = text.rfind(".")
    sentence = text[start_index:]

    justice_index = sentence.find("justice ")
    if justice_index == -1:
        justice_index = sentence.find("justice\n")
        if justice_index == -1:
            # catch rare format "Smith, Justice, delivered the opinion of the court."
            justice_index = sentence.find("justice, delivered")
            if justice_index != -1:
                return "justice " + sentence[:justice_index].split()[-1][:-1] # name is prev word sans comma
    if justice_index == -1:
        return None

    name_words = sentence[justice_index:].split()[:2]
    name_words[-1] = name_words[-1].replace(',','') # remove trailing comma if present
    name = " ".join(name_words)
    if name == 'justice dissentin': # catch rare false flag (actually a citation)
        return None
    return name

def get_index_from_keyphrase(text, start_index, keyphrase, alternate_keyphrase=None):
    '''
    returns first index of KEYPHRASE(str) in TEXT[START_INDEX:] that has an author name
    preceding it in the same sentence; returns None if none found
    '''
    search_text = text[start_index:]
    index = search_text.find(keyphrase)
    # if there isn't a justice preceding the keyphrase in the same sentence (rare),
    # then this is a false flag.  Move on to the next occurrence of the keyphrase and repeat until true flag or end.
    while index != -1 and find_author_listed_before(search_text, index + len(keyphrase)-2) is None:
        new_index = search_text[(index + len(keyphrase)):].find(keyphrase)
        index = new_index if new_index == -1 else new_index + (index + len(keyphrase))
        # because the search started with the index of the prev find as 0
    if index != -1:
        index += len(keyphrase) + start_index
    elif alternate_keyphrase is not None:
        index = get_index_from_keyphrase(text, start_index, alternate_keyphrase, None)
    return index

def get_indices(text, per_curiam=False):
    '''
    returns dictionary of beginning indices of majority / concurring / dissenting opinions in TEXT
    '''
    text = text.lower()
    indices = {}
    bookmark = 0  # keeps track of where to start our next search

    if per_curiam:
        indices['majority'] = text.find("per curiam.")
        if indices['majority'] != -1:
            indices['majority'] += len("per curiam.")
    else:
        indices['majority'] = get_index_from_keyphrase(text, 0, 'delivered the opinion of the court.', 'join.')

    if indices['majority'] == -1: # short-circuit if there is no majority opinion: it's a dismissal (or an anomaly)
        return indices

    bookmark = indices['majority']

    indices['first_concurring'] = get_index_from_keyphrase(
        text,
        bookmark,
        'concurring.',
        'concurring in the judgment.'
    )
    bookmark = max(bookmark, indices['first_concurring'])

    if indices['first_concurring'] == -1:
        indices['second_concurring'] = -1
    else:
        indices['second_concurring'] = get_index_from_keyphrase(
            text,
            bookmark,
            'concurring.'
        )
        bookmark = max(bookmark, indices['second_concurring'])

    indices['first_dissenting'] = get_index_from_keyphrase(
        text,
        bookmark,
        'dissenting.'
    )
    bookmark = max(bookmark, indices['first_dissenting'])


    if indices['first_dissenting'] == -1:
        indices['second_dissenting'] = -1
    else:
        indices['second_dissenting'] = get_index_from_keyphrase(
            text,
            bookmark,
            'dissenting.'
        )

    return indices

def remove_next_intro(text):
    '''removes last sentence of text if it's introducing the next opinion '''
    if text[-11:] in ['concurring.', 'dissenting.']:
        end_of_prev_sentence = text[:-1].replace('Mr.','Mr ').rfind('.')
        text = text[:end_of_prev_sentence + 2] # +2 to include last char and period
    return text

def split_and_label(text, per_curiam=False, include_concurring=True, include_second_dissent=True):
    ''' returns a list of tuples formatted as (author, majority/concurring/dissenting, text)'''
    opinions = []
    indices = get_indices(text, per_curiam)

    if indices['majority'] == -1: # indicates empty / dismissal / haywire
        return [None]

    majority_endpoint = indices['first_concurring'] if indices['first_concurring'] != -1 \
                            else indices['first_dissenting']
    if per_curiam:
        majority = (
            'per_curiam',
            'per_curiam',
            remove_next_intro( text[indices['majority']:majority_endpoint] ).strip()
        )
    else:
        majority = (
            find_author_listed_before(text, indices['majority']-1), # -1 to avoid including final period (find_author)
            'majority',
            remove_next_intro( text[indices['majority']:majority_endpoint] ).strip()
        )
    opinions.append(majority)

    concurring_endpoint = indices['second_concurring'] if indices['second_concurring'] != -1 \
                            else indices['first_dissenting']
    if include_concurring and indices['first_concurring'] != -1:
        first_concurring = (
            find_author_listed_before(text, indices['first_concurring']-1),
            'concurring',
            remove_next_intro( text[indices['first_concurring']:concurring_endpoint] ).strip()
        )
        opinions.append(first_concurring)

    if indices['first_dissenting'] != -1:
        first_dissenting = (
            find_author_listed_before(text, indices['first_dissenting']-1),
            'dissenting',
            remove_next_intro( text[indices['first_dissenting']:indices['second_dissenting']] ).strip()
        )
        opinions.append(first_dissenting)

    if include_second_dissent and indices['second_dissenting'] != -1:
        second_dissenting = (
            find_author_listed_before(text, indices['second_dissenting']-1),
            'second_dissenting',
            remove_next_intro( text[indices['second_dissenting']:] ).strip()
        )
        opinions.append(second_dissenting)

    # clip "notes" section from end of the text of the last opinion in the case file
    notes_index = opinions[-1][2].find('NOTES')
    if notes_index == -1:
        notes_index = opinions[-1][2].find('APPENDIXES')
    if notes_index != -1:
        opinions[-1] = (opinions[-1][0],
                        opinions[-1][1],
                        opinions[-1][2][:notes_index])

    return opinions

columns = [
    'author_name',
    'category',
    'per_curiam',
    'case_name',
    'date_filed',
    'federal_cite_one',
    'absolute_url',
    'cluster',
    'year_filed',
    'scdb_id',
    'scdb_decision_direction',
    'scdb_votes_majority',
    'scdb_votes_minority',
    'text'
]
opinions_df = pd.DataFrame(columns=columns)
counter = 0
start = time()

# .drop_duplicates(subset='federal_cite_one')
for i in cases_df.index:
    counter += 1
    print("Processing row {} of {}".format(counter, cases_df.shape[0]), end='\r')
    text = cases_df.plain_text[i]
    per_curiam = cases_df.per_curiam[i]
    opinions = split_and_label(text, per_curiam)
    if opinions[0] is None: # if no majority opinion, either empty or something is haywire
        continue
    for opinion in opinions:
        new_row = pd.Series(
            [
                opinion[0], # author
                opinion[1], # majority/concurring/dissenting
                per_curiam,
                cases_df.case_name[i],
                cases_df.date_filed[i],
                cases_df.federal_cite_one[i],
                cases_df.absolute_url[i],
                cases_df.cluster[i],
                cases_df.year_filed[i],
                cases_df.scdb_id[i],
                cases_df.scdb_decision_direction[i],
                cases_df.scdb_votes_majority[i],
                cases_df.scdb_votes_minority[i],
                opinion[2] # text
            ],
        index=columns)

#         print(new_row[:-1])
        opinions_df.loc[opinions_df.shape[0]] = new_row # append without creating new object each time

print("Elapsed opinion parsing time:", round((time()-start)/60, 1), 'minutes     ')

# retyping as necessary
opinions_df.per_curiam = opinions_df.per_curiam.astype(bool)
opinions_df.year_filed = opinions_df.year_filed.astype(int)

# drop any blank opinions that got read in (very few - about 7)
opinions_df = opinions_df[opinions_df.text.map(lambda x: len(x) > 1)]

# resolve apostrophe format discrepancies
opinions_df.author_name = opinions_df.author_name.map(lambda x: x.replace('’','\''))
opinions_df.author_name = opinions_df.author_name.map(lambda x: x.replace('`','\''))

# remove very rare (mostly erroneous) author_name values if desired:
# rare_authors = list(opinions_df.author_name.value_counts()[opinions_df.author_name.value_counts() <= 5].index)
# opinions_df = opinions_df[~opinions_df.author_name.isin(rare_authors)]
