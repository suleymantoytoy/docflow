# DocFlow — Kurumsal Doküman İşleme ve RAG Pipeline

> Durum: 🚧 Hafta 1 / 13 — Hazırlık aşaması

Dağınık kurumsal dokümanları (PDF/Word/HTML) otomatik olarak işleyen; kalite
kontrolünden, deduplication'dan ve versiyon takibinden geçiren; ve bunları
kaynak gösterebilen bir soru-cevap (RAG) sistemine besleyen uçtan uca bir
veri hattı.

## Neden

Kurumlarda yönetmelik, prosedür, SSS gibi dokümanlar dağınık formatlarda
tutulur. Bunları doğrudan bir LLM'e vermek güncellik ve güvenilirlik sorunu
yaratır. Bu proje, dokümanların yaşam döngüsünü (toplama → doğrulama →
tekilleştirme → versiyonlama → indeksleme → kaynaklı cevap) yöneterek bu
problemi çözer.

## Mimari (planlanan)

```
raw docs → [ingestion] → [quality check] → [dedup] → [versioning]
         → [chunking + embedding] → [vector DB] → [FastAPI /ask] → cevap + kaynak
```

## Domain

Bu prototipte kaynak veri seti: Necmettin Erbakan Üniversitesi'nin
halka açık personel görev tanımı PDF'leri. Bkz.
`docs/karar_gunlugu.md` (Hafta 1, Karar 1).

İlk 4 kaynak (tek tek doğrulanmış, çalışan URL'ler) `data/kaynak_listesi.json`
içinde. İndirmek için:

```bash
pip install requests
python scripts/download_documents.py
```

## Kurulum

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Yol Haritası

13 haftalık plan ve ilerleme takibi için: `docs/karar_gunlugu.md`
(canlı ilerleme takip aracı ayrıca paylaşılmıştır).

## Durum

- [x] Hafta 1: Domain ve ortam kararları
- [ ] Hafta 2-3: Ingestion & Parsing
- [ ] Hafta 4-5: Veri Kalitesi & Deduplication
- [ ] Hafta 6-7: Versioning & Incremental Processing
- [ ] Hafta 8-9: Chunking, Embedding & İndeksleme
- [ ] Hafta 10-11: Retrieval & RAG Serving
- [ ] Hafta 12: Değerlendirme
- [ ] Hafta 13: Dokümantasyon & Vitrin
