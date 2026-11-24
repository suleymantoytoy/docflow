# DocFlow: Hibrit RAG ve Ajan Tabanlı Okul Yönetmeliği Bilgi Asistanı

**Sürüm:** 1.0.0 (Release) | **Hedef Kullanım:** Öğrenci İşleri, Akademisyenler ve Öğrenciler için Mevzuat/Yönetmelik Destek Sistemi | **Mimari:** Hibrit Arama (RAG) + Otomatik Web Arama Ajanı (Fallback Agent)

---

## 📌 Proje Özeti
DocFlow, öğrenci işleri ve akademisyenlerin yönetmeliklerle ilgili karmaşık veya güncel sorularına hızlı ve doğrulanabilir yanıtlar üretmek için geliştirilmiş yapay zeka tabanlı bilgi asistanıdır. Geleneksel tek kaynaklı sohbet botlarının aksine, sorulan soruyu önce **yerel okul yönetmeliği ve kurumsal belgeler** içinde tarar; aranan bilgi yönetmeliklerde bulunamadığında otomatik olarak **internet aramasına (web fallback)** geçerek güncel cevabı getirir.

## 🏗️ Sistem Mimarisi

### 1. Belge İşleme ve Veri Kalitesi Hattı (`ingestion/` & `quality/`)
* **Ayrıştırma ve Takip (`parser.py`, `tracker.py`):** Kurumsal yönetmelik ve dokümanları otomatik olarak ayrıştırır, dosya değişikliklerini takip ederek güncel veri tabanını korur.
* **Kalite Filtreleme (`filter_pipeline.py`, `rules.py`):** İndeksleme öncesinde belgeleri belirlenen kalite kurallarından geçirerek gürültülü veya bozuk metinleri ayıklar.

### 2. Parçalama ve Hibrit Arama Motoru (`embedding/`)
* **Anlamsal Parçalama ve Vektörleştirme (`chunker.py`, `embedder.py`, `build_index.py`):** Yönetmelik metinlerini bağlamı koruyacak şekilde parçalara (chunk) böler ve vektör veritabanına (`db_manager.py`) indeksler.
* **Hibrit Getirme (`hybrid.py`):** Hem anlamsal (vektör) hem de anahtar kelime tabanlı aramayı birleştirerek soruya en uygun yönetmelik maddelerini üst sıralara taşır.

### 3. Ajan ve API Katmanı (`api/`)
* **Akıllı Yönlendirme Ajanı (`agent.py`):** Kullanıcı sorusunu analiz eder. Yerel yönetmelik indeksinde yeterli ve güvenilir bağlam varsa doğrudan mevzuata dayalı yanıt üretir; bilgi eksikse otomatik olarak internet araması yaparak cevabı tamamlar.
* **Servis ve Takvim Modülü (`main.py`, `takvim.py`):** Sistemin arka plan API servislerini ve akademik takvim/tarih sorgularını yönetir.
* **Değerlendirme ve Test (`scripts/`):** Hibrit arama, sıralama (`rank_test.py`), geri getirme (`retrieval_test.py`) ve uçtan uca kalite testleri (`eval.py`) için modüler doğrulama betikleri içerir.

## 🚀 Çalıştırma

**1. Kurulum ve Ortam Değişkenleri:**
```bash
pip install -r requirements.txt