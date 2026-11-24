"""
Hafta 1 - Toplu doküman indirme scripti.

Bu scripti KENDİ BİLGİSAYARINDA çalıştır (Claude'un sandbox'ı dış
sitelere erişemiyor). data/kaynak_listesi.json içindeki URL'leri
data/raw_documents/ klasörüne indirir.

Kullanım:
    pip install requests
    python scripts/download_documents.py
"""
import json
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_LIST = BASE_DIR / "data" / "kaynak_listesi.json"
OUTPUT_DIR = BASE_DIR / "data" / "raw_documents"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    return unquote(Path(path).name)


def download_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = json.loads(SOURCE_LIST.read_text(encoding="utf-8"))

    ok, failed = 0, []
    for item in sources:
        url = item["url"]
        fname = filename_from_url(url)
        out_path = OUTPUT_DIR / fname

        if out_path.exists():
            print(f"[atlandı - zaten var] {fname}")
            ok += 1
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            out_path.write_bytes(resp.content)
            print(f"[OK] {fname}  ({item['birim']} — {item['belge']})")
            ok += 1
        except Exception as e:
            print(f"[HATA] {url} -> {e}")
            failed.append(url)

        time.sleep(0.5)  # kibarca rate-limit

    print(f"\nToplam: {ok}/{len(sources)} başarılı.")
    if failed:
        print("Başarısız olanlar:")
        for u in failed:
            print(" -", u)


if __name__ == "__main__":
    download_all()
