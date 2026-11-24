"""
Faz 6 - Hafta 10: FastAPI Soru-Cevap Endpoint'i
Retrieval: hibrit arama (vektör + BM25) üzerinden yerel ChromaDB
LLM: Groq (OpenAI-uyumlu istemci)
Soru önce yönetmelik diliyle anahtar kelimelere genişletilir (sorgu genişletme).
Yerel cevap yoksa web aramasına düşülür; sonuç her durumda kullanıcıya gösterilir.
"""
import os
import re
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb
from openai import OpenAI

from embedding.model import load_embeddings
from embedding.hybrid import HybridRetriever, sozluk_genislet, tr_lower
from api.takvim import takvim_baglami
from api.agent import web_arama, SECILEN_MODEL

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY bulunamadı. Proje köküne bir .env dosyası oluşturup "
        "içine GROQ_API_KEY=... satırını ekle (bkz. .env.example)."
    )
llm_client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

WEB_ARAMA_BASARISIZ_KALIPLARI = ["hata", "bulunamadı", "boş geldi"]

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DB_DIR = BASE_DIR / "data" / "chroma_db"

app = FastAPI(title="DocFlow RAG API", description="Kurumsal Yönetmelik Asistanı")

print("Sistem ayağa kalkıyor... Modeller ve Veritabanı yükleniyor...")
embeddings = load_embeddings()
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
collection = chroma_client.get_collection(name="yonetmelikler")
retriever = HybridRetriever(collection, embeddings)


class QueryRequest(BaseModel):
    question: str


MODEL_SIRASI = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
HAFIF_MODEL_SIRASI = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]


def _call_llm(prompt: str, models=None) -> str:
    """Modelleri sırayla dener; biri limite takılırsa/hata verirse sıradakine geçer."""
    son_hata = None
    for model in (models or MODEL_SIRASI):
        try:
            response = llm_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            print(f"🤖 [MODEL]: {model}")
            return response.choices[0].message.content
        except Exception as e:
            son_hata = e
            print(f"⚠️ [{model} BAŞARISIZ]: {str(e)[:120]}")
    raise son_hata


def _sorgu_genislet(question: str) -> str:
    """Günlük dildeki soruyu, yönetmelik dilindeki anahtar kelimelere çevirir."""
    prompt = f"""Aşağıdaki öğrenci sorusunu, üniversite yönetmelik/yönerge metinlerinde
arama yapmak için 8-12 kelimelik bir anahtar kelime sorgusuna çevir.
Günlük dildeki ifadeleri yönetmelik dilindeki karşılıklarıyla birlikte yaz.
Örnekler:
- "alttan ders" (daha önce alınıp başarısız olunan ders; "devam zorunluluğu olan ders" ile AYNI ŞEY DEĞİLDİR) -> "başarısız ders, ders tekrarı, devam şartı, devam zorunluluğu"
- "intörn" veya "staj" (tıp dışı bölümler için) -> "işyeri eğitimi, işletmede mesleki eğitim, staj, uygulamalı eğitim, başvuru koşulları"
Soru hangi bölümle ilgili olduğunu belirtmiyorsa hem tıp (intörn doktorluk) hem
diğer bölümlerin (işyeri eğitimi, staj) terimlerini ekle.
Sadece anahtar kelimeleri yaz, başka açıklama yazma.

SORU: {question}
ANAHTAR KELİMELER:"""
    try:
        yanit = _call_llm(prompt, models=HAFIF_MODEL_SIRASI)
        yanit = re.sub(r"<think>.*?</think>", "", yanit, flags=re.S).strip()
        return yanit[:200]
    except Exception as e:
        print(f"[SORGU GENİŞLETME HATASI]: {e}")
        return ""

def _kullanilan_kaynaklar(answer: str, sources: list):
    """Modelin 'KULLANILAN: 1, 3' satırını ayıklar; okunamazsa tüm listeyi döner."""
    a = answer.strip()
    m = re.search(r"\**KULLANILAN:\s*([\d,\s]+)\**\s*$", a)
    if not m:
        return answer, sources
    secilen = [sources[int(n) - 1] for n in re.findall(r"\d+", m.group(1))
               if 0 < int(n) <= len(sources)]
    return a[:m.start()].rstrip(), (list(dict.fromkeys(secilen)) or sources)

def _looks_like_no_evidence(answer: str) -> bool:
    # Sadece cevap tamamen "bulunmamaktadır" cümlesiyle başlıyorsa kanıt yok say.
    a = answer.strip().lower()
    if a.startswith("kısa cevap:"):
        a = a[len("kısa cevap:"):].strip()
    return a.startswith("bu bilgi verilen dokümanlarda bulunmamaktadır")


def _web_arama_basarisiz_mi(web_veri: str) -> bool:
    kisa = web_veri.lower()[:30]
    return any(kalip in kisa for kalip in WEB_ARAMA_BASARISIZ_KALIPLARI)


def _is_overload_error(e: Exception) -> bool:
    msg = str(e).lower()
    status = getattr(e, "status_code", None)
    return status == 503 or "unavailable" in msg or "overloaded" in msg or "rate limit" in msg

TAKVIM_RE = re.compile(
    r"akademik takvim|(final|vize|ara sınav|bütünleme|genel sınav|ders kaydı|"
    r"kayıt yenileme).{0,40}(tarih|ne zaman|hangi gün)|"
    r"ne zaman.{0,40}(final|vize|ara sınav|bütünleme|genel sınav)")


def _takvim_cevabi(question: str):
    """Takvim sorusu: resmî PDF'ten cevap; alınamazsa resmî sayfaya yönlendirir."""
    sonuc = takvim_baglami(question)
    if sonuc:
        metin, yil, _url = sonuc
        prompt = f"""
        Bugünün tarihi: {date.today().isoformat()}
        Aşağıda Necmettin Erbakan Üniversitesi'nin {yil} akademik takviminden alınmış
        bölümler var. Bu, ön lisans/lisans/lisansüstü için genel üniversite takvimidir.
        Soruyu YALNIZCA bu metne dayanarak cevapla. Tarihleri olduğu gibi yaz, tahmin etme.
        Güz ve bahar yarıyıllarının ikisi de ilgiliyse ikisini de ver; bugünün tarihine göre
        hangisinin yaklaştığını belirt. "Final" soruluyorsa takvimdeki "Genel Sınav" (ve
        istenirse "Bütünleme Sınavı") satırlarını kullan; "vize" için "Ara Sınav".
        Ortak ders sınavları ayrı satırlardır, soruyla ilgiliyse ayrıca belirt.
        Metinde yoksa "Bu bilgi takvimde bulunmamaktadır." yaz.
        Cevabın sonuna şu notu ekle: "Bazı fakültelerin (örn. Tıp, Hukuk) ayrı takvimi
        olabilir; kendi biriminizin duyurularını da kontrol edin."

        TAKVİM METNİ:
        {metin}

        SORU: {question}

        CEVAP:
        """
        try:
            return {"question": question, "answer": _call_llm(prompt),
                    "sources": [f"🌐 {yil} Akademik Takvimi (erbakan.edu.tr/tr/akademik-takvim)"]}
        except Exception as e:
            print(f"[TAKVİM LLM HATASI]: {e}")
    return {
        "question": question,
        "answer": ("Sınav, kayıt ve ders tarihleri her yıl ve her fakülte/yüksekokul için ayrı "
                   "yayımlanır ve değişebilir; yanlış bilgi vermemek için tarih söylemiyorum. "
                   "Güncel akademik takvim için https://erbakan.edu.tr/tr/akademik-takvim "
                   "sayfasına ve kendi biriminizin duyurular sayfasına bakın, ya da öğrenci "
                   "işlerine danışın."),
        "sources": ["🌐 erbakan.edu.tr/tr/akademik-takvim"],
    }
@app.post("/ask")
def ask_question(request: QueryRequest):
    question = request.question
    print(f"\n❓ [SORU]: {question}")
        # Tarih/takvim soruları: tarihler her yıl ve fakülte için değişir, tahmin yürütme,
    # resmi takvime yönlendir.
    if re.search(r"akademik takvim|(final|vize|ara sınav|bütünleme|genel sınav|ders kaydı|"
                 r"kayıt yenileme).{0,40}(tarih|ne zaman|hangi gün)|"
                 r"ne zaman.{0,40}(final|vize|ara sınav|bütünleme|genel sınav)",
                 tr_lower(question)):
                sonuc = takvim_baglami(question)
    if sonuc:
            metin, yil, url = sonuc
            takvim_prompt = f"""
            Bugünün tarihi: {date.today().isoformat()}
            Aşağıda Necmettin Erbakan Üniversitesi'nin {yil} akademik takviminden alınmış
            bölümler var. Bu, ön lisans/lisans/lisansüstü için genel üniversite takvimidir.
            Soruyu YALNIZCA bu metne dayanarak cevapla. Tarihleri olduğu gibi yaz, tahmin etme.
            Güz ve bahar yarıyıllarının ikisi de ilgiliyse ikisini de ver; bugünün tarihine göre
            hangisinin yaklaştığını belirt. "Final" soruluyorsa takvimdeki "Genel Sınav" (ve
            istenirse "Bütünleme Sınavı") satırlarını kullan; "vize" için "Ara Sınav".
            Ortak ders sınavları ayrı satırlardır, soruyla ilgiliyse ayrıca belirt.
            Metinde yoksa "Bu bilgi takvimde bulunmamaktadır." yaz.
            Cevabın sonuna şu notu ekle: "Bazı fakültelerin (örn. Tıp, Hukuk) ayrı takvimi
            olabilir; kendi biriminizin duyurularını da kontrol edin."

            TAKVİM METNİ:
            {metin}

            SORU: {question}

            CEVAP:
            """
            try:
                cevap = _call_llm(takvim_prompt)
                return {"question": question, "answer": cevap,
                        "sources": [f"🌐 {yil} Akademik Takvimi (erbakan.edu.tr/tr/akademik-takvim)"]}
            except Exception as e:
                print(f"[TAKVİM LLM HATASI]: {e}")
            return {
            "question": question,
            "answer": ("Sınav, kayıt ve ders tarihleri her yıl ve her fakülte/yüksekokul için ayrı "
                       "yayımlanır ve değişebilir; yanlış bilgi vermemek için tarih söylemiyorum. "
                       "Güncel akademik takvim için üniversitenin akademik takvim sayfasına "
                       "(https://erbakan.edu.tr/tr/akademik-takvim) ve kendi biriminizin duyurular "
                       "sayfasına bakın, ya da öğrenci işlerine danışın."),
            "sources": ["🌐 erbakan.edu.tr/tr/akademik-takvim"],
        }

    # 0. Soruyu yönetmelik diliyle anahtar kelimelere genişlet
    genis = sozluk_genislet(question)
    print(f"\n🔎 [SÖZLÜK GENİŞLETME]: {genis or '(yok)'}")

    # 1. RETRIEVAL — hibrit arama (vektör + BM25)
    # "X kimdir?" (güncel görevli) soruları yönetmelik metinlerinde cevaplanamaz,
    # doğrudan web aramasına gidilir.
    web_dogrudan = bool(re.search(r"\bkimdir\b", question.lower()))
    hits = [] if web_dogrudan else retriever.search(
        question, k=10, extra_queries=[genis] if genis else [])

    local_context = ""
    local_sources = []
    for _cid, doc, metadata in hits:
        source_file = metadata.get("source_file", "Bilinmeyen Kaynak")
        if source_file not in local_sources:
            local_sources.append(source_file)
        no = local_sources.index(source_file) + 1
        local_context += f"\n--- Kaynak {no}: {source_file} ---\n{doc}\n"
    print(f"📚 [GETİRİLEN]: {len(hits)} parça → {local_sources}")
    print(f"🧩 [PARÇA ID]: {[cid.rsplit('_chunk_', 1)[0][:25] + '#' + cid.rsplit('_chunk_', 1)[1] for cid, _d, _m in hits]}")

    local_answer = None

    if local_context:
        alttan_notu = ""
        if "alttan" in question.lower():
            alttan_notu = ('Not: "alttan ders", daha önce alınıp başarısız olunan derstir; "devam '
                           'zorunluluğu olan ders" ile aynı şey değildir. Kanıtlarda devam zorunluluğu '
                           'şartı geçiyorsa, alttan dersin devam zorunluluğu taşıyıp taşımadığını '
                           'kanıtlara göre ayrıca değerlendir; kanıtlarda bu ayrım yoksa bunu belirt.')
        prompt = f"""
        Sen kurumun resmi yönetmelikleri üzerinde çalışan bir yapay zeka asistanısın.
        Aşağıda sana bazı resmi belgelerden kesitler (kanıtlar) verilmiştir.
        Kullanıcının sorusunu YALNIZCA bu verilen kanıtlara dayanarak cevapla.
        Kanıtlardaki tanım ve koşullardan açıkça ÇIKAN sonuçları da söyleyebilirsin;
        çıkarım yaptıysan bunu "Tanıma göre..." diye belirt. Farklı fakülte veya
        birimleri ilgilendiren kanıtlar varsa her birini ayrı belirt.
        {alttan_notu}
        Kanıtlarda soruyla ilgili HİÇBİR bilgi yoksa "Kısa cevap:" yazma, cevabın
        tamamı yalnızca şu cümle olsun: "Bu bilgi verilen dokümanlarda bulunmamaktadır."
        Tahmin yürütme.
        Cevaba 1-2 cümlelik net bir sonuçla ("Kısa cevap: ...") başla, ardından
        gerekçeyi ve dayandığın maddeyi yaz.
        Cevap metninde "Kaynak 1" gibi numara kullanma, doküman adını yaz.
        Numaraları yalnızca en son satırda, gerçekten dayandığın kaynakları
        belirtmek için şu biçimde kullan: "KULLANILAN: 1, 3". Kanıt yoksa bu satırı ekleme.
        KANITLAR:
        {local_context}

        SORU: {question}

        CEVAP:
        """
        try:
            local_answer = _call_llm(prompt)
            local_answer, local_sources = _kullanilan_kaynaklar(local_answer, local_sources)
            print(f"\n📝 [YEREL CEVAP]: {local_answer}\n")
            print(f"📎 [KULLANILAN KAYNAK]: {local_sources}")
        except Exception as e:
            print(f"\n[LLM HATASI]: {e}\n")
            if _is_overload_error(e):
                return {
                    "question": question,
                    "answer": "Yapay zeka sunucuları şu an yoğunluk sebebiyle yanıt veremiyor. "
                               "Ancak sorduğunuz soruyla ilgili yönetmelik maddelerini aşağıda "
                               "bulabilirsiniz:\n\n" + local_context,
                    "sources": local_sources,
                }
            print(f"\n[API HATASI DETAYI]: {e}\n")
            raise HTTPException(status_code=500, detail=f"LLM hatası: {e}")

    # 2. Yerel cevap yeterliyse direkt onu dön — gereksiz web çağrısı yapma
    if local_answer and not _looks_like_no_evidence(local_answer):
        return {"question": question, "answer": local_answer, "sources": local_sources}

    # Buraya gelindiyse yerel cevap kanıt bulamadı: o parçalar cevaba dayanmıyor,
    # kaynak olarak gösterme.
    local_sources = []

    # 3. Yerel cevap yok: web'de ara (genişletilmiş anahtar kelimelerle)
       # "X öğrencisiyim." ön eki arama motorunu birim tanıtım sayfalarına çekiyor, aramadan çıkar
    arama_sorgusu = re.sub(r"^.{0,80}?öğrencisiyim\.\s*", "", question)
    print(f"\n🌐 [FALLBACK] Web aramasına düşülüyor: '{arama_sorgusu}'")
    web_veri = web_arama(arama_sorgusu)

    if _web_arama_basarisiz_mi(web_veri):
        return {
            "question": question,
            "answer": (local_answer or "Bu bilgi kurumsal dokümanlarda bulunamadı.")
                      + "\n\n🌐 Web aramasında da bu soruya dair bir bilgi bulunamadı.",
            "sources": local_sources,
        }

    web_prompt = f"""
    Bugünün tarihi: {date.today().isoformat()}
    Aşağıda bir web aramasından elde edilmiş ham, doğrulanmamış bilgi var.
    Bu bilgiyi kullanarak soruyu kısaca ve net şekilde cevapla.
    KURALLAR:
    1) Cevap SADECE web verisinde açıkça yazan bilgiye dayanmalı. Bir detay
       veride GEÇMİYORSA UYDURMA; "Web aramasında bu sorunun net cevabı
       bulunamadı." yaz.
    2) Bir görevde birden fazla kişi olabilir (örn. iki dekan yardımcısı).
       Aynı görev için birden fazla isim listelenmişse hepsini yaz.
    3) Kaynaklar çelişirse EN GÜNCEL olanı seç: metinde geçen en yeni yıl/tarihi
       taşıyan kaynağı tercih et (örn. 2024 tarihli bir rapor, eski bir haber
       veya bülten yazısından günceldir). "Yrd. Doç. Dr." gibi eski unvanlar
       ve eski haberlerdeki isimler güncel olmayabilir.
    4) Çelişki varsa cevabın sonuna kısa bir not ekle.
    4b) Veri birden fazla birim veya yıl için farklı tarihler içeriyorsa
       "net cevap bulunamadı" DEME; bugünün tarihine en yakın ve geçerli
       dönemi seç, birim adını belirterek tarihleri yaz ve hangi birim/yıl
       için olduğunu açıkça söyle.
    4c) Cevabın sonunda dayandığın sayfanın adresini (kaynak: ...) yaz.
       "Web aramasında bu sorunun net cevabı bulunamadı." yaz. "WEB VERİSİ"
       gibi etiketleri cevapta tekrarlama.
    Sadece cevabı yaz, başka açıklama/uyarı ekleme.

    WEB VERİSİ:
    {web_veri}

    SORU: {question}

    CEVAP:
    """
    try:
        web_answer = _call_llm(web_prompt)
        print(f"\n🌐 [WEB CEVAP HAM]: {web_answer[:700]}\n")
    except Exception as e:
        print(f"\n[WEB FALLBACK LLM HATASI]: {e}\n")
        final_answer = local_answer or ("Web aramasından elde edilen ham veri:\n\n" + web_veri)
        return {"question": question, "answer": final_answer, "sources": local_sources}

    if "net cevabı bulunamadı" in web_answer:
        return {
            "question": question,
            "answer": (local_answer or "Bu bilgi kurumsal dokümanlarda bulunamadı.")
                      + "\n\n🌐 Web aramasında da net bir cevap bulunamadı.",
            "sources": local_sources,
        }

    web_disclaimer = ("⚠️ Aşağıdaki ek bilgi kurumsal yönetmelik dokümanlarında bulunamadı, "
                       "genel web aramasından derlendi — resmi teyit için ilgili birimle doğrulayın.")

    if local_answer:
        combined_answer = (
            f"{local_answer}\n\n---\n{web_disclaimer}\n\n🌐 **Web'den ek bilgi:**\n{web_answer}"
        )
        return {
            "question": question,
            "answer": combined_answer,
            "sources": local_sources + ["🌐 Web araması (resmi doküman değil)"],
        }

    return {
        "question": question,
        "answer": f"{web_disclaimer}\n\n{web_answer}",
        "sources": ["🌐 Web araması (resmi doküman değil)"],
    }