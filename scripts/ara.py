import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "parsed_documents"


def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def main():
    args = sys.argv[1:]
    belge_filtre = None
    if args and args[0].startswith("--belge="):
        belge_filtre = tr_lower(args[0].split("=", 1)[1])
        args = args[1:]
    if not args:
        print('Kullanım: python scripts/ara.py --belge="lisans yönetmeliği" "tek ders"')
        return

    belgeler = []
    for p in BASE.glob("*.json"):
        if belge_filtre and belge_filtre not in tr_lower(p.stem):
            continue
        with open(p, encoding="utf-8") as f:
            belgeler.append((p.stem, " ".join(json.load(f).get("text", "").split())))

    print(f"Taranan doküman sayısı: {len(belgeler)}")
    limit = 5 if belge_filtre else 3

    for terim in args:
        t = tr_lower(terim)
        print("=" * 60)
        print(f"ARANAN: {terim}")
        bulunan = 0
        for ad, metin in belgeler:
            kucuk = tr_lower(metin)
            i = kucuk.find(t)
            while i != -1 and bulunan < limit:
                bulunan += 1
                parca = " ".join(metin[max(0, i - 150): i + 300].split())
                print(f"\n[{ad[:60]}]\n...{parca}...")
                i = kucuk.find(t, i + 400) if belge_filtre else -1
        print(f"\n→ Gösterilen eşleşme: {bulunan}\n")


if __name__ == "__main__":
    main()