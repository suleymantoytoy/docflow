"""
Faz 5 - Hafta 10: Vektör Veritabanı Entegrasyonu
Onaylı belgeleri okur, parçalar, vektörlere çevirir ve ChromaDB'ye yazar.
Bir doküman güncellenirse o dokümana ait eski chunk'lar önce silinir.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embedding.model import load_embeddings, embed_passages

BASE_DIR = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE_DIR / "data" / "parsed_documents"
CHROMA_DB_DIR = BASE_DIR / "data" / "chroma_db"

MIN_CHUNK_UZUNLUK = 80  # bundan kısa parçalar gürültü yapıyor, atılıyor


def temizle(text: str) -> str:
    # Bazı PDF'lerde "i" harfi font kodlama hatasıyla "൴" çıkıyor
    return text.replace("൴", "i")


def build_vector_db():
    print("1/3 -> Embedding modeli yükleniyor (Lokal)...")
    embeddings = load_embeddings()

    print("2/3 -> ChromaDB kalıcı veritabanı başlatılıyor...")
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_or_create_collection(name="yonetmelikler")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
    )

    docs = list(PARSED_DIR.glob("*.json"))
    print(f"\n3/3 -> Toplam {len(docs)} onaylı doküman veritabanına işleniyor...\n")

    for doc_path in docs:
        with open(doc_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        text = temizle(data.get("text", ""))
        metadata = data.get("metadata", {})
        doc_name = doc_path.stem
        source_file = doc_path.name

        try:
            collection.delete(where={"source_file": source_file})
        except Exception as e:
            print(f"[UYARI] {source_file} için eski chunk temizliği başarısız: {e}")

        chunks = [c for c in text_splitter.split_text(text) if len(c.strip()) >= MIN_CHUNK_UZUNLUK]

        if not chunks:
            print(f"[UYARI] {doc_name[:40]}... -> boş metin, atlandı.")
            continue

        ids, documents, metadatas = [], [], []
        for i, chunk in enumerate(chunks):
            ids.append(f"{doc_name}_chunk_{i}")
            documents.append(f"[{doc_name}] {chunk}")
            chunk_meta = metadata.copy()
            chunk_meta["chunk_index"] = i
            chunk_meta["source_file"] = source_file
            metadatas.append(chunk_meta)

        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embed_passages(embeddings, documents),
            metadatas=metadatas,
        )
        print(f"✅ {doc_name[:30]}... -> {len(chunks)} parça kaydedildi.")

    print("\n🎉 İŞLEM TAMAMLANDI! Tüm belgeler başarıyla vektör veritabanına işlendi.")
    print(f"Veritabanı Kalıcı Konumu: {CHROMA_DB_DIR}")


if __name__ == "__main__":
    build_vector_db()