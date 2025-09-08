import logging

from pydantic import HttpUrl
from pathlib import Path

from app.core.models import Manifest
from app.core.utils.utils import make_session, scan_mods


logger = logging.getLogger(__name__)

def get_manifest(manifest_url: HttpUrl) -> Manifest:
    with make_session() as session:
        resp = session.get(manifest_url)
    return Manifest.model_validate_json(resp.content)

def generate_manifest(mods_folder: Path) -> Manifest:
    