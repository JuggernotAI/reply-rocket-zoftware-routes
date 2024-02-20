import tweepy
import os
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import requests

load_dotenv()

consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")

gpt_client = OpenAI(api_key=os.getenv("OPEN_AI_KEY"))

authenticator = tweepy.OAuthHandler(
    consumer_key,
    consumer_secret,
    callback=os.getenv("CALLBACK_URL"),
)

api_url = "https://api.twitter.com/2/users?user.fields=profile_image_url,verified&ids="

# access_token = os.getenv("access_token")
# access_token_secret = os.getenv("access_secret")


def init(access_token, access_token_secret):
    auth = tweepy.OAuth1UserHandler(
        consumer_key, consumer_secret, access_token, access_token_secret
    )

    api = tweepy.API(auth)

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    return api, client


def get_home_timeline_through_api_call(Bearer):
    api_url = "https://api.twitter.com/2/tweets/search/recent?query=from:twitterdev"


def get_home_timeline(access_token, access_token_secret):
    api, client = init(access_token, access_token_secret)
    response = client.get_home_timeline(
        exclude=["replies", "retweets"],
        tweet_fields=["created_at", "author_id"],
        user_fields=["username", "profile_image_url", "verified"],
    )
    return response.data


def get_users(user_ids):
    headers = {"Authorization": f"Bearer {os.getenv('bearer_token')}"}
    response = requests.get(
        api_url + ",".join(str(u) for u in user_ids), headers=headers
    )

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()["data"]


def get_me(access_token, access_token_secret):
    api, client = init(access_token, access_token_secret)
    user = client.get_me(user_fields=["profile_image_url"])
    user_profile_pic = user.data.profile_image_url
    data = {
        "profile_pic": user_profile_pic,
        "username": user.data.username,
        "name": user.data.name,
    }
    return data


def post_tweet(text, access_token, access_secret, path=None):
    api, client = init(access_token, access_secret)
    if path:
        media = api.media_upload(path)
        data = client.create_tweet(text=text, media_ids=[media.media_id])
    else:
        data = client.create_tweet(text=text)
    return data


def reply_tweet(tweet_id, text, access_token, access_secret):
    try:
        api, client = init(access_token, access_secret)
        data = client.create_tweet(text=text, in_reply_to_tweet_id=tweet_id)
        return data.data
    except Exception as e:
        return {"error": "Something went wrong"}


def reply_all(tweets, access_token, access_secret):
    try:
        api, client = init(access_token, access_secret)
        for tweet in tweets:
            client.create_tweet(
                text=tweet["reply"], in_reply_to_tweet_id=tweet["tweet_id"]
            )
        return {"success": True}
    except Exception as e:
        return {"error": "Something went wrong"}


def get_profile_details(user_ids, access_token, access_secret):
    api, client = init(access_token, access_secret)
    response = client.get_users(ids=user_ids)
    return response.data


def send_to_gpt(tweets):
    replies = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_tweet = {
            executor.submit(send_request, tweet): tweet for tweet in tweets
        }
        for future in as_completed(future_to_tweet):
            result = future.result()
            if result:
                print(result["tweet_id"])
                replies.append(result)
    return replies


def send_request(tweet):
    LLM_INITIAL_INSTRUCTIONS = [
        {
            "role": "user",
            "content": f"""Craft a thoughtful and engaging response to the following tweet(max 200 chars), expressing your genuine thoughts and feelings on the topic. Respond with wit and a unique perspective, ensuring humor is subtle and used sparingly. Provide clear, informative replies to necessary tweets. Adjust the tone according to the context of the tweet. Keep responses concise and relevant. Avoid using common, overused words such as 'wow,' 'amazing,' or 'incredible.' Instead, focus on providing meaningful commentary or sharing a personal perspective. Do not use word "reply" at the beginning of reply. just answer with a reply tweet. Make sure your reply does not acceed 200 character limit.

                        Tweet:
                        {tweet['text']}""",
        },
        {
            "role": "system",
            "content": f"""Generate a friendly and contextually relevant reply to the provided tweet. Ensure that the response is in a conversational tone and appears as a natural and informal, human reply. Additionally, after providing the reply, share your own views or opinions on the tweet. Please keep both the reply and your views concise. Make sure your reply does not acceed 200 character limit.""",
        },
    ]
    try:
        response = gpt_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=LLM_INITIAL_INSTRUCTIONS,
            max_tokens=70,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        return {
            "tweet_id": tweet["id"],
            "tweet": tweet["text"],
            "reply": reply,
            "username": tweet["username"],
            "profile_image_url": tweet["profile_image_url"],
            "verified": tweet["verified"],
            "name": tweet["name"],
        }
    except Exception as e:
        print(e)
        return None


def oauth():
    try:
        redirect_url = authenticator.get_authorization_url()
        request_token = authenticator.request_token
        return {"request_token": request_token, "redirect_url": redirect_url}
    except Exception as e:
        return {"error": str(e)}


def callback(request_token, verifier):
    try:
        authenticator.request_token = request_token
        access_info = authenticator.get_access_token(verifier)
        access_token = access_info[0]
        access_secret = access_info[1]
        return {"access_token": access_token, "access_secret": access_secret}
    except Exception as e:
        return {"error": str(e)}
