import checksumdir
import xxhash
import logging
import shutil
import requests

from pathlib import Path
from pydantic import HttpUrl
from email.message import EmailMessage
from collections.abc import Generator
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from app.core.models import LocalMod, RemoteMod


logger = logging.getLogger(__name__)





