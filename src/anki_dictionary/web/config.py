import json

from anki.httpclient import HttpClient

from ..utils.common import prefer_ipv4

DEFAULT_SERVER = "https://github.com/Alexander-Nilsson/dictionaries/raw/main"


def normalize_url(url):
    if not url.startswith("http"):
        url = "http://" + url
    while url.endswith("/"):
        url = url[:-1]
    return url


def download_index(server_url=DEFAULT_SERVER):
    server_url = normalize_url(server_url)

    index_url = server_url + "/index.json"

    client = HttpClient()
    try:
        # Use a 15s timeout to avoid long UI hangs
        with prefer_ipv4():
            resp = client.session.get(index_url, timeout=15, stream=True)  # ty:ignore[unresolved-attribute]
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    # Manually stream content to ensure it doesn't hang indefinitely
    chunks = []
    for chunk in resp.iter_content(chunk_size=16384):
        if chunk:
            chunks.append(chunk)

    data = b"".join(chunks)
    return json.loads(data.decode("utf-8-sig"))
