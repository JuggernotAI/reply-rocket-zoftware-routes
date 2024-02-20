from flask import Flask, jsonify, request, session, redirect
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv
import requests
import linkedin_helper
import twitter_helper

load_dotenv()
app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SESSION_SECRET")

UPLOAD_FOLDER = "./temp"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET"])
def index():
    return jsonify({"data": "Success", "status": 200}), 200


@app.route("/getme", methods=["GET"])
def getme():
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or "Bearer " not in auth_header:
            return jsonify({"error": "Bearer token not found in request headers"}), 401

        access_token = auth_header.split(" ")[1]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)

        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch user info"}), response.status_code

        user_info = response.json()
        return jsonify(user_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/me", methods=["GET"])
def get_twitter_me():
    try:
        access_token = request.args.get("access_token")
        access_secret = request.args.get("access_secret")
        data = twitter_helper.get_me(access_token, access_secret)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/users", methods=["GET"])
def get_users():
    try:
        users = twitter_helper.get_users(["101584084", "3888491"])
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# text-only post
@app.route("/post", methods=["POST"])
def makepost():
    access_token = request.json.get("access_token")
    linkedin_id = request.json.get("linkedin_id")
    post_content = request.json.get("content")

    if not all([access_token, linkedin_id, post_content]):
        return jsonify({"error": "Missing required parameters"}), 400
    try:
        post_response = linkedin_helper.create_linkedin_post(
            access_token, linkedin_id, post_content
        )
        return jsonify(post_response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# text+image post
@app.route("/upload", methods=["POST"])
def upload_file():
    if request.method == "POST":
        try:
            access_token = request.form.get("access_token")
            linkedin_id = request.form.get("linkedin_id")
            post_content = request.form.get("content")

            if not all([access_token, linkedin_id, post_content]):
                return jsonify({"error": "Missing required parameters"}), 400

            asset_id = None
            if "file" in request.files:
                file = request.files["file"]
                if file.filename == "":
                    return jsonify({"message": "No selected file"}), 400
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                else:
                    return jsonify({"message": "File type not allowed"}), 400

                response = linkedin_helper.register_image(access_token, linkedin_id)
                upload_url = response["value"]["uploadMechanism"][
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                ]["uploadUrl"]
                asset_id = response["value"]["asset"]
                linkedin_helper.uploadImage(
                    upload_url,
                    access_token,
                    os.path.join(app.config["UPLOAD_FOLDER"], filename),
                )

            if asset_id is not None:
                post_response = linkedin_helper.create_linkedin_post_image(
                    access_token, linkedin_id, post_content, asset_id
                )
            else:
                post_response = linkedin_helper.create_linkedin_post(
                    access_token, linkedin_id, post_content
                )
                print(post_response)
            return jsonify(post_response), 200
        except Exception as e:
            return jsonify(e), 500


@app.route("/twitter/timeline", methods=["GET"])
def fetch_twitter_timeline():
    try:
        access_token = "1717841543694778368-ckYjlVB9yM6cWfJ3W8WBUM7MkvEV26"
        access_secret = "sIn285wQXoyUBB22olwnyBTJTJYVzvivSCTVsh4fMghJf"
        timeline = twitter_helper.get_home_timeline(access_token, access_secret)
        timeline = timeline[0]
        tweets_list = [
            {
                "id": tweet.id,
                "text": tweet.text,
                "created_at": tweet.created_at,
                "author_id": tweet.author_id,
            }
            for tweet in timeline
        ]
        return jsonify(tweets_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/post", methods=["POST"])
def post_tweet():
    try:
        form_data = request.form
        text = form_data.get("text")
        if not text:
            return jsonify({"error": "Missing required parameter: text"}), 400
        path = None
        if "image" in request.files:
            file = request.files["image"]
            if file.filename == "":
                return jsonify({"message": "No selected file"}), 400
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            else:
                return jsonify({"message": "File type not allowed"}), 400
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

        data = twitter_helper.post_tweet(
            text, session["access_token"], session["access_secret"], path
        )
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/reply", methods=["POST"])
def reply_tweet():
    try:
        tweet_id = request.form.get("tweet_id")
        text = request.form.get("reply")
        access_token = request.form.get("access_token")
        access_secret = request.form.get("access_secret")
        if not all([tweet_id, text]):
            return jsonify({"error": "Missing required parameters"}), 500
        data = twitter_helper.reply_tweet(tweet_id, text, access_token, access_secret)
        if "error" in data.keys():
            return jsonify(data), 500
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/replyall", methods=["POST"])
def reply_all():
    try:
        replies = request.json.get("replies")
        access_token = request.json.get("access_token")
        access_secret = request.json.get("access_secret")
        if not replies:
            return jsonify({"error": "Missing required parameter: replies"}), 500
        data = twitter_helper.reply_all(replies, access_token, access_secret)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/twitter/gpt", methods=["GET"])
def gpt_call():
    try:
        access_token = request.args.get("access_token")
        access_secret = request.args.get("access_secret")
        timeline = twitter_helper.get_home_timeline(access_token, access_secret)
        author_ids = list(set([tweet.author_id for tweet in timeline]))
        users = twitter_helper.get_users(author_ids)
        # tweets_list = [
        #     {
        #         "id": tweet.id,
        #         "text": tweet.text,
        #         "created_at": tweet.created_at,
        #         "author_id": tweet.author_id,
        #     }
        #     for tweet in timeline
        # ]
        tweets_list = list()
        for tweet in timeline:
            user = [user for user in users if str(user["id"]) == str(tweet.author_id)][
                0
            ]
            temp_data = dict()
            temp_data["id"] = str(tweet.id)
            temp_data["text"] = tweet.text
            temp_data["created_at"] = tweet.created_at
            temp_data["author_id"] = tweet.author_id
            temp_data["username"] = user["username"]
            temp_data["profile_image_url"] = user["profile_image_url"]
            temp_data["verified"] = user["verified"]
            temp_data["name"] = user["name"]
            tweets_list.append(temp_data)
        data = twitter_helper.send_to_gpt(tweets_list)
        return jsonify(data)
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/oauth/twitter")
def oauth():
    try:
        data = twitter_helper.oauth()
        if "error" in data.keys():
            return jsonify(data), 500
        session["request_token"] = data["request_token"]
        return redirect(data["redirect_url"])
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/oauth/callback/twitter")
def callback():
    request_token = session.pop("request_token", None)
    verifier = request.args.get("oauth_verifier")
    if request_token is None or verifier is None:
        return "Access denied: reason=missing token or verifier."
    try:
        data = twitter_helper.callback(request_token, verifier)
        if "error" in data.keys():
            return jsonify(data), 500
        session["access_token"] = data["access_token"]
        session["access_secret"] = data["access_secret"]
        user_data = twitter_helper.get_me(data["access_token"], data["access_secret"])
        username = user_data["username"]
        name = user_data["name"]
        profile_pic = user_data["profile_pic"]
        frontend_url = os.getenv("FRONTEND_URL")
        return redirect(
            frontend_url
            + "/save?access_token="
            + data["access_token"]
            + "&access_secret="
            + data["access_secret"]
            + "&username="
            + username
            + "&name="
            + name
            + "&profile_pic="
            + profile_pic
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
