"""
Ana orkestrasyon scripti — tüm pipeline'ı sırayla çalıştırır:
  1. ingestion/parser.py   -> yeni/değişmiş ham dosyaları metne çevir
  2. quality/filter_pipeline.py -> kalite kontrolü + deduplication
  3. embedding/build_index.py   -> chunk'la, embed et, ChromaDB'ye yaz

Önceden her adımı elle, ayrı ayrı çalıştırmak gerekiyordu (python ingestion/parser.py,
sonra python quality/filter_pipeline.py, sonra python embedding/build_index.py) —
bu hem unutulmaya açıktı hem de hiçbir script birbirini çağırmıyordu. Airflow
kullanmama kararımız (bkz. karar_gunlugu.md) hâlâ geçerli; bu script o kararın
basit, Python-içi karşılığı — adımlar arasında sıra garantisi ve tek komutla
çalıştırma sağlıyor.

Kullanım:
    python run_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingestion.parser import run_parser
from quality.filter_pipeline import run_quality_pipeline
from embedding.build_index import build_vector_db


def main():
    print("=" * 60)
    print("ADIM 1/3 — INGESTION (ham dosyaları metne çevir)")
    print("=" * 60)
    run_parser()

    print("\n" + "=" * 60)
    print("ADIM 2/3 — VERİ KALİTESİ & DEDUPLICATION")
    print("=" * 60)
    run_quality_pipeline()

    print("\n" + "=" * 60)
    print("ADIM 3/3 — CHUNKING, EMBEDDING & İNDEKSLEME")
    print("=" * 60)
    build_vector_db()

    print("\n" + "=" * 60)
    print("✅ PIPELINE TAMAMLANDI")
    print("=" * 60)
    print("Sırada: 'uvicorn api.main:app --reload' ile API'yi, ardından")
    print("'streamlit run app.py' ile arayüzü başlatabilirsin.")


if __name__ == "__main__":
    main()