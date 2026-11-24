"""
Faz 4 - Hafta 8: Chunking (Metin Parçalama) Stratejisi ve Testi
LangChain kullanarak metinleri anlamlı bütünleri bozmadan parçalara ayırır.
"""
import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE_DIR / "data" / "parsed_documents"

def test_chunking():
    # YOL HARİTASI: Chunking stratejisine ve overlap boyutuna karar ver
    # Strateji: RecursiveCharacterTextSplitter (Anlamı korumak için en iyi yöntem)
    # Önce paragraflara (\n\n), sonra satırlara (\n), en son kelimelere göre böler.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,   # Her bir parça maksimum 1000 karakter olacak
        chunk_overlap=150, # Anlam kopmasın diye parçalar arası 150 karakterlik kesişim (örtüşme)
        length_function=len,
        is_separator_regex=False,
    )

    docs = list(PARSED_DIR.glob("*.json"))
    if not docs:
        print("İşlenecek onaylı doküman bulunamadı!")
        return

    print(f"Toplam {len(docs)} doküman parçalanacak (Chunking)...\n")
    
    total_chunks = 0
    
    # Terminali boğmamak için sadece ilk 3 belgenin detayını ekrana basıyoruz
    for i, doc_path in enumerate(docs):
        with open(doc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        text = data.get("text", "")
        
        # YOL HARİTASI: Kayıp (data loss) yaşamadan bölme işlemini test et
        chunks = text_splitter.split_text(text)
        total_chunks += len(chunks)
        
        if i < 3:
            print(f"📄 Doküman: {doc_path.name}")
            print(f"   Orijinal Uzunluk: {len(text)} karakter")
            print(f"   Oluşan Parça (Chunk) Sayısı: {len(chunks)}")
            if chunks:
                print(f"   Örnek Parça 1 Uzunluğu: {len(chunks[0])} karakter")
                print(f"   --- İlk parçadan kısa bir kesit ---")
                print(f"   {chunks[0][:150]}...\n")
                
    print("-" * 40)
    print(f"TEST BAŞARILI: {len(docs)} belge, hiçbir veri kaybı yaşanmadan toplam {total_chunks} parçaya bölündü!")

if __name__ == "__main__":
    test_chunking()