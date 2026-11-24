"""
Faz 3 - Hafta 7: Upsert (Üzerine Yazma / Geçersiz Kılma) Mekanizması

NOT: Bu dosya KAVRAMSAL bir prototip/kanıt-of-concept'tir — ayrı bir
mock_vectordb.json dosyasına yazıyor, gerçek pipeline'da (embedding/build_index.py,
api/main.py) KULLANILMIYOR. Gerçek upsert/invalidation mantığı build_index.py
içinde, ChromaDB üzerinde uygulanıyor (ve orada bu prototipte fark edilmeyen
bir "yetim chunk" hatası bulunup düzeltildi — bkz. docs/karar_gunlugu.md).
Bu dosya sadece fikrin basitleştirilmiş bir gösterimi olarak repoda kalıyor.
"""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MOCK_DB_FILE = BASE_DIR / "data" / "mock_vectordb.json"

def upsert_document(doc_id: str, text: str, metadata: dict):
    """
    Belirtilen ID'ye (Dosya Adı) sahip bir kayıt varsa ezer (Update),
    yoksa yeni kayıt olarak ekler (Insert).
    """
    # 1. Mevcut veritabanını oku
    db = {}
    if MOCK_DB_FILE.exists():
        with open(MOCK_DB_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
            
    # 2. Kayıt veritabanında zaten var mı kontrol et
    is_update = doc_id in db
    
    # 3. Veriyi yaz/güncelle (Eski veri acımasızca ezilir)
    db[doc_id] = {
        "text": text,
        "metadata": metadata
    }
    
    # 4. Veritabanını kaydet
    MOCK_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MOCK_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
        
    action = "GÜNCELLENDİ (Eski versiyon silindi/ezildi)" if is_update else "YENİ KAYIT EKLENDİ"
    print(f"[UPSERT] Doküman ID: '{doc_id}' -> {action}")
    
    return is_update

if __name__ == "__main__":
    # YOL HARİTASI HEDEFİ: Uçtan uca senaryoyu test et
    print("--- 1. ADIM: Yönetmeliğin Orijinal Halini Sisteme Yükle ---")
    upsert_document(
        doc_id="sinav_yonetmeligi", # Sabit ID (Dosya adını temsil eder)
        text="Madde 1: Üniversitede geçme notu 50'dir.",
        metadata={"kaynak": "sinav_yonetmeligi.pdf", "tarih": "2024"}
    )
    
    print("\n--- 2. ADIM: Üniversite Kuralları Değiştirdi! Yeni Dosyayı Yükle ---")
    upsert_document(
        doc_id="sinav_yonetmeligi", # ID aynı olduğu için sistem eski kaydı bulup ezecek
        text="Madde 1: Üniversitede geçme notu 65 olmuştur. (GÜNCEL)",
        metadata={"kaynak": "sinav_yonetmeligi.pdf", "tarih": "2026"}
    )
    
    print("\nVeritabanının son hali 'data/mock_vectordb.json' dosyasına işlendi. Halüsinasyon riski ortadan kaldırıldı!")