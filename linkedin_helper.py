import requests
import json
from mimetypes import guess_type


def create_linkedin_post(access_token, linkedin_id, content):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    post_data = {
        "author": f"urn:li:person:{linkedin_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_data,
        timeout=10000,
    )
    if response.status_code != 201:
        raise Exception(f"LinkedIn API Error: {response.json()}")
    print(response.json())
    return response.json()


def register_image(access_token, linkedin_id):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": f"urn:li:person:{linkedin_id}",
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent",
                }
            ],
        }
    }

    response = requests.post(
        "https://api.linkedin.com/v2/assets?action=registerUpload",
        headers=headers,
        json=body,
        timeout=10000,
    )

    if response.status_code != 200:
        raise Exception(f"LinkedIn Image Register API Error: {response.json()}")

    return response.json()


def uploadImage(upload_url, access_token, path):
    headers = {
        "X-Restli-Protocol-Version": "2.0.0",
        "Authorization": f"Bearer {access_token}",
    }

    content_type = guess_type(path)[0]
    with open(path, "rb") as image:
        files = {"file": (path, image, content_type)}
        response = requests.post(
            upload_url, headers=headers, files=files, timeout=10000
        )
        if response.status_code != 201:
            raise Exception(
                f"LinkedIn Image Register API Error: {response.status_code()}"
            )
        print(response.status_code)


def create_linkedin_post_image(access_token, linkedin_id, content, asset_id):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    post_data = {
        "author": f"urn:li:person:{linkedin_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": content},
                "shareMediaCategory": "IMAGE",
                "media": [
                    {
                        "status": "READY",
                        "description": {"text": "Center stage!"},
                        "media": asset_id,
                        "title": {"text": content},
                    }
                ],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    response = requests.post(
        "https://api.linkedin.com/v2/ugcPosts",
        headers=headers,
        json=post_data,
        timeout=10000,
    )
    if response.status_code != 201:
        raise Exception(f"LinkedIn API Error: {response.json()}")

    posted_url = {
        "url": f'https://www.linkedin.com/feed/update/{response.json()["id"]}'
    }
    return posted_url
