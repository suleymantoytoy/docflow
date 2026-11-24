"""
Kaynak klasör izleme mekanizması (Yeni ve değişen dosya tespiti).
"""
import json
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DOCS_DIR = BASE_DIR / "data" / "raw_documents"
TRACKER_FILE = BASE_DIR / "data" / "file_tracker.json"

def get_file_hash(filepath: Path) -> str:
    """Dosyanın içeriğine göre MD5 parmak izini hesaplar."""
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        # Büyük dosyalar için belleği şişirmemek adına chunk'lar halinde de okunabilir,
        # ancak belgelerimiz ufak olduğu için doğrudan okumak yeterli.
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def get_new_or_updated_files() -> list:
    """Sadece yeni veya içeriği değişmiş dosyaların yollarını (Path) döndürür."""
    # İzleme dosyasını oku (varsa)
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            tracked_data = json.load(f)
    else:
        tracked_data = {}

    files_to_process = []
    
    # raw_documents klasöründeki tüm dosyaları tara
    for filepath in RAW_DOCS_DIR.glob("*.*"):
        if filepath.is_file():
            current_hash = get_file_hash(filepath)
            filename = filepath.name
            
            # 1. Dosya JSON'da yoksa YENİDİR.
            # 2. Dosya JSON'da var ama hash'i farklıysa DEĞİŞMİŞTİR.
            if filename not in tracked_data or tracked_data[filename] != current_hash:
                files_to_process.append(filepath)
                
    return files_to_process

def update_tracker(filename: str, file_hash: str):
    """Dosya başarıyla işlendikten (ingest) sonra takip dosyasını günceller."""
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
            tracked_data = json.load(f)
    else:
        tracked_data = {}
        
    tracked_data[filename] = file_hash
    
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracked_data, f, ensure_ascii=False, indent=4)