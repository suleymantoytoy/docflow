# Karar Günlüğü — DocFlow

Bu dosya, proje boyunca alınan mimari kararları ve gerekçelerini kaydeder.
Amaç: mülakatta "neden bunu seçtin" sorusuna hazır, yazılı bir kanıt.

---

## Hafta 1 — Domain ve Ortam Kararları

**Tarih:** 2026-09-25

### Karar 1: Domain seçimi — İç yönetmelik / kurumsal prosedür dokümanları

Seçilen kaynak: Necmettin Erbakan Üniversitesi'nin (erbakan.edu.tr) halka açık
"personel görev tanımı" PDF'leri (çeşitli fakülte/birimlerden).

**Neden bu domain:**
- Gerçek, halka açık, indirilmesi kolay dokümanlar (KVKK riski yok — kişisel veri
  içermiyor, kurumsal görev tanımları).
- Kendi üniversitem olduğu için hem daha otantik hem de gerektiğinde ek
  doğrulama/bağlam bulmak daha kolay.
- Tek bir kurumdan geldiği için biçimsel tutarlılık var (Doküman No / Yayın Tarihi /
  Revizyon No / Görev ve Sorumluluklar gibi sabit alanlar tekrar ediyor), ama içerik
  birim birim farklılaşıyor — bu da gerçekçi bir "benzer ama aynı değil doküman seti"
  senaryosu kuruyor (dedup/versiyonlama katmanını anlamlı kılıyor).
- Format çeşitliliği barındırıyor: standart PDF'lerin yanında en az bir `.doc`
  (eski Word formatı, `.docx` değil) uzantılı belge de listede — bu, Faz 1'deki
  parser'ın hata toleransını gerçek bir edge-case ile test etmeyi sağlıyor.

**Kaynak toplama notu — beklenmeyen bir ders:** İlk aramada bulunan 5 URL'den
indirme scripti çalıştırıldığında 4'ü 404 verdi. Nedeni: erbakan.edu.tr, dosya
depolama şemasını değiştirmiş (`storage/files/department/{birim}/...` yapısından
`storage/departments/files/{id}/...` yapısına geçmiş); arama motorunun indexlediği
eski URL'lerin bir kısmı artık geçersiz. Her URL tek tek elle doğrulandı, 4 yeni
geçerli URL ile liste güncellendi (`data/kaynak_listesi.json`).

**Bu, projenin ilk gerçek veri kalitesi dersi oldu:** kaynak listeleri zamanla
bozulur ("link rot"), bu yüzden ingestion adımının kendisi de bir doğrulama
(HTTP durum kodu kontrolü, boş/404 yanıtları ayrı bir "başarısız kaynaklar"
listesine yazma) içermeli. Bu, Hafta 2-3'te ingestion modülüne eklenecek bir
gereksinim olarak not edildi — sadece dosya formatı hataları değil, kaynak
erişilebilirlik hataları da hata toleransı kapsamına giriyor.

20-30 hedefine ulaşmak için birim/fakülte sitelerinin "İç Kontrol", "Kalite" veya
"Yönergeler" sayfaları elle gezilerek liste genişletilecek — bu, Hafta 1'in açık
kalan bir görevi. Yeni bir URL eklerken önce tarayıcıda/`curl -I` ile açılabilir
olduğu doğrulanmalı (arama sonuçlarına körü körüne güvenilmemeli).

**Alternatif düşünülen:** Müşteri SSS / API dokümantasyonu. Elenme nedeni: hazır,
gerçek ve halka açık örnek bulmak daha zordu; yönetmelik dokümanları hem daha kolay
toplanabilir hem de "kurumsal RAG" hikayesini daha doğal anlatıyor.

### Karar 2: Orkestrasyon — Airflow değil, sade Python pipeline

**Neden Airflow değil:** Bu ölçekte (20-30 doküman, tek makine, düzenli ama sık
olmayan güncellemeler) Airflow'un getirdiği operasyonel yük (scheduler, webserver,
metadata DB kurulumu) faydasının önüne geçiyor. Pipeline'ı ayrı, test edilebilir
fonksiyonlara bölüp (ingest → quality → version → embed → index) bir CLI script'i
üzerinden çalıştıracağız. Adımlar birbirinden bağımsız modüller olduğu için, ileride
gerçekten ölçek/zamanlama ihtiyacı doğarsa Airflow'a (veya daha hafif bir alternatif
olan Prefect'e) taşımak mimariyi değiştirmeden mümkün olacak.

**Mülakatta savunma cümlesi:** "Airflow'u seçmedim çünkü ölçek onu gerektirmiyordu;
ama pipeline'ı Airflow'a taşınabilir şekilde modüler tasarladım — her adım bağımsız
bir fonksiyon, girdi/çıktısı net."

### Karar 3: Repo yapısı

```
docflow/
├── ingestion/      # PDF/Word/HTML parsing
├── quality/        # Kalite kuralları, deduplication
├── versioning/     # Doküman versiyon takibi, eski veri invalidation
├── embedding/      # Chunking, embedding, vektör DB yazma
├── api/            # FastAPI serving katmanı
├── eval/           # Retrieval evaluation seti ve script'i
├── docs/           # karar_gunlugu.md, kalite_raporu.md, eval_raporu.md
├── data/
│   ├── raw_documents/   # İndirilen ham PDF'ler (git'e girmez)
│   └── rejected/        # Kalite kontrolünden geçemeyenler (git'e girmez)
└── tests/
```

---

## Sıradaki adım (Hafta 1 devamı / Hafta 2)

- [x] İlk kaynak URL'leri bulundu ve tek tek doğrulandı (4/4 çalışıyor) →
      `data/kaynak_listesi.json`
- [ ] `scripts/download_documents.py` ile bu 4 dokümanı indir → `data/raw_documents/`
- [ ] Birim/fakülte "İç Kontrol", "Kalite" ve "Yönergeler" sayfalarını gezerek
      listeyi 20-30'a genişlet (her yeni URL'yi eklemeden önce açılabilir
      olduğunu doğrula, `kaynak_listesi.json`'a aynı formatta ekle)
- [ ] Hafta 2: ingestion/parser.py — PDF'den ham metin çıkarma (+ kaynak
      erişilebilirlik kontrolünü ingestion adımına dahil et — bkz. yukarıdaki
      "beklenmeyen ders")


# Karar Günlüğü

## Faz 0 - Başlangıç Kararları
* **Domain:** Necmettin Erbakan Üniversitesi iç yönetmelikleri ve yönergeleri (RAG testleri için ideal, kural tabanlı ve yapılandırılmış metinler).
* **Orkestrasyon Aracı:** Prefect. 
  * **Gerekçe:** Airflow'un hantal ve ağır altyapısı yerine; Python ekosistemine daha uygun, hafif, hızlı ayağa kalkan ve kod içi dekoratörlerle kolayca hata toleransı (retries) sağlayabilen modern bir araç olması.

## Faz 1 - Ingestion & Hata Toleransı
* **Parser ve Tracker:** PyMuPDF kullanılarak PDF okuma, MD5 hash yöntemiyle incremental processing (sadece yeni/değişen dosyaları işleme) mekanizması kuruldu.
* **Hata Toleransı Testi:** Kasıtlı olarak oluşturulan bozuk dosya (`bozuk_test.pdf`) ile sistem test edildi. Pipeline'ın çökmeden hatayı logladığı ve izole ederek akışa devam ettiği doğrulandı.

## Faz 3 - Versiyonlama Stratejisi
* **Karar:** Content Hash (İçerik Parmak İzi).
* **Gerekçe:** Dosya ismi veya değiştirilme tarihi yanıltıcı olabilir. Metnin içeriğinden üretilen hash değeri, dokümanda gerçek bir değişiklik olup olmadığını kesin olarak kanıtlar. Aynı dosya tekrar gelirse hash değeri değişmediği için pipeline tarafından atlanır (incremental processing).

## Faz 3 - Hafta 7: Upsert ve Geçersiz Kılma (Invalidation)
* **Karar:** Aynı ID'ye (Dosya Adı) sahip yeni bir belge geldiğinde "Upsert" (Üzerine Yazma) mekanizması uygulanacak.
* **Gerekçe:** Güncellenen kurumsal belgelerin eski versiyonlarının vektör veritabanında (veya mock DB'de) kalması yapay zekanın çelişkili cevaplar (halüsinasyon) vermesine sebep olur. Upsert mantığı ile eski veri anında yok edilerek sistemin her zaman en güncel gerçeği yansıtması sağlandı.

## Faz 4 - Hafta 8: Chunking Stratejisi
* **Karar:** LangChain `RecursiveCharacterTextSplitter` (chunk_size: 1000, overlap: 150)
* **Gerekçe:** Yönetmelikler yasal ve resmi metinler olduğu için cümle ortasında bölünmemesi çok kritiktir. Bu splitter, metni önce paragraflara sonra satırlara bölerek anlam bütünlüğünü maksimum seviyede korur. 150 karakterlik örtüşme (overlap) payı sayesinde ardışık parçalar arasındaki bağlam kaybı engellenmiştir.

## Faz 4 - Hafta 9: Embedding Modeli Seçimi
* **Karar:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (Lokal Açık Kaynak)
* **Gerekçe:** Yönetmeliklerimiz Türkçe olduğu için çok dilli (multilingual) bir modele ihtiyacımız var. `BAAI/bge-m3` kadar ağır olmayan ama Türkçe metinlerin anlamsal (semantik) bağını çok iyi yakalayabilen, CPU'da bile hızlı çalışan optimum model olarak bu seçilmiştir.


---

## Kapsamlı Gözden Geçirme ve Düzeltmeler (Ekim 2026)

Proje hızla büyüdü (3 → 185 doküman) ve bu arada başka bir asistanla (Gemini)
paralel geliştirme yapıldı. Tüm kod tabanı satır satır gözden geçirildi, şu
sorunlar bulundu ve düzeltildi:

### 🚨 Güvenlik (kritik, acil)
- `api/agent.py` içinde hardcoded Groq API anahtarı, `api/main.py` içinde
  hardcoded Gemini API anahtarı bulundu — ikisi de sohbet/dosya paylaşımı
  sırasında açığa çıktı. **İkisi de iptal edilip yenilendi**, artık `.env`
  dosyasından okunuyor (`.env.example` şablonu eklendi, `.gitignore`'a `.env`
  zaten ekliydi/eklendi).
- `.gitignore` dosyasının kendisi zip'te eksikti — `data/raw_documents/`
  (185 PDF) ve `data/chroma_db/` gibi büyük klasörlerin yanlışlıkla commit
  edilmesi riski vardı. Yeniden oluşturuldu, `chroma_db/` ve `mock_vectordb.json`
  gibi yeni üretilen dosyalar da eklendi.

### 🐛 Mantık hataları
- **`embedding/build_index.py` — "yetim chunk" hatası (en kritik bulgu):**
  Eski kod, chunk ID'lerini sabit tutarak (`dosya_chunk_0`, `dosya_chunk_1`...)
  upsert yapıyordu. Bu SADECE yeni versiyon eski versiyondan daha fazla/eşit
  chunk üretirse doğru çalışır. Doküman kısalırsa, fazla eski chunk'lar
  veritabanında kalıcı olarak kalır — tam olarak projenin başından beri
  kaçınmaya çalıştığımız "eski veri asla silinmesin" riski. Düzeltme: her
  dokümanı işlemeden önce o dokümana ait tüm eski chunk'lar `source_file`
  metadata'sına göre siliniyor, sonra temiz ekleniyor.
- **`ingestion/tracker.py` hiç kullanılmıyordu (ölü kod):** Hash tabanlı
  değişiklik tespiti yazılmıştı ama `parser.py` ona hiç başvurmuyordu; onun
  yerine "JSON zaten var mı" diye bakıyordu — yani bir kaynak dosya
  güncellense bile JSON zaten varsa yeniden işlenmiyordu. `parser.py`
  artık `tracker.get_new_or_updated_files()` kullanıyor.
- **`ingestion/pipeline.py` ve `quality/filter_pipeline.py` birebir aynıydı**
  (kopya-yapıştır). `ingestion/pipeline.py` silindi, kanonik versiyon
  `quality/filter_pipeline.py` olarak kaldı.
- **Hiçbir script birbirini çağırmıyordu** — `parser.py`, `filter_pipeline.py`,
  `build_index.py` hepsi bağımsız, elle sırayla çalıştırılması gereken
  scriptlerdi. `run_pipeline.py` eklendi — tek komutla (`python run_pipeline.py`)
  üçünü doğru sırada çalıştırıyor. (Airflow kullanmama kararımız hâlâ geçerli,
  bu sadece o kararın basit Python karşılığı.)
- **`.doc` dosyaları `python-docx` ile sessizce başarısız oluyordu**
  (kütüphane sadece `.docx` okuyabiliyor, eski binary `.doc` formatını değil).
  Artık açıkça loglanıp atlanıyor.

### 🔌 Mimari: web arama fallback'i bağlandı
- `api/agent.py`'deki web arama (DuckDuckGo) mantığı genelleştirilip
  (`web_arama()`) `api/main.py`'ye bağlandı: yerel ChromaDB'de kanıt
  bulunamazsa (veya LLM "bulamadım" derse) sistem web aramasına düşüyor.
  **Önemli:** bu durumda cevap açıkça "⚠️ web aramasından derlendi, resmi
  doküman değil" diye işaretleniyor ve `sources` alanı bunu yansıtıyor —
  kurumsal dokümana dayanan cevaplarla web'den gelen cevaplar asla
  karıştırılmıyor. Bu, "kanıt yoksa uydurma" ilkesini korurken pratik bir
  kapsam genişletmesi.

### 📦 Bağımlılıklar
- `requirements.txt` gerçekte kullanılan kütüphaneleri yansıtmıyordu
  (örn. `qdrant-client` yazıyordu ama proje `chromadb` kullanıyor;
  `pymupdf`, `prefect`, `langchain-*`, `google-genai`, `duckduckgo-search`,
  `streamlit` hiç listede yoktu). Güncellendi — artık sıfır bir ortamda
  `pip install -r requirements.txt` gerçekten çalışır durumda.

### Not: Model adları
- `api/main.py`'deki `gemini-3.8-flash` gerçek bir model adı değildi
  (muhtemelen halüsinasyon) → `gemini-3.1-flash-lite` ile değiştirildi
  (stabil, ucuz; `gemini-2.5-flash` ise 16 Ekim 2026'da kapatılıyor, o yüzden
  tercih edilmedi).
- `api/agent.py`'deki `qwen/qwen3.8-27b` kontrol edildi — bu gerçek bir
  Groq modeli, değiştirilmedi.

### Karar: Gemini kaldırıldı, tek sağlayıcı Groq
`main.py` başlangıçta Gemini kullanıyordu ama Gemini API anahtarı kurulumda
sürekli hata verdi ("AQ." ile başlayan anahtar — muhtemelen yanlış/eksik
oluşturulmuş bir Google AI Studio anahtarıydı, standart Gemini anahtarları
genelde "AIza..." ile başlar). Hata ayıklamaya zaman harcamak yerine, zaten
çalışan ve tek anahtarla iki yeri de (agent.py + main.py) besleyebilen Groq'a
geçildi. Artık `.env`'de tek bir `GROQ_API_KEY` yeterli — `google-genai`
bağımlılığı `requirements.txt`'ten çıkarıldı.


---

## Retrieval ve LLM katmanı kararları (Ekim–Kasım 2026)

**Yöntem notu:** Tek bir soruya bakarak ayar yapmak başka soruları bozdu. Bu yüzden `scripts/eval.py`
ile 17 soruluk bir arama testi kuruldu. Test cevap kalitesini değil, "doğru parça ilk 10'da geliyor
mu?" sorusunu ölçer. Sınırlar: soru sayısı az, aranan ifadeleri biz seçtik, ilk 3 soruda zaten ayar
yapmıştık. Sonuçlar iyimser olabilir.

1. **Embedding MiniLM yerine multilingual-e5-small.** MiniLM bir metnin yaklaşık ilk 128 token'ını
   okuyor, parçalar ise 1000 karakterdi. Bozuk karakterli Havacılık parçaları da sıralamayı kirletiyordu.
   Model değişince intörn yönergesinden gelen parça sayısı arttı. Sayısal önce/sonra ölçümü yok.
2. **Parçalama:** 800 karakter, 150 örtüşme, 80 karakterden kısa parçalar atılır, her parçanın başına
   doküman adı eklenir. PDF'lerdeki bozuk `൴` karakteri indeksleme sırasında `i` yapılır.
3. **Hibrit arama (BM25 + vektör, RRF), doküman başına en fazla 3 parça.** Neden: "intörn" gibi nadir
   bir kelimenin geçtiği tanım parçası anlamsal aramada 31. sıradaydı.
4. **Reranker (bge-reranker-v2-m3) denendi, bırakıldı.** CPU'da 22,6 sn sürdü ve hedef parçaları
   ilk 8'e taşımadı.
5. **HyDE yazıldı ama hiç uygulanıp ölçülmedi, ertelendi.**
6. **Sorgu genişletme: LLM yerine sabit sözlük.** Ölçüm: düz arama 14/17, sözlük 15/17, LLM
   45/51 (yaklaşık 15/17). Fark gürültü seviyesinde. Sözlük her seferinde aynı sonucu veriyor ve kota
   harcamıyor; LLM genişletme bir soruda 3/3'ten 1/3'e oynadı. Sınır: soru 17'yi LLM buluyor, sözlük bulmuyor.
7. **"Alttan ders" ile "devam zorunluluğu olan ders" aynı şey değildir** (kullanıcı düzeltmesi). Sözlük
   ikisini de arar ama eş anlam olarak yazmaz.
8. **Streamlit'te birim seçimi.** "İntörn" Tıp ve Veteriner'de intörn doktorluk, diğer birimlerde
   işyeri eğitimi demek. Birim, soruya otomatik eklenir.
9. **LLM: tek sağlayıcı Groq.** Gemini kaldırıldı (anahtar hata verdi, `gemini-3.8-flash` gerçek model
   değildi). Günlük limit model başına 200 bin token, bu yüzden zincir: qwen/qwen3.8-27b, openai/gpt-oss-120b,
   openai/gpt-oss-20b. `llama-3.1-8b-instant` hesapta yok (404).
10. **Web fallback: DuckDuckGo yerine Tavily.** DuckDuckGo boş içerik döndürüyordu. Web cevabı
    "resmi doküman değil" diye işaretlenir, veride olmayan bilgi uydurulmaz, çelişkide en yeni yıl seçilir.
11. **"Kanıt yok" tespiti** sadece cevap bu cümleyle başlıyorsa devreye girer (kelime aramasında yanlış
    pozitifler vardı). LLM `temperature=0`.
12. **Yerel LLM (Ollama) reddedildi:** RTX 3050 Ti 4 GB, boş RAM yaklaşık 2 GB.
13. **ChromaDB `<1.5`:** 1.5.x sürümü Windows'ta "Error loading hnsw index" veriyordu (kurulu: 1.4.1).
    OneDrive'dan taşınma bu sorunu çözmedi, sebep kütüphane hatasıydı.
14. **API anahtarları** `.env` dosyasında. Eski Groq ve Gemini anahtarları açığa çıktı, iptal edildiği
    doğrulanmadı.

**Bilinen açıklar:** Test sorusu 16 (Diş Hekimliği sınav türleri) hiçbir yöntemde bulunmuyor, nedeni
bilinmiyor. Soru 17 (işletmede mesleki eğitim başvuru şartları) sözlükle bulunmuyor. Taranmış PDF'ler
için OCR yok. Kalite kuralları bozuk karakterli metni yakalamıyor.

## Uçtan uca test ve retrieval düzeltmeleri (Kasım 2026)

15 gerçek öğrenci sorusuyla uçtan uca test yapıldı. Kök nedenler ölçümle ayrıldı:

1. **Sözlüğe "GNO" kuralı eklendi.** Soru 12 ("AKTS, GNO") doğru parçayı vektör 209, BM25 ~75. sıraya
   düşürüyordu. Aynı soru yönetmelik kelimeleriyle sorulunca ilk 6'ya giriyordu. Kısaltma metinde hiç geçmiyor.
2. **Doküman başına parça sınırı 3 → 5.** Çift anadal sorusunda aynı yönergenin 3 parçası sınırı doldurup
   hedef parçaları dışarıda bırakıyordu. Eval: sözlük 16/19 → 18/19, 1-15 satırlarında bozulma yok.
   Sınır 100 yapılınca ek kazanç yok.
3. **k=10 kaldı.** k=14 sadece 1 soruyu düzeltti, k=18 ikisini; ikisi de token maliyetini
   ~%40-80 artırır (tahmin). Soru 18 (genel mezuniyet şartı) açık: doğru parça 17. sırada.
4. **Sözlüğe Tıp için "dönem VI, altıncı sınıfa geçme, tüm sınavları tamamlama" eklendi.** "Alttan dersle
   intörn olunur mu" sorusunda belirleyici cümle Tıp Yönetmeliği'nde "6. sınıfa geçiş" diye geçiyor;
   soru ile cümle arasında ortak kelime yoktu (vektör 60, BM25 423). Düzeltmeden sonra cevap
   "Hayır" ve iki doküman gösteriyor.
5. **Web fallback tetikleyicisi:** "Kısa cevap:" talimatı "kanıt yok" cümlesiyle çakışıyordu. Prompt
   ve `_looks_like_no_evidence` düzeltildi. Kanıt yoksa yerel kaynak listesi boşaltılıyor.
6. **Kaynak listesi:** modelden "KULLANILAN: 1, 3" satırı isteniyor; okunamazsa tam liste gösteriliyor.
   Birimsiz soruda cevabın kısalması gözlendi, izlenecek.
7. **"Alttan ders" notu** artık sadece soruda "alttan" geçince prompt'a ekleniyor.
8. **Eval düzeltmesi:** hedef ifade "belge::ifade" biçiminde belge adıyla sınırlanabiliyor.
   Soru 18 önceden Tıp parçasıyla yanlış "var" veriyordu.

Sınır: sözlük kuralları ve eval soruları aynı sorular görüldükten sonra yazıldı, sonuçlar iyimser.
Açık: soru 16 (Diş Hekimliği sınav türleri), soru 18, Öğrenci Disiplin Yönetmeliği korpusta yok.

9. **e5-base denendi, geri alındı.** Sözlük 19/22 → 16/22 (2, 5, 9 bozuldu), hedef sorular (18, 19, 22)
   düzelmedi. e5-small'a göre ayarlanmış sözlük kuralları e5-base'de aynı etkiyi vermedi (tahmin).
10. **"yandal → yan dal" yazım düzeltmesi denendi, geri alındı.** Soru 22 düzelmedi, soru 19 bozuldu.
    Yan dal başvuru parçası (Yandal Yönergesi Madde 6): "çift anadal ve yandal" sorusunda vektör 39,
    BM25 15; yalnızca yan dalı soran sorguda vektör 3, BM25 2. Çift programlı sorularda parçalar
    birbiriyle yarışıyor (tahmin). Açık sorun: soru parçalama (query decomposition) ertelendi, LLM çağrısı maliyeti.
11. **Cevap hatası (doğrulandı):** yandal başvuru şartı sorulduğunda model, ilişik kesme maddesindeki 2,30'u
    başvuru şartı gibi sundu; doğru şart Madde 6'da 2,50.