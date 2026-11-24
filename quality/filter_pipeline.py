"""
Faz 2 - Hafta 4 ve 5: Kalite Kontrol, Deduplication ve Raporlama İş Akışı
"""
import json
import hashlib
from pathlib import Path
from prefect import task, flow
from quality.rules import evaluate_document

BASE_DIR = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE_DIR / "data" / "parsed_documents"
REJECTED_DIR = BASE_DIR / "data" / "rejected"
REPORT_FILE = BASE_DIR / "docs" / "kalite_raporu.md"

def get_text_hash(text: str) -> str:
    """Duplicate tespiti için metnin içeriğine göre SHA-256 parmak izi üretir."""
    clean_text = text.strip().lower()
    return hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

@task(name="1- İşlenmiş Belgeleri Getir")
def get_parsed_documents():
    return list(PARSED_DIR.glob("*.json"))

@task(name="2- Kalite ve Deduplication Kontrolü")
def apply_gates_and_dedup(filepath: Path, seen_hashes: set):
    """
    Belgeyi kalite kurallarından ve duplicate testinden geçirir.
    Geçemeyenleri rejected klasörüne taşır.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        parsed_data = json.load(f)
        
    is_valid, reasons = evaluate_document(parsed_data)
    
    # Kural 1: Mevcut kalite kurallarını geçemezse reddet
    if not is_valid:
        reject_reason = "Yetersiz/Bozuk İçerik: " + " | ".join(reasons)
    else:
        # Kural 2: Deduplication (Kopya Kontrolü)
        text_hash = get_text_hash(parsed_data.get("text", ""))
        if text_hash in seen_hashes:
            is_valid = False
            reject_reason = "Duplicate (Kopya İçerik)"
        else:
            seen_hashes.add(text_hash)
            
    if not is_valid:
        parsed_data["rejection_reasons"] = [reject_reason]
        rejected_path = REJECTED_DIR / filepath.name
        
        with open(rejected_path, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=4)
            
        filepath.unlink()
        return False, filepath.name, reject_reason
        
    return True, filepath.name, ""

@task(name="3- Rapor Oluştur ve Kaydet")
def generate_markdown_report(total: int, passed: int, rejected: int, duplicate: int, insufficient: int):
    """Hafta 5 hedefine uygun somut sayı üreten Markdown raporunu yazar."""
    report_content = f"""# Veri Kalitesi ve Deduplication Raporu

**Özet Sonuç:** Toplam {total} dokümanın {rejected}'si elendi. {passed} doküman RAG indekslemesi için onaylandı.

## Detaylı Kırılım
* **Onaylanan (Geçerli) Doküman:** {passed}
* **Elenen Toplam Doküman:** {rejected}
  * **Duplicate (Kopya) Nedeniyle Elenenler:** {duplicate}
  * **Yetersiz/Bozuk İçerik Nedeniyle Elenenler:** {insufficient}

*Not: Bu rapor otomatik olarak Prefect iş akışı tarafından oluşturulmuştur.*
"""
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_content)

@flow(name="Kalite_ve_Dedup_Akisi", log_prints=True)
def run_quality_pipeline():
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    docs = get_parsed_documents()
    
    seen_hashes = set()
    total_docs = len(docs)
    passed_count = 0
    duplicate_count = 0
    insufficient_count = 0
    
    print(f"Test Seti Çalıştırılıyor: Toplam {total_docs} belge işlenecek.")
    
    for doc_path in docs:
        is_valid, name, reason = apply_gates_and_dedup(doc_path, seen_hashes)
        
        if is_valid:
            passed_count += 1
        else:
            if "Duplicate" in reason:
                duplicate_count += 1
            else:
                insufficient_count += 1
                
    rejected_count = duplicate_count + insufficient_count
    
    print("-" * 30)
    print(f"Sonuç: {total_docs} dokümanın {rejected_count}'si elendi — {duplicate_count}'si duplicate, {insufficient_count}'si yetersiz içerik.")
    
    generate_markdown_report(total_docs, passed_count, rejected_count, duplicate_count, insufficient_count)
    print(f"Rapor başarıyla 'docs/kalite_raporu.md' konumuna kaydedildi.")

if __name__ == "__main__":
    run_quality_pipeline()