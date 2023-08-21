from pathlib import Path
import os
import argparse
import urllib
import requests
import json
from bs4 import BeautifulSoup
import moviepy.editor as mpe
import time
from tqdm import tqdm
from dotenv import load_dotenv


def main(episode_url):
    try:
        default_ua = "Chrome/51.0.2704.103 Safari/537.36"
        userTokenUrl = episode_url
        res = requests.get(url=userTokenUrl, headers={"User-Agent": os.getenv("USER_AGENT", default_ua)})
        cookies = ""
        for c in res.headers["Set-Cookie"].split(";"):
            if "sp_t" in c:
                cookies += c + ";"
        cookies += f" sp_dc={os.getenv('SP_DC_COOKIE')};"

        userTokenHeaders = {
            "Cookie": cookies,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": os.getenv("USER_AGENT", default_ua),
        }

        userTokenResponse = requests.get(userTokenUrl, headers=userTokenHeaders)
        userTokenResponse.raise_for_status()

        parsed_html = BeautifulSoup(userTokenResponse.text, features="html.parser")
        userTokenJSON = parsed_html.body.find("script", attrs={"id": "session", "data-testid": "session"}).contents[0]
        title = parsed_html.head.find("title").contents[0].split("|")[0].strip()

        Path(f"{title}").mkdir(parents=True, exist_ok=True)
        print(title)
        userToken = json.loads(userTokenJSON)["accessToken"]

        clientTokenUrl = "https://clienttoken.spotify.com/v1/clienttoken"
        ClientTokenHeaders = {
            "User-Agent": os.getenv("USER_AGENT", default_ua),
            "Host": "clienttoken.spotify.com",
            "Connection": "keep-alive",
            "Content-Length": "280",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://open.spotify.com",
            "Referer": "https://open.spotify.com/",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
        clientTokenData = {
            "client_data": {
                "client_version": "1.2.17.626.gb271f477",
                "client_id": os.getenv("CLIENT_ID"),
                "js_sdk_data": {
                    "device_brand": "Apple",
                    "device_model": "unknown",
                    "os": "macos",
                    "os_version": "10.15.7",
                    "device_id": os.getenv("DEVICE_ID"),
                    "device_type": "computer",
                },
            }
        }

        clientTokenResponse = requests.post(
            clientTokenUrl, data=json.dumps(clientTokenData), headers=ClientTokenHeaders
        )
        clientTokenResponse.raise_for_status()

        clientToken = clientTokenResponse.json()["granted_token"]["token"]
        supports_drm = f"https://gew4-spclient.spotify.com/manifests/v7/json/sources/{os.getenv('DRM_SOURCE')}/options/supports_drm"

        drm_headers = {
            "Accept": "*/*",
            "Origin": "https://open.spotify.com",
            "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}",
            "Referer": "https://open.spotify.com/",
            "Accept-Language": "en-GB,en;q=0.9",
            "Host": "gew4-spclient.spotify.com",
            "User-Agent": os.getenv("USER_AGENT", default_ua),
            "Accept-Encoding": "application/json",
            "Connection": "keep-alive",
            "client-token": f"{clientToken}",
            "Priority": "u=3, i",
        }

        drm_response = requests.get(supports_drm, headers=drm_headers)
        drm_response.raise_for_status()
        drm_data = drm_response.json()

        end_time_millis = drm_data["contents"][0]["end_time_millis"]
        segment_length = drm_data["contents"][0]["segment_length"]

        i = 0
        videoProfile = {"{{profile_id}}": "0", "{{file_type}}": "ts"}
        audioProfile = {"{{profile_id}}": "9", "{{file_type}}": "ts"}

        url = drm_data["base_urls"][0]
        videoURL, audioURL = drm_data["segment_template"], drm_data["segment_template"]

        for key, value in videoProfile.items():
            videoURL = videoURL.replace(key, value)

        for key, value in audioProfile.items():
            audioURL = audioURL.replace(key, value)

        with tqdm(total=int(end_time_millis / 1000), unit="segments") as pbar:
            i = 0
            while i * segment_length < int(end_time_millis / 1000):
                videoResponse = requests.get(url + videoURL.replace("{{segment_timestamp}}", str(i * segment_length)))
                audioResponse = requests.get(url + audioURL.replace("{{segment_timestamp}}", str(i * segment_length)))
                videoResponse.raise_for_status()
                audioResponse.raise_for_status()
                open(f"{title}/video_segment_{i * segment_length}.ts", "wb").write(videoResponse.content)
                open(f"{title}/audio_segment_{i * segment_length}.ts", "wb").write(audioResponse.content)

                i += 1
                pbar.update(segment_length)

    except requests.exceptions.RequestException as e:
        print(str(e))
        if e.response is not None:
            print(e.response.text)


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description="Download spotify video podcasts.")
    parser.add_argument("link", type=str, help="spotify episode link from web")

    args = parser.parse_args()

    main(args.link)
