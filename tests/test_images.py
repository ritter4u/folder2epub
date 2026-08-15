from pathlib import Path

from folder2epub.images import find_images


def test_natural_sort(tmp_path: Path):
    for name in ["10.jpg", "2.jpg", "1.jpg", "note.txt"]:
        (tmp_path / name).write_bytes(b"x")

    result = [p.name for p in find_images(tmp_path)]
    assert result == ["1.jpg", "2.jpg", "10.jpg"]
