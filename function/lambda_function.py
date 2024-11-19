from tweepy import Client
import requests
import time
try:
    from secrets import secrets
except:
    import os
    secrets = None
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import random

OPENAI_API_KEY = secrets.get("OPENAI_API_KEY") if secrets else os.environ.get('OPENAI_API_KEY')
OPENAI_ASST_ID = secrets.get("OPENAI_ASSISTANT_ID") if secrets else os.environ.get('OPENAI_ASSISTANT_ID')

BOT_NAME = "mcafee-bot"
mongo_uri = secrets.get("MONGO_URI") if secrets else os.environ.get('MONGO_URI')
pymongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
try:
    pymongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Get the bot config
db = pymongo_client.get_database("TWITTER_BOTS")
config_collection = db.get_collection("bot_config")
bot_config = config_collection.find_one({"name": BOT_NAME})
tweet_history_collection = db.get_collection("tweet_history")


def make_openai_request(method, endpoint, data=None):
    url = f"https://api.openai.com/v1/{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2"
    }
    response = requests.request(method, url, headers=headers, json=data)
    return response.json()


tweepy_client = Client(
    consumer_key=secrets.get("CONSUMER_KEY") if secrets else os.environ.get('CONSUMER_KEY'),
    consumer_secret=secrets.get("CONSUMER_SECRET") if secrets else os.environ.get('CONSUMER_SECRET'),
    access_token=secrets.get("ACCESS_TOKEN") if secrets else os.environ.get('ACCESS_TOKEN'),
    access_token_secret=secrets.get("ACCESS_TOKEN_SECRET") if secrets else os.environ.get('ACCESS_TOKEN_SECRET'),
    wait_on_rate_limit=True
)

me = tweepy_client.get_me().data


def post_tweet(text, tweet_id = None):
    if tweet_id is None:
        return tweepy_client.create_tweet(
            text=text,
            # user_auth=True
        )
    tweepy_client.create_tweet(
        text=text,
        in_reply_to_tweet_id=tweet_id,
        # user_auth=True
    )


def create_thread():
    thread = make_openai_request("POST", "threads")
    return thread["id"]


def create_message(thread_id, content):
    message = make_openai_request("POST", f"threads/{thread_id}/messages", {
        "role": "user",
        "content": content
    })
    return message


def create_run(thread_id, asst_id):
    run = make_openai_request("POST", f"threads/{thread_id}/runs", {
        "assistant_id": asst_id,
    })
    return run


THREAD_ID = create_thread()


def create_reply_to_tweet(tweet_id, text, testing=True):
    random_length = random.randint(90, 400)
    create_message(THREAD_ID, f'Respond to this in around {random_length} characters: "{text}"')

    run = create_run(THREAD_ID, OPENAI_ASST_ID)
    while run["status"] != 'completed':
        # wait for 3 seconds
        time.sleep(3)
        run = make_openai_request("GET", f"threads/{THREAD_ID}/runs/{run['id']}")

    messages = make_openai_request("GET", f"threads/{THREAD_ID}/messages")
    try:
        reply = messages["data"][0]["content"][0]["text"]["value"]
        if reply[0] == '"':
            reply = reply[1:-1]
        if testing:
            print(reply)
        else:
            post_tweet(reply, tweet_id)
            tweet_history_collection.insert_one(
                {
                    "tweet_id": tweet_id,
                    "tweet_text": text,
                    "reply": reply,
                    "bot_id": bot_config["_id"]
                 }
            )
    except:
        print("Error in creating reply")


def create_tweet_on_timeline(testing=True):
    create_message(THREAD_ID, f"Give the world a though")
    run = create_run(THREAD_ID, OPENAI_ASST_ID)
    while run["status"] != 'completed':
        # wait for 3 seconds
        time.sleep(3)
        run = make_openai_request("GET", f"threads/{THREAD_ID}/runs/{run['id']}")

    messages = make_openai_request("GET", f"threads/{THREAD_ID}/messages")
    try:
        tweet = messages["data"][0]["content"][0]["text"]["value"]
        if testing:
            print(tweet)
        else:
            post_tweet(tweet)

    except:
        print("Error in creating reply")


def get_mentions():
    mentions = tweepy_client.get_users_mentions(me.id, user_auth=True, expansions="author_id",
                                                tweet_fields="public_metrics,conversation_id", max_results=25)
    possible_mentions = []

    # Check if the bot has already replied to the tweet
    for mention in mentions.data:
        if not tweet_history_collection.find_one({"tweet_id": mention.id, "bot_id": bot_config["_id"]}):
            possible_mentions.append(mention)

    # sample mentions
    ideal_sample_size = 3
    sample_size = min(ideal_sample_size, len(possible_mentions))
    random_mentions = random.sample(possible_mentions, sample_size)
    return random_mentions


def lambda_handler(event, context):
    # Get params from event
    testing = event.get("testing_flag", False)
    print("IS TESTING: ", testing)
    
    # Get top mentions
    mentions = get_mentions()
    for mention in mentions:
        print("Mentioned in tweet: ", mention.id)
        create_reply_to_tweet(mention.id, mention.text, testing=testing)

    # Create tweet on timeline
    # create_tweet_on_timeline(testing=testing)
