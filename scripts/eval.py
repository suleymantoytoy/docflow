"""
Retrieval değerlendirmesi: LLM cevabı üretmez, sadece "doğru parça getiriliyor mu?" ölçer.
Her soru için, cevabın geçtiği parçadan bir ifade belirlenmiştir; ilk K sonuçtan biri bu
ifadeyi içeriyorsa isabet sayılır. Sorgu genişletme LLM kullandığı için kararsızdır,
RUNS kez tekrarlanır.

Kullanım:
    python scripts/eval.py            # K=10, 3 tekrar
    python scripts/eval.py --k=14     # parça sayısını değiştirip karşılaştır
"""
import contextlib
import io
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from embedding.hybrid import tr_lower, sozluk_genislet
from api.main import retriever, _sorgu_genislet

import functools

K, RUNS, MAXDOC = 10, 3, 5
for a in sys.argv[1:]:
    if a.startswith("--k="):
        K = int(a[4:])
    elif a.startswith("--runs="):
        RUNS = int(a[7:])
    elif a.startswith("--maxdoc="):
        MAXDOC = int(a[9:])
retriever.search = functools.partial(retriever.search, max_per_doc=MAXDOC)

ALTTAN = "Alttan dersim varken intörn yapabilir miyim?"
SEYDI = "Seydişehir Ahmet Cengiz Mühendislik Fakültesi"
HIC = "Belirtmek istemiyorum"

# (birim, soru, [cevabın geçtiği parçada aranacak ifadelerden herhangi biri])
SORULAR = [
    ("Tıp Fakültesi", ALTTAN, ["stajlarını tamamlamış"]),
    ("Mühendislik Fakültesi (Konya)", ALTTAN,
     ["devam zorunluluğu olan dersi bulunmaması", "devam zorunluluğu gerektiren dersin bulunmaması"]),
    (SEYDI, ALTTAN,
     ["devam zorunluluğu gerektiren dersin bulunmaması", "devam zorunluluğu olan dersi bulunmaması"]),
    (HIC, "Mezuniyet aşamasındayım ve başarısız olduğum tek bir ders var. Sınırsız sınav hakkından nasıl yararlanabilirim?",
     ["bütünleme sınavını takip eden bir ay"]),
    (HIC, "Tek ders sınavı için öğrenim ücreti ödenir mi?", ["katkı payı alınmaz"]),
    ("Turizm Fakültesi", "İşbaşı eğitimi sırasında alttan ders alabilir miyim?",
     ["alttan ya da üstten alamazlar"]),
    ("Meslek Yüksekokulu", "İşyeri eğitiminden DC alırsam ne olur?",
     ["DC ve daha düşük not alan öğrenciler"]),
    ("Veteriner Fakültesi", "Veteriner fakültesinde intörn programı hangi yarıyıllarda alınır?",
     ["IX. ve X. yarıyıllarda"]),
    ("Veteriner Fakültesi", "Veteriner intörn programında devam şartı nedir?",
     ["uygulamaların toplamının en az"]),
    ("Tıp Fakültesi", "İntörn doktorluk döneminde devamsızlık sınırı nedir?",
     ["o stajdan başarısız sayılır"]),
    ("Tıp Fakültesi", "İntörn doktorluk dönemi ne kadar sürer?", ["12 (on iki) aylık"]),
    ("Mühendislik Fakültesi (Konya)", "İşyeri eğitiminden kalırsam tek ders sınavına girebilir miyim?",
     ["bütünleme sınav veya tek ders hakkı tanınmaz"]),
    ("Mühendislik Fakültesi (Konya)", "İşyeri eğitimi kaç hafta sürer?", ["en az 14 hafta"]),
    (SEYDI, "İşletmede mesleki eğitim programı zorunlu mu?", ["seçmeli bir programdır"]),
    (HIC, "Üniversiteden ayrılırken kütüphane ile ilişik kesmek için ne gerekir?",
     ["ilişiklerinin olmadığına dair belge"]),
    ("Diş Hekimliği Fakültesi", "Diş Hekimliği Fakültesinde hangi sınav türleri vardır?",
     ["klinik uygulama sınavları"]),
    (SEYDI, "İşletmede mesleki eğitime başvurmak için hangi şartlar gerekir?",
     ["ilk 6 yarıyıldaki tüm derslerini"]),
    (HIC, "Mezuniyet için gereken şartlar nelerdir (AKTS, GNO)?",
     ["ön lisans ve lisans::mezuniyet ağırlıklı not ortalamasının en az 2,00"]),
    (HIC, "Çift anadal ve yandal için not ortalaması şartı nedir?",
     ["genel not ortalamasının 4.00 üzerinden en az 3.00"]),
    (HIC, "Mezuniyet için GNO kaç olmalı?",
     ["ön lisans ve lisans::mezuniyet ağırlıklı not ortalamasının en az 2,00"]),
    ("Tıp Fakültesi", ALTTAN,
     ["tıp fakültesi eğitim::tüm sınavlarını beşinci sınıfta tamamlamadan altıncı sınıfa geçemezler"]),
    (HIC, "Çift anadal ve yandal için not ortalaması şartı nedir?",
     ["yandal::genel not ortalamasının 4.00 üzerinden en az 2,50"]),
    (HIC, "Devamsızlık sınırı nedir, sınırı aşarsam ne olur?",
     ["ön lisans ve lisans::fazlasına devam etmeyen ve uygulamalarda başarılı olamayan öğrenci o dersin sınavlarına giremez"]),
]


def norm(s):
    return " ".join(tr_lower(s).split())


def api_sorusu(birim, prompt):
    """app.py'deki soru hazırlama mantığının aynısı."""
    p = prompt
    if birim not in (HIC, "Tıp Fakültesi", "Veteriner Fakültesi"):
        p = re.sub(r"\b[iİ]nt[öo]rn\w*", "işyeri eğitimi (intörn)", prompt)
    return p if birim == HIC else f"{birim} öğrencisiyim. {p}"


def ilk_isabet(hits, ifadeler):
    # ifade "belge::ifade" biçimindeyse parçanın o belgeden gelmesi de şart
    hedefler = [norm(i) for i in ifadeler]
    for sira, (_cid, doc, m) in enumerate(hits, 1):
        t = norm(doc)
        ad = norm(m.get("source_file", ""))
        for h in hedefler:
            belge, _, ifade = h.rpartition("::")
            if ifade in t and (not belge or belge in ad):
                return sira
    return None



def birlesik(q, genis, k=K, taban=6):
    """Düz aramanın ilk `taban` sonucu aynen korunur; kalan yerleri genişletme doldurur."""
    if not genis:
        return retriever.search(q, k=k)
    secilen = list(retriever.search(q, k=taban))
    gorulen = {c for c, _d, _m in secilen}
    for h in retriever.search(q, k=3 * k, extra_queries=[genis]):
        if h[0] not in gorulen:
            secilen.append(h)
            gorulen.add(h[0])
        if len(secilen) >= k:
            break
    return secilen


def ev(b):
    return "var" if b else "YOK"


print(f"\nK={K} parça | LLM genişletme {RUNS} tekrar\n")
print(f"{'#':>2}  {'soru':30} {'düz':7} {'sözlük':7} {'düz+söz':8} {'LLM':6} düz+LLM")

top = {"duz": 0, "soz": 0, "bsoz": 0, "llm": 0, "bllm": 0}
for i, (birim, soru, ifadeler) in enumerate(SORULAR, 1):
    q = api_sorusu(birim, soru)
    s = sozluk_genislet(q)

    duz = ilk_isabet(retriever.search(q, k=K), ifadeler) is not None
    soz = ilk_isabet(retriever.search(q, k=K, extra_queries=[s] if s else []), ifadeler) is not None
    bsoz = ilk_isabet(birlesik(q, s), ifadeler) is not None

    llm = bllm = 0
    for _ in range(RUNS):
        with contextlib.redirect_stdout(io.StringIO()):
            genis = _sorgu_genislet(q)
        llm += ilk_isabet(retriever.search(q, k=K, extra_queries=[genis] if genis else []), ifadeler) is not None
        bllm += ilk_isabet(birlesik(q, genis), ifadeler) is not None
        time.sleep(2.5)

    top["duz"] += duz
    top["soz"] += soz
    top["bsoz"] += bsoz
    top["llm"] += llm
    top["bllm"] += bllm
    print(f"{i:>2}  {soru[:30]:30} {ev(duz):7} {ev(soz):7} {ev(bsoz):8} {llm}/{RUNS}    {bllm}/{RUNS}")

n = len(SORULAR)
print("\n" + "=" * 60)
print(f"DÜZ                    : {top['duz']}/{n}")
print(f"SÖZLÜK (birim duyarlı) : {top['soz']}/{n}")
print(f"DÜZ-ÖNCELİKLİ + SÖZLÜK : {top['bsoz']}/{n}")
print(f"LLM genişletme         : {top['llm']}/{n * RUNS}")
print(f"DÜZ-ÖNCELİKLİ + LLM    : {top['bllm']}/{n * RUNS}")