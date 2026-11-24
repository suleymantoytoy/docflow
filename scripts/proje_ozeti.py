"""
Projeyi tek bir txt dosyasında toplar (yeni bir sohbete yapıştırmak için).
Sadece metin kaynak kodu alınır; veri, model, görsel, PDF, venv, indeks, tek kullanımlık
test scriptleri alınmaz. API anahtarları otomatik gizlenir. Çıktı: proje_ozeti.txt

Kullanım:  python scripts/proje_ozeti.py
"""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CIKTI = BASE / "proje_ozeti.txt"
DEVIR = BASE / "docs" / "devir_notu.md"

UZANTILAR = {".py"}
OZEL_DOSYALAR = {"requirements.txt", ".env.example"}

ATLA_KLASORLER = {"venv", ".venv", "__pycache__", ".git", "data", "docs", "node_modules"}
ATLA_DOSYALAR = {
    "rerank_test.py", "rank_test.py", "hybrid_test.py", "retrieval_test.py",
    "db_manager.py", "chunker.py", "embedder.py", "proje_ozeti.py",
}
MAX_KARAKTER = 30_000  # bir dosya bundan uzunsa kesilir

ANAHTAR = re.compile(r"(gsk_[A-Za-z0-9]{20,}|tvly-[A-Za-z0-9_\-]{10,}|AIza[0-9A-Za-z_\-]{20,}|AQ\.[A-Za-z0-9_\-]{20,})")


def temizle(metin: str) -> str:
    metin = ANAHTAR.sub("[GİZLİ-ANAHTAR]", metin)
    metin = "\n".join(s.rstrip() for s in metin.splitlines())
    return re.sub(r"\n{3,}", "\n\n", metin).strip()


dosyalar = []
for p in sorted(BASE.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(BASE)
    if any(parca in ATLA_KLASORLER for parca in rel.parts[:-1]):
        continue
    if p.name in ATLA_DOSYALAR or p.name == ".env":
        continue
    if p.suffix.lower() in UZANTILAR or p.name in OZEL_DOSYALAR:
        dosyalar.append(p)

bolumler = []
if DEVIR.exists():
    bolumler.append("##### DEVİR NOTU #####\n" + temizle(DEVIR.read_text(encoding="utf-8", errors="replace")))

bolumler.append("##### DOSYA AĞACI #####\n" + "\n".join(str(p.relative_to(BASE)) for p in dosyalar))

for p in dosyalar:
    metin = temizle(p.read_text(encoding="utf-8", errors="replace"))
    if len(metin) > MAX_KARAKTER:
        metin = metin[:MAX_KARAKTER] + "\n... [KESİLDİ: dosya çok uzun]"
    bolumler.append(f"===== {p.relative_to(BASE)} =====\n{metin}")

cikti = "\n\n".join(bolumler)
CIKTI.write_text(cikti, encoding="utf-8")
print(f"{len(dosyalar)} dosya, {len(cikti):,} karakter (yaklaşık {len(cikti) // 3:,} token) -> {CIKTI}")