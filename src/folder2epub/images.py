from pathlib import Path
from natsort import natsorted

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"
}


def find_images(folder: Path) -> list[Path]:
    files = [
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return list(natsorted(files, key=lambda p: p.name.lower()))
