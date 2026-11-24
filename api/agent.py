import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

load_dotenv()

# 1. API KURULUMU — anahtar artık .env dosyasından okunuyor, kodda yazmıyoruz
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY bulunamadı. Proje köküne bir .env dosyası oluşturup "
        "içine GROQ_API_KEY=... satırını ekle (bkz. .env.example)."
    )

client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

SECILEN_MODEL = "qwen/qwen3.8-27b"


def web_arama(sorgu: str, baglam: str = "Necmettin Erbakan Üniversitesi") -> str:
    """Tavily ile web araması. Önce üniversitenin kendi sitesinde, bulunamazsa genel webde arar."""
    print(f"\n🕵️ Web araması çalıştırılıyor: '{sorgu}'...")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Arama sırasında hata: TAVILY_API_KEY .env dosyasında bulunamadı."

    tavily = TavilyClient(api_key=api_key)
    # soruda zaten üniversite adı geçiyorsa tekrar ekleme
    if baglam and baglam.lower() not in sorgu.lower():
        search_query = f"{baglam} {sorgu}"
    else:
        search_query = sorgu

    try:
        results = []
        # 1. önce üniversitenin kendi sitesinde ara (daha güvenilir)
        resp = tavily.search(query=search_query, max_results=5,
                             search_depth="advanced",
                             include_domains=["erbakan.edu.tr"])
        results = resp.get("results", [])

        # 2. orada yoksa genel webe çık
        if not results:
            resp = tavily.search(query=search_query, max_results=5,
                                 search_depth="advanced")
            results = resp.get("results", [])

        if not results:
            return "İnternette güncel bir bilgi bulunamadı."

        print(f"🔍 [DEBUG] Ham sonuç sayısı: {len(results)}")
        parcalar = []
        for i, r in enumerate(results):
            print(f"  [{i}] {r.get('url','')[:80]}")
            icerik = (r.get("content") or "").strip()
            if icerik:
                parcalar.append(f"[{r.get('title','')}] (kaynak: {r.get('url','')}) {icerik}")

        canli_veri = "\n\n".join(parcalar)
        if not canli_veri:
            return "Arama sonuç döndürdü ama içerik boş geldi."

        print(f"📡 [Bulunan Veri]: {canli_veri[:150]}...")
        return canli_veri
    except Exception as e:
        return f"Arama sırasında hata: {str(e)}"


def bolum_baskani_bul(bolum_adi: str) -> str:
    """Özel amaçlı sarmalayıcı — dekan/bölüm başkanı sorguları için web_arama()'yı kullanır."""
    return web_arama(f"{bolum_adi} dekanı bölüm başkanı")


tools = [{
    "type": "function",
    "function": {
        "name": "bolum_baskani_bul",
        "description": "Üniversitedeki bir bölümün başkanını, dekanını veya akademik personelini bulmak için internette arama yapar.",
        "parameters": {
            "type": "object",
            "properties": {
                "bolum_adi": {"type": "string", "description": "Arama yapılacak bölüm veya fakülte adı"}
            },
            "required": ["bolum_adi"]
        }
    }
}]


# --- YÖNLENDİRİCİ MOTOR (bağımsız CLI testi için) ---
def soru_sor(kullanici_mesaji: str):
    print(f"\nSoru: {kullanici_mesaji}")
    print("Düşünülüyor...")

    messages = [
        {"role": "system", "content": "Sen Necmettin Erbakan Üniversitesi için yazılmış zeki bir asistansın. Sana araçlardan gelen veriyi okuyup cevabı doğrudan ver. Asla kullanıcıya 'kendiniz arayın' deme."},
        {"role": "user", "content": kullanici_mesaji}
    ]

    response = client.chat.completions.create(
        model=SECILEN_MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)

        for tool_call in tool_calls:
            if tool_call.function.name == "bolum_baskani_bul":
                fonksiyon_argumanlari = json.loads(tool_call.function.arguments)
                canli_veri = bolum_baskani_bul(bolum_adi=fonksiyon_argumanlari.get("bolum_adi"))

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": canli_veri,
                })

        son_cevap = client.chat.completions.create(
            model=SECILEN_MODEL,
            messages=messages
        )
        print(f"\n🤖 DocFlow: {son_cevap.choices[0].message.content}")

    else:
        print(f"\n🤖 DocFlow: {response_message.content}")

    print("-" * 50)


if __name__ == "__main__":
    soru_sor("Necmettin Erbakan Üniversitesi Seydişehir Ahmet Cengiz Mühendislik Fakültesi Dekanı kimdir?")
