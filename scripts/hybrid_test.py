import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import chromadb
from embedding.model import load_embeddings
from embedding.hybrid import HybridRetriever, tr_lower

soru = "Alttan dersim varken intörn yapabilir miyim?"
genis = sys.argv[1] if len(sys.argv) > 1 else ""

emb = load_embeddings()
col = chromadb.PersistentClient(path=str(BASE / "data" / "chroma_db")).get_collection("yonetmelikler")
ret = HybridRetriever(col, emb)

hedefler = {
    "devam zorunluluğu olan dersi": "MÜHENDİSLİK madde 10-b",
    "stajlarını tamamlamış": "TIP intörn tanımı",
}

for max_doc in (3, 10):
    hits = ret.search(soru, k=60, max_per_doc=max_doc, extra_queries=[genis] if genis else [])
    print(f"\nmax_per_doc={max_doc} (LLM'e giden: ilk 14)")
    for hedef, ad in hedefler.items():
        sira = [i + 1 for i, (_c, d, _m) in enumerate(hits) if hedef in tr_lower(" ".join(d.split()))]
        print(f"  {ad}: sıra {sira if sira else 'YOK'}")