import json
from anki.httpclient import HttpClient

DEFAULT_SERVER = "https://raw.githubusercontent.com/Alexander-Nilsson/dictionaries/main"


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
        # Use a 30s timeout to accommodate slower connections
        resp = client.session.get(index_url, timeout=30, stream=True)
    except Exception:
        return None

    if resp.status_code != 200:
        return None

    # Manually stream content to ensure it doesn't hang indefinitely
    data = b""
    for chunk in resp.iter_content(chunk_size=16384):
        if chunk:
            data += chunk
            
    return json.loads(data.decode("utf-8-sig"))
