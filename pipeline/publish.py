"""Upload the mp4 (GitHub Release asset on a public repo, or S3-compatible storage
when S3_BUCKET is set) and save a Buffer draft. Never raises:
a publishing problem is reported but must not discard a rendered video."""
import json
import os
from datetime import datetime, timedelta, timezone

import requests

BUFFER_URL = "https://api.buffer.com"


def upload(mp4, key):
    import boto3
    from botocore.config import Config

    s3 = boto3.client(
        "s3", endpoint_url=os.environ["S3_ENDPOINT"], region_name="auto",
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4"))
    bucket = os.environ["S3_BUCKET"]
    s3.upload_file(str(mp4), bucket, key, ExtraArgs={"ContentType": "video/mp4"})
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    if base:
        return f"{base}/{key}"
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=7 * 24 * 3600)


def upload_release(mp4, key, keep_days=14):
    """Attach the video to a rolling 'videos' release; needs a public repo so Buffer can fetch it."""
    repo, tag = os.environ["GITHUB_REPOSITORY"], "videos"
    key = key.replace("/", "-")
    api = f"https://api.github.com/repos/{repo}"
    h = {"Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
         "Accept": "application/vnd.github+json"}
    r = requests.get(f"{api}/releases/tags/{tag}", headers=h, timeout=60)
    if r.status_code == 404:
        r = requests.post(f"{api}/releases", headers=h, timeout=60, json={
            "tag_name": tag, "name": "Rendered videos",
            "body": "Auto-generated videos (old ones are pruned)."})
    r.raise_for_status()
    rel = r.json()
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    for a in rel.get("assets", []):
        try:
            made = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
            if made < cutoff or a["name"] == key:
                requests.delete(f"{api}/releases/assets/{a['id']}", headers=h, timeout=60)
        except Exception:
            pass
    up = rel["upload_url"].split("{")[0]
    with open(mp4, "rb") as f:
        r = requests.post(up, params={"name": key}, data=f, timeout=300,
                          headers={**h, "Content-Type": "video/mp4"})
    r.raise_for_status()
    return r.json()["browser_download_url"]


def buffer_draft(text, video_url, channel_id, api_key):
    mutation = (
        "mutation { createPost(input: {"
        f" text: {json.dumps(text)}, channelId: {json.dumps(channel_id)},"
        " schedulingType: automatic, mode: addToQueue, saveToDraft: true,"
        f" assets: [{{ video: {{ url: {json.dumps(video_url)} }} }}]"
        " }) { __typename ... on PostActionSuccess { post { id } }"
        " ... on MutationError { message } } }")
    r = requests.post(BUFFER_URL, json={"query": mutation}, timeout=60, headers={
        "Authorization": "Bearer " + api_key, "Content-Type": "application/json"})
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"])[:400])
    result = body["data"]["createPost"]
    if "message" in result:
        raise RuntimeError(result["message"])
    return result["post"]["id"]


def publish(mp4, key, caption):
    out = {"url": None, "post_id": None, "error": None}
    try:
        out["url"] = upload(mp4, key) if os.environ.get("S3_BUCKET") else upload_release(mp4, key)
    except Exception as exc:
        out["error"] = f"upload failed: {type(exc).__name__}: {exc}"
        return out
    try:
        out["post_id"] = buffer_draft(
            caption, out["url"], os.environ["BUFFER_CHANNEL_ID"], os.environ["BUFFER_API_KEY"])
    except Exception as exc:
        out["error"] = f"buffer failed: {type(exc).__name__}: {exc}"
    return out
