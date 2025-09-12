from __future__ import annotations
from pydantic import SecretStr
import argparse
import logging
import json
import mimetypes
import os
from pathlib import Path
from typing import List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel, Field, ConfigDict, HttpUrl

from app.core.models import LocalMod, RemoteMod, Manifest


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]

def upload_google_drive(mods: list[LocalMod], token: SecretStr) -> list[RemoteMod]:
    pass


# --- Google Drive helpers ---



def authenticate_service_account(sa_keyfile: str):
    """Аутентификация через service account JSON-key.
    Возвращает объект service для Drive API.
    """
    creds = service_account.Credentials.from_service_account_file(sa_keyfile, scopes=SCOPES)
    service = build("drive", "v3", credentials=creds)
    return service


def upload_file_to_folder(service, file_path: Path, folder_id: str) -> dict:
    """Загружает файл в папку Drive. Возвращает dict с метаданными файла.

    Результат содержит минимум: id, name, webViewLink, mimeType
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    file_metadata = {
        "name": file_path.name,
        "parents": [folder_id],
    }

    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
    uploaded = service.files().create(body=file_metadata, media_body=media, fields="id,name,mimeType,webViewLink,webContentLink").execute()

    file_id = uploaded.get("id")

    # Делаем доступ по ссылке: anyoneWithLink
    try:
        service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()
    except Exception as e:
        # permission could fail in some org settings; warn but continue
        print(f"Warning: cannot set public permission for {file_path.name}: {e}")

    # Получим обновлённые поля
    result = service.files().get(fileId=file_id, fields="id,name,mimeType,webViewLink,webContentLink").execute()
    return result


# --- Mod uploader + manifest generator ---

def upload_mods_and_generate_manifest(
    sa_keyfile: str,
    folder_id: str,
    local_mod_paths: List[Path],
    out_manifest_path: Optional[Path] = None,
) -> Manifest:
    service = authenticate_service_account(sa_keyfile)

    remote_mods: List[RemoteMod] = []

    for p in local_mod_paths:
        p = Path(p)
        if p.is_dir():
            # если передана папка — найдём файлы внутри (архивы и т.д.)
            # берем все файлы в корне папки
            candidates = sorted([x for x in p.iterdir() if x.is_file()])
            if not candidates:
                print(f"Dir {p} is empty, skipping")
                continue
            for c in candidates:
                print(f"Uploading {c}...")
                info = upload_file_to_folder(service, c, folder_id)
                url = info.get("webViewLink") or info.get("webContentLink")
                # Создаём мод. Предполагаем, что имя файла является name мода, id — id от Drive
                remote = RemoteMod(name=c.stem, id=info["id"], mod_hash="", mod_url=url)
                remote_mods.append(remote)
        elif p.is_file():
            print(f"Uploading {p}...")
            info = upload_file_to_folder(service, p, folder_id)
            url = info.get("webViewLink") or info.get("webContentLink")
            remote = RemoteMod(name=p.stem, id=info["id"], mod_hash="", mod_url=url)
            remote_mods.append(remote)
        else:
            print(f"Path {p} not found, skipping")

    manifest = Manifest(mods=remote_mods)

    if out_manifest_path:
        with open(out_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.model_dump(), f, ensure_ascii=False, indent=2)
        print(f"Manifest saved to {out_manifest_path}")

    return manifest


# --- CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload mods to Google Drive and generate manifest.json")
    parser.add_argument("--service-account", required=True, help="Path to service account JSON key")
    parser.add_argument("--folder-id", required=True, help="Drive folder ID where to upload")
    parser.add_argument("--out", default="manifest.json", help="Output manifest file path")
    parser.add_argument("paths", nargs="+", help="Paths to local mod files or directories")

    args = parser.parse_args()

    # Normalize paths
    paths = [Path(p) for p in args.paths]

    manifest = upload_mods_and_generate_manifest(
        sa_keyfile=args.service_account,
        folder_id=args.folder_id,
        local_mod_paths=paths,
        out_manifest_path=Path(args.out),
    )

    # Короткий вывод
    print("Uploaded mods:")
    for m in manifest.mods:
        print(f" - {m.name}: {m.mod_url}")
