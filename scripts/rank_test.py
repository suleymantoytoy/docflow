import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import chromadb
from embedding.model import load_embeddings
from embedding.hybrid import HybridRetriever, tr_lower

soru = "Alttan dersim varken intörn yapabilir miyim?"
genis = sys.argv[1] if len(sys.argv) > 1 else ""
SOZLUK = ("alttan ders, devam zorunluluğu olan ders, başarısız ders; "
          "intörn, işyeri eğitimi, işletmede mesleki eğitim, staj, uygulamalı eğitim")

emb = load_embeddings()
col = chromadb.PersistentClient(path=str(BASE / "data" / "chroma_db")).get_collection("yonetmelikler")
ret = HybridRetriever(col, emb)

hedefler = {
    "MÜHENDİSLİK 10-b": "devam zorunluluğu olan ders",
    "TIP intörn tanımı": "stajlarını tamamlamış",
}
varyantlar = {
    "A) sadece soru": [],
    "B) soru + LLM genişletme": [genis] if genis else [],
    "C) soru + sözlük": [SOZLUK],
    "D) soru + LLM + sözlük": [x for x in (genis, SOZLUK) if x],
}

for ad, ekstra in varyantlar.items():
    hits = ret.search(soru, k=100, pool=150, max_per_doc=3, extra_queries=ekstra)
    print(f"\n{ad}")
    for h_ad, h in hedefler.items():
        bulunan = []
        for i, (_c, d, m) in enumerate(hits):
            if h in tr_lower(" ".join(d.split())):
                bulunan.append(f"{i+1}:{m.get('source_file', '?')[:25]}")
        print(f"  {h_ad}: {bulunan if bulunan else 'YOK'}")