import checksumdir
import xxhash
import logging

from pathlib import Path


logger = logging.getLogger(__name__)


def hashdir(path: Path) -> str:
    hashvalues = []
    
    for root, _, files in path.walk():
        for file in files:
            hashvalues.append(checksumdir._filehash(root / file, xxhash.xxh3_64))
    
    hashvalues.sort()
    
    return checksumdir._reduce_hash(hashvalues, xxhash.xxh3_64)