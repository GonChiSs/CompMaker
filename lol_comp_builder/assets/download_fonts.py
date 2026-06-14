from __future__ import annotations

import os
import urllib.request
from pathlib import Path


FONTS = {
    "BarlowCondensed-Regular.ttf": "https://github.com/jpt/barlow/raw/master/fonts/ttf/BarlowCondensed-Regular.ttf",
    "BarlowCondensed-Bold.ttf": "https://github.com/jpt/barlow/raw/master/fonts/ttf/BarlowCondensed-Bold.ttf",
    "BarlowCondensed-ExtraBold.ttf": "https://github.com/jpt/barlow/raw/master/fonts/ttf/BarlowCondensed-ExtraBold.ttf",
    "JetBrainsMono-Regular.ttf": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Bold.ttf": "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Bold.ttf",
    "Cinzel[wght].ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf",
}


def main() -> None:
    fonts_dir = Path(__file__).resolve().parent / "fonts"
    os.makedirs(fonts_dir, exist_ok=True)
    for name, url in FONTS.items():
        path = fonts_dir / name
        if path.exists():
            continue
        print(f"Downloading {name}...")
        urllib.request.urlretrieve(url, path)
        print(f"  OK {name}")


if __name__ == "__main__":
    main()
