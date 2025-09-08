import logging
import requests

from pathlib import Path
from pydantic import HttpUrl
from email.message import EmailMessage
from requests.adapters import HTTPAdapter
from urllib3 import Retry


logger = logging.getLogger(__name__)

def download_file(url: HttpUrl, destination: Path, session: requests.Session) -> Path:
    with session.get(url, stream=True) as r:
        r.raise_for_status()

        msg = EmailMessage()
        msg["Content-Disposition"] = r.headers["Content-Disposition"]
        filename = msg.get_filename()
        
        path = destination / filename
        
        with open(path, "wb") as file:
            file.write(r.content)
    logger.info(f"{filename} downloaded") 
    return path

def make_session() -> requests.Session:
    session = requests.Session()
    
    retries = Retry(
        total=5,
        connect=5,      
        read=5,
        backoff_factor=0.5,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset(["HEAD","GET"])
    )
    
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    return session