import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from embedding.hybrid import tr_lower, sozluk_genislet
from api.main import retriever

def norm(s):
    return " ".join(tr_lower(s).split())

soru, ifade = sys.argv[1], sys.argv[2]
hedef = norm(ifade)
genis = sozluk_genislet(soru)
extra = [genis] if genis else []

for etiket, md in (("SINIR 5 (gerçek ayar)", 5), ("SINIRSIZ", 1000)):
    hits = retriever.search(soru, k=40, max_per_doc=md, extra_queries=extra)
    print(f"\n--- {etiket} ---")
    for sira, (cid, doc, m) in enumerate(hits, 1):
        isaret = "  <== HEDEF" if hedef in norm(doc) else ""
        if sira <= 12 or isaret:
            print(f"{sira:>2} {cid[:60]}{isaret}")