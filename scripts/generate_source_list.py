"""
Web sayfasındaki dokümanları otomatik toplayıp kaynak_listesi.json dosyasını doldurur.
GÜNCEL VERSİYON: Link adreslerinin yanı sıra BUTON İSİMLERİNİ de kontrol eden gelişmiş örümcek.
"""
import json
import time
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_LIST_PATH = BASE_DIR / "data" / "kaynak_listesi.json"

# Üniversitenin taranacak ana damarları
START_URLS = [
    "https://erbakan.edu.tr",
    "https://erbakan.edu.tr/tr/akademik",
    "https://erbakan.edu.tr/tr/idari"
] 

# Örümceğin arayacağı kelimeler (Türkçe karakterli halleri eklendi)
TARGET_KEYWORDS = ["yönerge", "yonerge", "mevzuat", "belge", "esas", "yönetmelik", "yonetmelik", "senato"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

def url_is_alive(url: str) -> bool:
    """Bir URL'nin gerçekten indirilebilir olup olmadığını kontrol eder.
    Link rot dersinden sonra eklendi — bkz. docs/karar_gunlugu.md."""
    try:
        resp = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if resp.status_code == 200:
            return True
        # Bazı sunucular HEAD'i desteklemiyor (405/403 dönebilir) — GET ile tekrar dene
        if resp.status_code in (405, 403):
            resp = requests.get(url, headers=HEADERS, timeout=8, stream=True)
            return resp.status_code == 200
        return False
    except Exception:
        return False


def get_links_with_text(url):
    """Bir sayfadaki linkleri ve butonların üzerindeki yazıları birlikte çeker"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, "html.parser")
        results = []
        for a in soup.find_all('a', href=True):
            full_url = urljoin(url, a['href'])
            text = a.get_text(strip=True).lower()
            results.append((full_url, text))
        return results
    except Exception:
        return []

def generate_json():
    existing_sources = []
    
    if SOURCE_LIST_PATH.exists():
        try:
            existing_sources = json.loads(SOURCE_LIST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    existing_urls = {item["url"] for item in existing_sources}
    
    print("🕸️ Gelişmiş Örümcek uyandı! Buton metinleri ve alt sayfalar taranıyor...\n")
    
    unit_links = []
    visited_pages = set()
    new_docs_count = 0
    
    # 1. Aşama: Tüm başlangıç linklerinden alt sayfa bağlantılarını topla
    for start_url in START_URLS:
        links = get_links_with_text(start_url)
        for url, text in links:
            if "erbakan.edu.tr" in url and url not in visited_pages:
                unit_links.append(url)
                visited_pages.add(url)

    # 2. Aşama: Toplanan sayfalara tek tek gir ve hedefleri ara
    for unit_url in unit_links:
        sub_links = get_links_with_text(unit_url)
        
        for sub_url, sub_text in sub_links:
            # KRİTİK NOKTA: Hedef kelime URL'nin içinde VEYA butonun üzerindeki yazıda var mı?
            if any(kw in sub_url.lower() or kw in sub_text for kw in TARGET_KEYWORDS):
                if sub_url in visited_pages:
                    continue
                visited_pages.add(sub_url)
                
                print(f"🔍 Mevzuat potansiyeli tespit edildi: {sub_url}")
                
                try:
                    resp = requests.get(sub_url, headers=HEADERS, timeout=10)
                    soup = BeautifulSoup(resp.content, "html.parser")
                    
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        text = a_tag.get_text(strip=True) or "İsimsiz Belge"
                        
                        if href.lower().endswith(('.pdf', '.doc', '.docx')):
                            full_url = urljoin(sub_url, href)

                            if full_url not in existing_urls:
                                # DÜZELTME: link rot dersi (bkz. karar_gunlugu.md) —
                                # bulunan her URL'yi listeye eklemeden ÖNCE gerçekten
                                # açılabildiğini doğrula. Arama/tarama sonuçlarına
                                # körü körüne güvenmek kırık linklerle sonuçlanabiliyor.
                                if not url_is_alive(full_url):
                                    print(f"   ⛔ Kırık/erişilemez, atlandı: {full_url}")
                                    continue

                                existing_sources.append({
                                    "url": full_url,
                                    "birim": sub_url.split("/")[-1] or "Bilinmeyen Birim",
                                    "belge": text
                                })
                                existing_urls.add(full_url)
                                new_docs_count += 1
                except Exception:
                    pass
                
                time.sleep(0.3)

    # 3. Aşama: Yeni veriyi kaydet
    SOURCE_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SOURCE_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(existing_sources, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Örümcek taramayı bitirdi! Toplam {new_docs_count} YENİ belge bulundu.")
    print(f"📂 JSON içindeki toplam belge sayısı: {len(existing_sources)}")

if __name__ == "__main__":
    generate_json()