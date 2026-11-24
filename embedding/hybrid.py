"""
Hibrit arama: vektör (anlamsal) + BM25 (anahtar kelime), Reciprocal Rank Fusion ile birleştirilir.
Her sorgu metni (soru + genişletilmiş anahtar kelimeler) ayrı ayrı aranır, sıralamalar RRF ile
birleşir. Tek bir doküman sonuçları doldurmasın diye doküman başına parça sınırı uygulanır.
"""
import re
from rank_bm25 import BM25Okapi
from embedding.model import embed_query


def tr_lower(s):
    return s.replace("İ", "i").replace("I", "ı").lower()


def tokenize(text):
    # Türkçe çekim eklerine karşı kaba çözüm: her kelimenin ilk 5 harfi
    return [w[:5] for w in re.findall(r"\w+", tr_lower(text)) if len(w) > 1]


class HybridRetriever:
    def __init__(self, collection, embeddings):
        self.collection = collection
        self.embeddings = embeddings
        data = collection.get(include=["documents", "metadatas"])
        self.ids = data["ids"]
        self.docs = data["documents"]
        self.metas = data["metadatas"]
        self.pos = {cid: i for i, cid in enumerate(self.ids)}
        self.bm25 = BM25Okapi([tokenize(d) for d in self.docs])
        print(f"Hibrit arama hazır: {len(self.ids)} parça indekslendi.")

    def _rankings(self, text, pool):
        qv = embed_query(self.embeddings, text)
        r = self.collection.query(query_embeddings=[qv], n_results=pool)
        vec_ids = r["ids"][0]
        scores = self.bm25.get_scores(tokenize(text))
        bm_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:pool]
        bm_ids = [self.ids[i] for i in bm_idx if scores[i] > 0]
        return vec_ids, bm_ids

    def search(self, question, k=10, pool=30, rrf_k=60, max_per_doc=5, extra_queries=()):
        fused = {}
        for text in [question, *extra_queries]:
            if not text or not text.strip():
                continue
            for ranking in self._rankings(text, pool):
                for rank, cid in enumerate(ranking):
                    fused[cid] = fused.get(cid, 0) + 1 / (rrf_k + rank + 1)

        sayac, secilen = {}, []
        for cid in sorted(fused, key=fused.get, reverse=True):
            kaynak = self.metas[self.pos[cid]].get("source_file", "?")
            if sayac.get(kaynak, 0) >= max_per_doc:
                continue
            sayac[kaynak] = sayac.get(kaynak, 0) + 1
            secilen.append(cid)
            if len(secilen) >= k:
                break
        return [(cid, self.docs[self.pos[cid]], self.metas[self.pos[cid]]) for cid in secilen]


def sozluk_genislet(soru: str) -> str:
    """Günlük dildeki kelimeleri yönetmelik terimleriyle genişletir (sabit kural, LLM yok).
    'alttan ders' (daha önce alınıp kalınmış ders) ile 'devam zorunluluğu olan ders' aynı
    şey değildir; ama yönergeler bu kavramları birlikte andığı için ikisi de aranır."""
    t = tr_lower(soru)
    tip = "tıp fakültesi" in t or "veteriner" in t
    birim_var = "öğrencisiyim" in t
    parca = []
    if "alttan" in t:
        parca.append("başarısız ders, ders tekrarı, devamsızlık, devam şartı, devam zorunluluğu")
    if re.search(r"\ba?gno\b", t):
        parca.append("genel not ortalaması, genel ağırlıklı not ortalaması, mezuniyet ağırlıklı not ortalaması")
    if re.search(r"kul[uü][pb]", t):
        parca.append("öğrenci topluluğu, topluluk kurma, kuruluş başvurusu, kurucu öğrenci")
    if "intörn" in t:
        tip_terimleri = "intörn doktorluk, intörn programı, dönem VI, altıncı sınıfa geçme, tüm sınavları tamamlama"
        is_terimleri = "işyeri eğitimi, işletmede mesleki eğitim, staj"
        if tip:
            parca.append(tip_terimleri)
        elif birim_var:
            parca.append(is_terimleri)
        else:
            parca.append(f"{tip_terimleri}, {is_terimleri}")
    return " ".join(parca)