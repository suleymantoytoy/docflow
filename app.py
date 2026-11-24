import streamlit as st
import requests
import re

# Arka planda çalışan FastAPI sunucumuzun adresi
API_URL = "http://127.0.0.1:8000/ask"

BIRIMLER = [
    "Belirtmek istemiyorum",
    "Seydişehir Ahmet Cengiz Mühendislik Fakültesi",
    "Mühendislik Fakültesi (Konya)",
    "Tıp Fakültesi",
    "Diş Hekimliği Fakültesi",
    "Veteriner Fakültesi",
    "Hemşirelik Fakültesi",
    "Sağlık Bilimleri Fakültesi",
    "Turizm Fakültesi",
    "Havacılık ve Uzay Bilimleri Fakültesi",
    "Ahmet Keleşoğlu Eğitim Fakültesi",
    "Ahmet Keleşoğlu İlahiyat Fakültesi",
    "Güzel Sanatlar ve Mimarlık Fakültesi",
    "Sosyal ve Beşeri Bilimler Fakültesi",
    "Fen Fakültesi",
    "Uygulamalı Bilimler Fakültesi",
    "Meslek Yüksekokulu",
    "Lisansüstü Eğitim (Enstitüler)",
]

st.set_page_config(page_title="DocFlow Asistanı", page_icon="📚")
st.title("📚 DocFlow Kurumsal Yönetmelik Asistanı")
st.markdown("Necmettin Erbakan Üniversitesi yönetmelikleri hakkında sorularınızı sorabilirsiniz.")

# Kenar çubuğu: birim seçimi (aynı kelime farklı birimlerde farklı anlam taşıyabilir,
# örn. "intörn" Tıp'ta intörn doktorluk, mühendislikte işyeri eğitimi)
birim = st.sidebar.selectbox("Hangi birimdensiniz?", BIRIMLER)
st.sidebar.caption("Birim seçerseniz cevaplar o birimin yönergelerine göre daha isabetli olur.")

# Sohbet geçmişini hafızada tut
if "messages" not in st.session_state:
    st.session_state.messages = []

# Geçmiş mesajları ekrana çiz
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            st.caption(f"**Kaynaklar:** {', '.join(message['sources'])}")

# Kullanıcıdan yeni soru al
if prompt := st.chat_input("Yönetmeliklerle ilgili bir soru sorun... (Örn: Öğrenci kurulu kimlerden oluşur?)"):

    # Kullanıcı mesajını ekrana yaz ve geçmişe kaydet (sadece yazdığı hali)
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # API'ye giden soruya birim bilgisini ekle
    api_prompt = prompt
    # "intörn" Tıp ve Veteriner'de intörn doktorluk, diğer birimlerde işyeri eğitimi/staj
    # demek; yönergeler resmi terimi kullanıyor.
    if birim not in ("Belirtmek istemiyorum", "Tıp Fakültesi", "Veteriner Fakültesi"):
        api_prompt = re.sub(r"\b[iİ]nt[öo]rn\w*", "işyeri eğitimi (intörn)", prompt)

    if birim != "Belirtmek istemiyorum":
        api_sorusu = f"{birim} öğrencisiyim. {api_prompt}"
    else:
        api_sorusu = api_prompt

    with st.chat_message("assistant"):
        with st.spinner("Yönetmelikler taranıyor..."):
            try:
                response = requests.post(API_URL, json={"question": api_sorusu}, timeout=120)

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "Bir hata oluştu, cevap boş.")
                    sources = data.get("sources", [])

                    st.markdown(answer)
                    if sources:
                        st.caption(f"**Kaynaklar:** {', '.join(sources)}")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources
                    })
                else:
                    st.error(f"Sunucudan hata döndü: {response.status_code}")

            except requests.exceptions.ConnectionError:
                st.error("Arka plan sunucusuna bağlanılamadı! FastAPI (Uvicorn) sunucusunun diğer terminalde çalıştığından emin olun.")
            except requests.exceptions.Timeout:
                st.error("Sunucu zamanında cevap vermedi, lütfen tekrar deneyin.")