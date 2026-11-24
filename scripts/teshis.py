import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from embedding.hybrid import tr_lower, tokenize
from embedding.model import embed_query
from api.main import retriever

def norm(s):
    return " ".join(tr_lower(s).split())

soru, ifade = sys.argv[1], sys.argv[2]
hedef = norm(ifade)
idx = [i for i, d in enumerate(retriever.docs) if hedef in norm(d)]
print(f"\nHedef ifadeyi içeren parça sayısı: {len(idx)}")
if not idx:
    sys.exit()

N = len(retriever.ids)
qv = embed_query(retriever.embeddings, soru)
r = retriever.collection.query(query_embeddings=[qv], n_results=N)
vec_rank = {cid: k + 1 for k, cid in enumerate(r["ids"][0])}
scores = retriever.bm25.get_scores(tokenize(soru))
order = sorted(range(N), key=lambda i: scores[i], reverse=True)
bm_rank = {retriever.ids[i]: k + 1 for k, i in enumerate(order)}

for i in idx:
    cid = retriever.ids[i]
    print(cid[:70])
    print("  vektör sırası:", vec_rank.get(cid), "| BM25 sırası:", bm_rank.get(cid),
          "| BM25 skoru:", round(float(scores[i]), 2))