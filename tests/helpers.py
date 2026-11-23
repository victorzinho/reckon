import shutil
from pathlib import Path

_RESOURCES = Path(__file__).parent / 'resources'


def place(resource: str, path: Path) -> Path:
    """Copy tests/resources/<resource> to path, creating its directory, and return path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_RESOURCES / resource, path)
    return path
