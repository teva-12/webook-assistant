import webbrowser
from urllib.parse import urlparse


def open_event_page(url: str) -> bool:
    parsed_url = urlparse(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in {"webook.com", "www.webook.com"}
    ):
        raise ValueError("Only official Webook HTTPS URLs are allowed.")

    return webbrowser.open(url, new=2)