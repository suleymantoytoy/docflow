"""
PDF, Word ve HTML dosyaları için ayrıştırıcı (parser) modülü.
Ham metni ve temel metadata'yı (kaynak, tarih, format) çıkarır.

Hafta 6-7 düzeltmesi: Artık tracker.py üzerinden içerik hash'ine göre
yeni/değişmiş dosyaları tespit ediyor (önceden sadece "JSON zaten var mı"
diye bakıyordu — bu yüzden bir dosya güncellense bile yeniden işlenmiyordu).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pymupdf as fitz  # PyMuPDF
import docx  # Word dosyaları için (.docx)
from bs4 import BeautifulSoup  # HTML için

# Bu dosya doğrudan "python ingestion/parser.py" ile de çalıştırılabilsin diye
# (run_pipeline.py üzerinden değil) proje kökünü elle sys.path'e ekliyoruz —
# yoksa "ingestion.tracker" importu "ModuleNotFoundError" ile patlar.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingestion.tracker import get_new_or_updated_files, get_file_hash, update_tracker


def extract_metadata(filepath: Path, doc_format: str) -> dict:
    return {
        "kaynak": filepath.name,
        "tarih": datetime.now().isoformat(),
        "format": doc_format,
    }


def parse_pdf(filepath: Path) -> tuple:
    text = ""
    try:
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text() + "\n"
    except Exception as e:
        print(f"[HATA] PDF okunamadı {filepath.name}: {e}")
    return text.strip(), extract_metadata(filepath, "pdf")


def parse_docx(filepath: Path) -> tuple:
    text = ""
    try:
        doc = docx.Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        print(f"[HATA] Word okunamadı {filepath.name}: {e}")
    return text.strip(), extract_metadata(filepath, "docx")


def parse_html(filepath: Path) -> tuple:
    text = ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
    except Exception as e:
        print(f"[HATA] HTML okunamadı {filepath.name}: {e}")
    return text.strip(), extract_metadata(filepath, "html")


def parse_document(filepath: Path) -> dict:
    ext = filepath.suffix.lower()
    text, metadata = "", {}

    if ext == ".pdf":
        text, metadata = parse_pdf(filepath)
    elif ext == ".docx":
        text, metadata = parse_docx(filepath)
    elif ext == ".doc":
        # python-docx eski .doc (binary OLE) formatını OKUYAMAZ, sadece .docx'i okur.
        # Bunu sessizce başarısız olup kafa karıştırmak yerine açıkça logluyoruz.
        print(f"[ATLANDI] {filepath.name}: eski .doc formatı desteklenmiyor "
              f"(python-docx sadece .docx okuyabilir). Elle .docx'e çevirip tekrar deneyin.")
    elif ext in [".htm", ".html"]:
        text, metadata = parse_html(filepath)
    else:
        print(f"[ATLANDI] {filepath.name}: desteklenmeyen format ({ext})")

    return {"text": text, "metadata": metadata}


def run_parser():
    BASE_DIR = Path(__file__).resolve().parent.parent
    PARSED_DIR = BASE_DIR / "data" / "parsed_documents"
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    # Hafta 6-7: sadece YENİ veya İÇERİĞİ DEĞİŞMİŞ dosyaları al (hash tabanlı)
    files_to_process = get_new_or_updated_files()

    if not files_to_process:
        print("Yeni veya güncellenmiş dosya yok — hepsi zaten güncel, hiçbir şey yapılmadı.")
        return

    print(f"Toplam {len(files_to_process)} yeni/güncellenmiş dosya okunuyor. Lütfen bekleyin...")

    new_count = 0
    for filepath in files_to_process:
        print(f"Okunuyor: {filepath.name}")
        parsed_data = parse_document(filepath)

        json_filepath = PARSED_DIR / (filepath.stem + ".json")

        if parsed_data["text"]:
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, ensure_ascii=False, indent=4)
            new_count += 1
            # Sadece başarıyla işlendiyse tracker'ı güncelle — başarısız olursa
            # bir sonraki çalıştırmada tekrar denensin diye hash kaydedilmiyor.
            update_tracker(filepath.name, get_file_hash(filepath))
        else:
            print(f"[UYARI] {filepath.name}: metin çıkarılamadı, tracker güncellenmedi (tekrar denenecek).")

    print(f"\n✅ İşlem tamam! {new_count} belge başarıyla metne çevrildi/güncellendi.")


if __name__ == "__main__":
    run_parser()
