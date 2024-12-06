# AssessingSCOTUSBias
Identifying Biases in SCOTUS Judgements Based on Political Affiliations 
Project Team: Javier Aristizabal, Katie Harris, Oluwatoorese Lasebikan, Anum Malik, Hajra Shahab

## Getting started:
All csv files needed to run the [topic_analysis.ipynb](topic_analysis.ipynb) can be found in the [Data](Data) folder. **_Before running the notebook you will need to unzip the file all_opinions_1940.zip and install the WordCloud library if it isn't already._**

`pip install https://github.com/sulunemre/word_cloud/releases/download/2/wordcloud-0.post1+gd8241b5-cp39-cp39-win_amd64.whl`

The UDA SCOTUS [pdf](UDA_SCOTUS.pdf) contains the slides from our final presentation.
## Project Background:

The overlap between judicial ideology and political inclinations of the appointed parties has been a consistent feature of the constitutional politics of the United States. This has caused an increased strain on the public’s acceptance of the distinction between what is considered to fall in the realm of law versus underlying political agendas. According to the Pew Research Center, Republican perceptions lean towards a moderate Supreme Court whereas Democrats believe it is mostly conservative in its decisions. Within this context, Justices of the Supreme Court of the United States (SCOTUS) should carefully consider the types of rhetoric they employ in their written statements. This project will aim to conduct an ideological analysis of the Justices of the Supreme Court and determine whether their political affiliations introduce a bias, if any, within their rulings over time. In doing so, we will identify if there are cyclical behaviors/patterns of conservatism or liberalism that could be associated with their political affiliation, the political era, or with evolving social movements in the country.

## Data:

We will be using 3 data sets. The first is a data set containing almost all the SCOTUS opinions ever written, who they were written by, which case they were written for, which year they were filed, and whether it was a dissenting opinion. Using this data set, we will be able to track justices’ opinions over time. Using NLP analysis in conjunction with this data set of  justice profiles, we will try and track how a judge’s ideology changes over time and how often they agree with other justices appointed by the same political party. The set of justice profiles contains who each justice was appointed by, when he/she began their term, and ended his/her term. We will supplement this data set with presidential data to match justices and presidents to political parties. This presidential data set provides the beginning and end date of the terms of each president, as well as their political affiliation. 

## Methodology: 

Using the appropriate datasets, we will first pair the Supreme Court judges according to their political parties over their tenure, i.e, Republican or Democrat. Given the extensive opinions shared from 1789 to 2020, we will begin our analysis by restricting the dataset to 1940 to 2020 given the social context and to account for any computational limitations.

After cleaning and normalizing the raw text, we will adopt a three-pronged approach to ascertain a judge’s position:

1)    Collect the statistics of the common words in the form of a frequency table and group by entities to assess the key phrases for further exploration.
 
2)    Determine the type of cases that have been historically significant in terms of extreme views of both political parties i.e; same-sex marriage, or abortion rights. Our goal is to classify text to a particular topic, and we will do this by using co-occurrence of words, K-means clustering, and LDA techniques. LDA will allow us to vectorize and create stopwords to further restrict the dataset by assessing words that are more frequent or infrequent. Once the topics have been separated, they can be evaluated overtime to see if they are becoming more common. 

3)   We will assign numerical values, ‘score’, that indicate the degree of conservatism or liberalism to each of the judge’s opinions. This will allow us to evaluate their performance with respect to his/her political affiliation. We intend to consider the year of the opinion when evaluating the topic according to the nuance for its time. For example: women’s rights, or immigration laws might be perceived differently in the 1800s than the 1900s. 

Our quantitative reasoning will rely on matching the judge, the text, and the numerical values such as the frequency of the words, the number of opinions of every judge, and their liberal or conservative score. We aim to form a conclusion with results showing us a scale of degree against judges.  

## Limitations: 

1) Computational Limitation: Since the data is from 1789 to 2020, we may run into computational limitations and will have to work with a sample. Working with a sample may prevent us from making deeper analysis for over 200 years of SCOTUS rulings and understanding precedence for each type of case. Even with the restricted dataset (1940s -2020), the rulings are long and analyzing each opinion would involve robust computational space.
2) Inconsistent Data Frequency: Due to inefficient record keeping practice in the past and overall fewer number of cases, we have fewer data points to work with for early years of dataset. This may limit us from passing conclusive statements regarding any Justice’s action towards a case. 
3) Contextualize Each Case: While it is important to contextualize each case as per the evolving political narrative in any given time, it would require a robust understanding of US political history, precedence set in each issue and overall political climate at the time of each ruling.
4) External Factors Affecting Judgment: While political affiliation can certainly develop biases in a Justice’s ruling, there are multiple other factors that could contribute to these biases and affect human judgment that cannot be fully accounted for in our analysis. For example, a study showed that judges gave more lenient judgments at the start of the day and immediately after a scheduled break in court proceedings such as lunch.
