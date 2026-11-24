# DocFlow — Devir Notu (yeni sohbet için)

## Proje
Necmettin Erbakan Üniversitesi'nin 184 yönetmelik/yönerge PDF'i üzerinde çalışan, kaynak gösteren soru-cevap
asistanı (RAG) ve onu besleyen veri hattı. CV/portföy projesi. Kullanıcı bilgisayar mühendisliği öğrencisi (Windows,
`C:\Docflow`, venv, Python 3.12, RTX 3050 Ti 4 GB, 16 GB RAM). Roadmap'e göre Faz 6-7 civarındayız (retrieval iyileştirme,
değerlendirme, sonra vitrin).

## Mimari
- `run_pipeline.py`: parser, kalite kontrolü, indeksleme sırayla çalışır.
- `ingestion/parser.py` (pymupdf, `tracker.py` ile hash tabanlı değişiklik tespiti), `quality/` (Prefect akışı:
  uzunluk, dil, tekrar kontrolü).
- `embedding/model.py`: multilingual-e5-small (sorgu "query: ", parça "passage: " öneki). `build_index.py`: parçalar,
  bir dokümanın eski parçalarını silip yenisini ekler, ChromaDB (`<1.5`) koleksiyonu `yonetmelikler`, 5135 parça.
- `embedding/hybrid.py`: BM25 + vektör, RRF, doküman başına en fazla 3 parça, `sozluk_genislet()`.
- `api/main.py`: FastAPI `/ask`. Sözlük genişletme, hibrit arama (10 parça), Groq model zinciri, yerel cevap
  "Bu bilgi verilen dokümanlarda bulunmamaktadır." ile başlıyorsa Tavily web aramasına düşer.
- `api/agent.py`: Tavily `web_arama()` (önce erbakan.edu.tr, sonra genel web).
- `app.py`: Streamlit. Yan menüden birim seçilir, soruya "X öğrencisiyim." eklenir, Tıp/Veteriner dışında "intörn" kelimesi
  "işyeri eğitimi (intörn)" yapılır.
- `scripts/`: `eval.py` (17 soruluk arama testi), `ara.py` (korpusta kelime arama), `download_documents.py`.
- Sırlar `.env` içinde (GROQ_API_KEY, TAVILY_API_KEY). `.env` içeriğini asla paylaşma.

## Yaşadığımız hatalar ve çözümleri
- Koda yazılmış API anahtarları, `.gitignore` eksikliği: `.env` ve yeni `.gitignore` ile çözüldü.
- Güncellenen dokümanın eski parçaları silinmiyordu: silip yeniden ekleme ile çözüldü. `tracker.py` hiç kullanılmıyordu, bağlandı.
- ChromaDB 1.5.x Windows hatası: `chromadb<1.5`.
- Gemini anahtarı çalışmadı: Groq'a geçildi.
- DuckDuckGo boş sonuç, web'den uydurma isim: Tavily, "uydurma" yasağı, `temperature=0`.
- "Kanıt yok" kelime araması yanlış pozitif verdi: `startswith` kontrolü.
- Arama doğru maddeyi getirmiyordu (kısa embedding penceresi, nadir kelime): e5 modeli, hibrit arama. Reranker işe yaramadı.
- Groq günlük token limiti: model zinciri. HyDE hiç denenmedi.
- "Intörn" kelimesi birime göre farklı anlama geliyor: birim seçimi.

## Açık sorunlar
1. Test sorusu 16 (Diş Hekimliği sınav türleri) hiçbir yöntemde bulunmuyor. Tahmin: çok sayıda benzer Diş Hekimliği parçası yarışıyor (doğrulanmadı).
2. Test sorusu 17 (Seydişehir, işletmede mesleki eğitime başvuru şartları) sözlükle bulunmuyor.
3. Mühendislik cevabı uzun, ilk cümlede net sonuç yok. "Kısa cevap:" ile başlatma önerildi, uygulandığı doğrulanmadı.
4. Kaynak listesi gürültülü, cevaba katkısı olmayan dokümanlar da yazılıyor.
5. `eval.py` sadece aramayı ölçüyor, cevap kalitesini ölçmüyor.
6. Kalite kuralları bozuk karakterli metni (`൴`) yakalamıyor. Taranmış PDF'ler (OCR yok) atlanıyor.
7. Doğrulanmamış: `main.py`'nin gerçekten `sozluk_genislet` kullandığı (terminalde `🔎 [SÖZLÜK GENİŞLETME]` satırı görünmeli). Eski Groq/Gemini anahtarlarının iptali.

## Sıradaki adımlar
1. Yukarıdaki 7. maddedeki iki şeyi doğrula.
2. "Kısa cevap:" prompt değişikliği, kaynak listesini sadeleştirme (sadece en alakalı 3-4 doküman).
3. Gerçek uçtan uca test: kullanıcı 8-10 gerçek öğrenci sorusu yazar, sitede sorulur, cevaplar doğru/yanlış/eksik diye işaretlenir.
4. Soru 16 ve 17'yi teşhis et (`scripts/ara.py` ve `eval.py`'deki sıra bilgisiyle). Birim seçimine dayalı doküman filtresi (metadata) düşünülebilir.
5. Parser'da bozuk karakter düzeltmesi ve kalite kuralı.
6. Vitrin: README (İngilizce), mimari şema, `tests/test_api.py`, demo videosu, versiyonlama demosu (doküman güncelle, eski parçaların silindiğini göster), karar günlüğü son hali.

## Çalışma tarzı (kullanıcı tercihleri)
- Adım adım ilerle, her adımda tek iş ver. Kod bloklarını dosyaya yapıştırılacak şekilde tam ver.
- Şablon/kart formatı kullanma, cevapları kısa tut. Kullanıcının token'ı sınırlı.
- Tahminle ayar yapma: önce log/ölçüm iste. Doğrulanmamış şeyi "tahmin" diye belirt.
- Tek bir soruya göre ayar yapma, `scripts/eval.py` ile ölç. Eval sonuçları iyimser olabilir (aranan ifadeleri biz seçtik).
- Kullanıcı kod bloklarını elle kopyalıyor: eksik/fazla satır riski var, değişikliği "şunu bul, şununla değiştir" diye net yaz.