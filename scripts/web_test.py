import os
import sys

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
soru = " ".join(sys.argv[1:])
t = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

for ad, kw in (("SADECE erbakan.edu.tr", {"include_domains": ["erbakan.edu.tr"]}),
               ("GENEL WEB", {})):
    r = t.search(query=f"Necmettin Erbakan Üniversitesi {soru}", max_results=5,
                 search_depth="advanced", **kw)
    sonuclar = r.get("results", [])
    print(f"\n=== {ad}: {len(sonuclar)} sonuç ===")
    for i, x in enumerate(sonuclar, 1):
        icerik = " ".join((x.get("content") or "").split())
        print(f"{i}. {x.get('url', '')[:90]}")
        print(f"   {icerik[:250]}")