"""Copia i file iniziali (archivio, tracker) in DATA_DIR se non esistono ancora.
Utile al primo avvio su Render con un Disk vuoto: `python seed_data.py`."""
import os, shutil
from pathlib import Path

src = Path(__file__).parent / "data"
dst = Path(os.environ.get("DATA_DIR", src))
dst.mkdir(parents=True, exist_ok=True)
for f in src.iterdir():
    if f.is_file() and not (dst / f.name).exists():
        shutil.copy(f, dst / f.name)
        print("copiato", f.name)
