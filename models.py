import numpy as np
from flask import Flask, request, jsonify, render_template
import pickle
from flask import Flask, request, jsonify, render_template, abort
import json
import pandas as pd
import csv
from datetime import datetime
import sys
import GetOldTweets3 as got

from joblib import dump, load

def getCredibilityRating(dataset, credibility_model):
    scaler = load('./model/scaler.pkl')
    lbl_Encoder = load('./model/lbl_encoder.pkl')

    for index, row in dataset.iterrows():

        dataset.listed_count = dataset.listed_count.astype(float)
        dataset.favourites_count = dataset.favourites_count.astype(float)
        listed_count = dataset.loc[index, 'listed_count']
        favourites_count = dataset.loc[index, 'favourites_count']
        dataset.loc[index, 'list/fav'] = listed_count * favourites_count

    # Transform data
    dataset = dataset.drop(['listed_count', 'favourites_count'], axis=1).dropna(how='all')
    # print('---------------->', dataset['interested_news_category'], file=sys.stderr)
    dataset['verified'] = lbl_Encoder.fit_transform(dataset['verified'])
    dataset['default_profile'] = lbl_Encoder.fit_transform(dataset['default_profile'])
    dataset['interested_news_category'] = lbl_Encoder.fit_transform(dataset['interested_news_category'])

    # Made all the features matter the "same" amount (Normal distribution).
    x = scaler.transform(dataset.values)

    # Predict labels
    y_predict = credibility_model.predict(x)

    # Mapping the correct cluster
    y_list = []
    for index, rate in enumerate(y_predict):
        if rate == 4:
            y_list.append(3)
        elif rate == 0:
            y_list.append(2)
        elif rate == 3:
            y_list.append(1)
        elif rate == 1:
            y_list.append(4)
        elif rate == 2:
            y_list.append(5)

    return y_list


def getSentiment(querySearchTerm,sentiment_model,category_model):

    tweetLimit = 20
    reply_list = []
    category_list =[]
    positive_count = 0
    total_reply_count = 0
    agreement_score = 0
    try:
        tweetCriteria = got.manager.TweetCriteria().setQuerySearch(querySearchTerm) \
            .setSince('2019-04-21') \
            .setUntil('2020-01-22') \
            .setMaxTweets(tweetLimit)
        tweets = enumerate(got.manager.TweetManager.getTweets(tweetCriteria))
    except Exception as e:
        print(e, "ALL TWEET ERROR!!")


    for index, x in tweets:
        reply = x.text
        total_reply_count = total_reply_count + 1
        if (reply == None or reply == ' ' or type(reply) == float):
            continue
        try:
            sentiment = sentiment_model.predict([reply])
            category = category_model.predict([reply])
            category_list.insert(index, category[0])

            if (sentiment == [1]):
                positive_count = positive_count + 1
            agreement_score = positive_count / total_reply_count

        except Exception as e:
            agreement_score = 0
        except ZeroDivisionError:
            agreement_score = 0

        reply_list.append({'tweet': reply, 'sentiment': sentiment.tolist(), 'category': category.tolist(),'agreement_score':agreement_score,'category_list':category_list})



    return reply_list





def getReputation(user,agreement_score):

    if(user.verified  and  user.followers_count>10000000 and agreement_score>=0.8):
        print('---------------->', user.verified, user.followers_count, file=sys.stderr)
        return 5
    elif(agreement_score>=0.8 or  user.followers_count>1000000):
        return 4
    elif (agreement_score >= 0.5 and user.followers_count > 500000):
        return 3
    elif (user.followers_count > 10000 and user.statuses_count > 1000):
        print('---------------->', user.verified, file=sys.stderr)
        return 2
    else:
        return 1

