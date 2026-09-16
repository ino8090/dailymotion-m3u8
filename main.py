import os
from pathlib import Path

import requests


API_BASE = "https://api.dailymotion.com"
TOKEN_URL = "https://oauth2.dailymotion.com/v2/token"
OUTPUT_FILE = Path("playlist.m3u")


def get_access_token():
    client_id = os.environ["DAILYMOTION_CLIENT_ID"]
    client_secret = os.environ["DAILYMOTION_CLIENT_SECRET"]

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "scope": "video.read",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if "access_token" not in data:
        raise RuntimeError("Access token alınamadı.")

    return data["access_token"]


def get_profile_videos(profile_id, token):
    videos = []
    page = 1

    while True:
        response = requests.get(
            f"{API_BASE}/v2/profiles/{profile_id}/videos",
            headers={
                "Authorization": f"Bearer {token}"
            },
            params={
                "page": page,
                "page_size": 100,
                "fields": "video_id,title,video_url",
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        for video in data.get("list", []):
            videos.append(video)

        if not data.get("has_more"):
            break

        page += 1

    return videos


def get_hls_url(video_id, token):
    response = requests.post(
        f"{API_BASE}/v2/videos/{video_id}/streams",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "protocol": "hls"
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    for stream in data.get("stream_urls", []):
        if stream.get("protocol") == "hls":
            url = stream.get("stream_url")

            if url:
                return url

    return None


def create_m3u(videos, token):
    lines = ["#EXTM3U"]

    for video in videos:
        video_id = video.get("video_id")
        title = video.get("title") or video_id

        print(f"[+] {title} ({video_id})")

        try:
            hls_url = get_hls_url(
                video_id,
                token
            )

            if not hls_url:
                print(
                    f"[!] HLS bulunamadı: {video_id}"
                )
                continue

            lines.append(
                f"#EXTINF:-1,{title}"
            )

            lines.append(hls_url)

        except Exception as error:
            print(
                f"[!] {video_id} hata: {error}"
            )

    OUTPUT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    print(
        f"[+] Playlist oluşturuldu: "
        f"{OUTPUT_FILE}"
    )


def main():
    profile_id = os.environ.get(
        "DAILYMOTION_PROFILE_ID"
    )

    if not profile_id:
        raise RuntimeError(
            "DAILYMOTION_PROFILE_ID ayarlanmamış."
        )

    print("[*] Access token alınıyor...")

    token = get_access_token()

    print("[*] Profil videoları alınıyor...")

    videos = get_profile_videos(
        profile_id,
        token
    )

    print(
        f"[+] {len(videos)} video bulundu."
    )

    print("[*] M3U oluşturuluyor...")

    create_m3u(
        videos,
        token
    )


if __name__ == "__main__":
    main()
