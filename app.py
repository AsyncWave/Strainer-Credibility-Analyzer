import numpy as np
import json
import tweepy
import models
import pandas as pd
from bson import json_util
from flask import Flask, request, jsonify, render_template, abort
from flask_pymongo import PyMongo 
from flask_cors import CORS, cross_origin
from datetime import datetime
import collections

from joblib import dump, load

CONSUMER_KEY = "eCcOHT9FzWkINeH78O2tN5Mr7"
CONSUMER_SECRET = "qlsSKiJtgTbLwC5YMEHzGvN4P2Lvygxm7EgsTSdVwTJBTLLRpL"
ACCESS_TOKEN = "715007031556448256-V9UNiZR80oypXR7D1G8ofAQObYDkOUj"
ACCESS_TOKEN_SECRET = "2hekp24EvWAl6khZCaxyTfVtbz2XVG4dcFO4DP8jp96Je"
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

sentiment_model = load('./model/sentiment_model.pkl')
category_model = load('./model/category_model.pkl')
credibility_model =  load('./model/credibility_model.pkl')
mongo = PyMongo()

app = Flask(__name__)

app.config["MONGO_URI"] = 'mongodb+srv://Malith:789123@cluster0-r8ack.mongodb.net/test?retryWrites=true&w=majority'
#Example_____________
#app.config["MONGO_URI"] = 'mongodb+srv://<user>:<password>@strainercluster-igrpg.azure.mongodb.net/<collection-name>?retryWrites=true&w=majority'
CORS(app)

app.config['CORS_HEADERS'] = 'Content-Type'

mongo.init_app(app)

@app.route('/')
@cross_origin()
def home():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
@cross_origin()
def query():
    data = request.get_json(force=True)
    if not data or not 'queryId' in data:
        abort(400)
    queryToInsert = {
        'queryId': data['queryId'],
        'field1': data['field1'],
        'field2': data['field2'],
        'field3': data['field3']
    }
    query_collection = mongo.db.queries #select queries collection
    query_collection.insert(queryToInsert) #insert
    return jsonify({'query': data['queryId'],'message': 'Query added successfully'}), 201

@app.route('/get/<id>', methods=['GET'])
@cross_origin()
def get(id):
    try:
        queryId = int(id)
    except:
        return jsonify({'message': 'Not a valid Id'}), 400
    
    query_collection = mongo.db.queries
    result = json.dumps(list(query_collection.find({'queryId' : queryId},{"_id": 0, "field1": 1, "field2": 1, "field3": 1 })),default=json_util.default)
    if result == "[]":
        return jsonify({'queryId': queryId, 'message': 'No query is available for Id ' + id + ', rechek and try again!'}), 400
    return result, 200

@app.route('/getUserProfile/<username>', methods=['GET'])
@cross_origin()
def getUserProfile(username):
    try:
        user = api.get_user(username)
    except:
        return jsonify({'message': 'Twitter Error'}), 400

    replies = models.getSentiment(username,sentiment_model,category_model)
    create_date = datetime.strptime(str(user.created_at), "%Y-%m-%d %H:%M:%S")
    today = datetime. today()
    datetime.today()
    profile_age = ((today - create_date).days)
    last_reply = replies[len(replies)-1]
    intersted_category = last_reply['category']
    credibility_data = pd.DataFrame(np.array([[last_reply['agreement_score'], profile_age, user.default_profile, user.favourites_count,
                                               user.followers_count, user.friends_count, intersted_category[0], user.listed_count,
                                               len(user.screen_name), user.statuses_count, user.verified]])
                                    ,columns=['agreement_score', 'days_between_create', 'default_profile', 'favourites_count', 'followers_count', 'friends_count', 'interested_news_category', 'listed_count', 'screen_name_length','statuses_count','verified'])
    credibility_rating = models.getCredibilityRating(credibility_data, credibility_model)

    intereted_category = [item for item, count in collections.Counter(last_reply['category_list']).items() if count > 3]
    reputation_rating = models.getReputation(user,last_reply['agreement_score'])
    return jsonify({'user': user.name,
                    'screen_name':user.screen_name,
                    'followers_count': str(user.followers_count),
                    'created_at': str(create_date.date()),
                    'profile_age': str(profile_age),
                    'status_count': str(user.statuses_count),
                    'profile_image_url_https': str(user.profile_image_url_https),
                    'description': str(user.description),
                    'location': str(user.location),
                    'profile_location': str(user.profile_location),
                    'protected': str(user.protected),
                    'verified': str(user.verified),
                    'friends_count': str(user.friends_count),
                    'default_profile': str(user.default_profile),
                    'replies': replies,
                    'credibility': reputation_rating,
                    'agreement_score': last_reply['agreement_score'],
                    'interested_category':intereted_category[0]}), 200

if __name__ == "__main__":
    app.run(debug=True)
