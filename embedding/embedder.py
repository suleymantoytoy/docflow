"""
Faz 4 - Hafta 9: Embedding Entegrasyonu ve Testi
Chunk'lanmış metinleri HuggingFace modeli kullanarak sayısal vektörlere çevirir.
"""
from langchain_huggingface import HuggingFaceEmbeddings
import time

def test_embedding_model():
    print("Model yükleniyor... (İlk seferde indireceği için 1-2 dakika sürebilir)")
    start_time = time.time()
    
    # Seçtiğimiz Türkçe destekli lokal model
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        # CPU'da çalışmaya zorluyoruz ki ekran kartı sorunu yaşamayalım
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': False}
    )
    
    load_time = time.time() - start_time
    print(f"Model başarıyla yüklendi! (Yükleme süresi: {load_time:.2f} saniye)\n")

    # YOL HARİTASI HEDEFİ: 1 doküman üzerinde test et
    ornek_metin = "NECMETTİN ERBAKAN ÜNİVERSİTESİ ÖĞRENCİ KURULU YÖNERGESİ"
    print(f"Test Metni: '{ornek_metin}'")
    print("Vektöre çevriliyor...")
    
    # Metni embed (vektör) haline getiriyoruz
    vektor = embeddings.embed_query(ornek_metin)
    
    print("-" * 40)
    print("TEST BAŞARILI!")
    print(f"Vektör Boyutu: {len(vektor)} boyut (Yani bu cümle {len(vektor)} farklı sayı ile ifade ediliyor)")
    print(f"Vektörün İlk 5 Elemanı: {vektor[:5]}")
    
if __name__ == "__main__":
    test_embedding_model()