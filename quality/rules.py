"""
Faz 2 - Hafta 4: Veri Kalitesi Kuralları
Bu modül, işlenen belgelerin RAG sistemine uygunluğunu denetler.
"""
from langdetect import detect, LangDetectException

def check_min_length_and_empty(text: str, min_chars: int = 150) -> tuple[bool, str]:
    """
    Kural 1 ve Kural 3: Minimum karakter kuralı ve Boş doküman kontrolü.
    Eğer metin yoksa veya çok kısaysa (örn. sadece başlık veya bozuk sayfa),
    RAG aramalarında işe yaramayacağı için elenir.
    """
    if not text:
        return False, "Doküman tamamen boş."
    
    # Boşlukları temizleyip gerçek uzunluğa bakıyoruz
    clean_text = text.strip()
    if len(clean_text) < min_chars:
        return False, f"İçerik çok kısa ({len(clean_text)} karakter). Min: {min_chars}"
        
    return True, ""

def check_language(text: str, expected_lang: str = "tr") -> tuple[bool, str]:
    """
    Kural 2: Dil tespiti kuralı.
    Sisteme yanlışlıkla İngilizce veya anlamsız karakter dizilerinden oluşan
    bir metin girerse tespit eder.
    """
    try:
        # Metnin ilk 1000 karakterini alarak hız kazandırıyoruz
        lang = detect(text[:1000])
        if lang != expected_lang:
            return False, f"Beklenmeyen dil tespit edildi: {lang}"
    except LangDetectException:
        # Eğer metinde hiç harf yoksa (sadece sayı/noktalama ise) buraya düşer
        return False, "Metnin dili anlaşılamadı (muhtemelen anlamsız karakterler)."
        
    return True, ""

def check_metadata_completeness(metadata: dict) -> tuple[bool, str]:
    """
    Kural 4: Metadata eksiksizlik kontrolü.
    Kaynak adı, tarih veya format bilgisi eksikse veriyi reddederiz.
    """
    required_keys = ["kaynak", "tarih", "format"]
    
    for key in required_keys:
        if key not in metadata or not metadata[key]:
            return False, f"Eksik metadata alanı: {key}"
            
    return True, ""

def evaluate_document(parsed_data: dict) -> tuple[bool, list]:
    """
    Tüm kuralları çalıştıran ana değerlendirme fonksiyonu.
    Geçerlilik durumunu ve eğer hata varsa elenme sebeplerini döndürür.
    """
    text = parsed_data.get("text", "")
    metadata = parsed_data.get("metadata", {})
    
    reasons = [] # Elenme sebeplerini toplayacağımız liste
    
    # 1. ve 3. Kuralı Uygula (Uzunluk ve Boşluk)
    passed_len, msg_len = check_min_length_and_empty(text)
    if not passed_len:
        reasons.append(msg_len)
        
    # Eğer metin yoksa veya çok kısaysa dil tespiti yapmaya gerek yok, çöker.
    # Bu yüzden sadece uzunluk testini geçenlere dil testi yapıyoruz.
    if passed_len:
        # 2. Kuralı Uygula (Dil)
        passed_lang, msg_lang = check_language(text)
        if not passed_lang:
            reasons.append(msg_lang)
            
    # 4. Kuralı Uygula (Metadata)
    passed_meta, msg_meta = check_metadata_completeness(metadata)
    if not passed_meta:
        reasons.append(msg_meta)
        
    # Eğer reasons listesi boşsa (0 hata), belge kuralları geçmiştir (True).
    is_valid = len(reasons) == 0
    
    return is_valid, reasons