from httpx import Response
from urllib.parse import urlparse


def id_from_location(response: Response) -> str:

    location = response.headers["Location"]
    parsed = urlparse(location)
    
    uid = parsed.path.rstrip("/").split("/")[-1]

    return uid