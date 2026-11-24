"""
Akademik takvim: kullanıcı takvim sorusu sorduğunda resmî sayfadan güncel PDF'i çeker.
Takvimi indekse koymaz; PDF 24 saat önbellekte tutulur, soruyla ilgili bölümler seçilir.

Test:  python api/takvim.py "Mühendislik Fakültesi öğrencisiyim. Final tarihleri ne zaman?"
"""
import hashlib
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin

import pymupdf
import requests
from bs4 import BeautifulSoup

SAYFA = "https://erbakan.edu.tr/tr/akademik-takvim"
BASE_DIR = Path(__file__).resolve().parent.parent
ONBELLEK = BASE_DIR / "data" / "takvim_cache"
ONBELLEK_SURESI = 24 * 3600
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
BLOK = 1200          # karakter, takvim parçalarının boyutu
MAX_BAGLAM = 5500    # LLM'e gidecek en fazla karakter
GENEL = {"zaman", "tarih", "nedir", "hangi", "öğren", "kaçta", "ne"}  # ayırt edici olmayan kelimeler


def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def tokenize(text):
    return [w[:5] for w in re.findall(r"\w+", tr_lower(text)) if len(w) > 1]


def hedef_yil(bugun=None):
    b = bugun or date.today()
    bas = b.year if b.month >= 8 else b.year - 1
    return f"{bas}-{bas + 1}"


def _linkler():
    r = requests.get(SAYFA, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")
    sonuc = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if ".pdf" not in href.lower():
            continue
        tr = a.find_parent("tr")
        etiket = tr.get_text(" ", strip=True) if tr else a.get_text(" ", strip=True)
        m = re.search(r"(\d{4})\s*-\s*(\d{4})", etiket) or re.search(r"(\d{4})\s*-\s*(\d{4})", unquote(href))
        if m:
            sonuc.setdefault(f"{m.group(1)}-{m.group(2)}", urljoin(SAYFA, href))
    return sonuc


def _sayfa_metni(page):
    metin = page.get_text("text")
    satirlar = []
    try:
        for t in page.find_tables().tables:
            for row in t.extract():
                hucre = [" ".join((c or "").split()) for c in row]
                if any(hucre):
                    satirlar.append(" | ".join(hucre))
    except Exception:
        pass
    if satirlar:
        metin += "\n[TABLO SATIRLARI]\n" + "\n".join(satirlar)
    return metin


def _sayfalar(url):
    ONBELLEK.mkdir(parents=True, exist_ok=True)
    dosya = ONBELLEK / (hashlib.md5(url.encode()).hexdigest() + ".txt")
    if dosya.exists() and time.time() - dosya.stat().st_mtime < ONBELLEK_SURESI:
        return dosya.read_text(encoding="utf-8").split("\f")
    try:
        r = requests.get(url, headers=HEADERS, timeout=40)
        r.raise_for_status()
        sayfalar = []
        with pymupdf.open(stream=r.content, filetype="pdf") as doc:
            for i, page in enumerate(doc, 1):
                sayfalar.append(f"[Sayfa {i}]\n" + _sayfa_metni(page))
        dosya.write_text("\f".join(sayfalar), encoding="utf-8")
        return sayfalar
    except Exception as e:
        if dosya.exists():  # site kapalıysa eski önbelleği kullan
            print(f"[TAKVİM] indirilemedi ({e}), eski önbellek kullanılıyor")
            return dosya.read_text(encoding="utf-8").split("\f")
        raise


def _bloklar(sayfalar):
    bloklar = []
    for s in sayfalar:
        akim = ""
        for satir in s.splitlines():
            if akim and len(akim) + len(satir) > BLOK:
                bloklar.append(akim)
                akim = ""
            akim += satir + "\n"
        if akim.strip():
            bloklar.append(akim)
    return bloklar


def _sec(bloklar, soru):
    t = tr_lower(soru)
    ek = ""
    if "final" in t:
        ek += " genel sınav bütünleme"
    if "vize" in t:
        ek += " ara sınav"
    sorgu = {w for w in tokenize(soru + ek) if w not in GENEL}
    puanlar = sorted(((sum(1 for w in sorgu if w in set(tokenize(b))), -i) for i, b in enumerate(bloklar)),
                     reverse=True)
    secilen = {0}
    for _p, ni in puanlar[:2]:
        i = -ni
        secilen.update({i, i + 1})
    secilen = sorted(i for i in secilen if i < len(bloklar))
    metin = "\n".join(bloklar[i] for i in secilen)
    return metin[:MAX_BAGLAM]


def takvim_baglami(soru):
    """(metin, yıl, url) döner; takvim alınamazsa None."""
    try:
        linkler = _linkler()
        if not linkler:
            return None
        yil = hedef_yil()
        if yil not in linkler:
            yil = next(iter(linkler))
        url = linkler[yil]
        bloklar = _bloklar(_sayfalar(url))
        if not bloklar:
            return None
        return _sec(bloklar, soru), yil, url
    except Exception as e:
        print(f"[TAKVİM HATASI]: {e}")
        return None


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sonuc = takvim_baglami(" ".join(sys.argv[1:]))
    if not sonuc:
        print("Takvim alınamadı.")
    else:
        metin, yil, url = sonuc
        print(f"Yıl: {yil}\nURL: {url}\nSeçilen metin: {len(metin)} karakter\n")
        print(metin)