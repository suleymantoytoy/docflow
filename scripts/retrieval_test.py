import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import chromadb
from embedding.model import load_embeddings, embed_query

args = sys.argv[1:]
kelime = None
if args and args[0].startswith("--kelime="):
    kelime = args[0].split("=", 1)[1].lower()
    args = args[1:]
soru = " ".join(args)

N = 50
emb = load_embeddings()
col = chromadb.PersistentClient(path=str(BASE / "data" / "chroma_db")).get_collection("yonetmelikler")
r = col.query(query_embeddings=[embed_query(emb, soru)], n_results=N)

print("\nİlk 10 sonuç:")
for i in range(10):
    meta = r["metadatas"][0][i]
    print(f"[{i+1}] mesafe={r['distances'][0][i]:.3f} | {meta.get('source_file', '?')[:50]}")

if kelime:
    print(f"\n'{kelime}' ifadesi geçen parçalar (ilk {N} sonuç içinde):")
    bulundu = False
    for i in range(N):
        metin = " ".join(r["documents"][0][i].split())
        k = metin.lower().find(kelime)
        if k != -1:
            bulundu = True
            kaynak = r["metadatas"][0][i].get("source_file", "?")[:40]
            parca = metin[max(0, k - 150): k + 200]
            print(f"\n  SIRA {i + 1} | {kaynak}\n  ...{parca}...")
    if not bulundu:
        print("  hiçbiri")