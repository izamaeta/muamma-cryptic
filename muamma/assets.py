import hashlib
from pathlib import Path

from flask import current_app

_versions: dict[str, str] = {}


def asset_version(filename: str) -> str | None:
    """Short content hash for a static file, or None if it is not there.

    Cached outside debug, where the files cannot change while the process
    runs. The hash is what makes a one year cache header safe: new content
    means a new address.
    """
    if not current_app.debug and filename in _versions:
        return _versions[filename]

    root = current_app.static_folder
    if not root:
        return None
    try:
        digest = hashlib.sha256((Path(root) / filename).read_bytes()).hexdigest()[:8]
    except OSError:
        return None

    _versions[filename] = digest
    return digest
