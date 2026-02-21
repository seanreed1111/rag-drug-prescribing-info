"""Download prescribing information PDFs from DailyMed for drugs ranked 21-50."""

import json
import os
import time
import urllib.request
import urllib.error

DRUGS = [
    ("biktarvy", "bictegravir emtricitabine tenofovir"),
    ("trikafta", "elexacaftor tezacaftor ivacaftor"),
    ("eylea", "aflibercept"),
    ("humira", "adalimumab"),
    ("gardasil", "human papillomavirus vaccine"),
    ("comirnaty", "tozinameran"),
    ("xarelto", "rivaroxaban"),
    ("revlimid", "lenalidomide"),
    ("paxlovid", "nirmatrelvir ritonavir"),
    ("vyndaqel", "tafamidis"),
    ("xtandi", "enzalutamide"),
    ("entyvio", "vedolizumab"),
    ("trulicity", "dulaglutide"),
    ("hemlibra", "emicizumab"),
    ("lynparza", "olaparib"),
    ("imfinzi", "durvalumab"),
    ("vabysmo", "faricimab"),
    ("prolia", "denosumab"),
    ("ibrance", "palbociclib"),
    ("shingrix", "zoster vaccine"),
    ("invega sustenna", "paliperidone palmitate"),
    ("tecentriq", "atezolizumab"),
    ("perjeta", "pertuzumab"),
    ("ofev", "nintedanib"),
    ("xolair", "omalizumab"),
    ("orencia", "abatacept"),
    ("tremfya", "guselkumab"),
    ("pomalyst", "pomalidomide"),
    ("rybelsus", "semaglutide"),
    ("imbruvica", "ibrutinib"),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prescribing_info")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


def get_setid(brand_name, generic_name):
    for name in [brand_name, generic_name]:
        url = f"{BASE_API}/spls.json?drug_name={urllib.request.quote(name)}&page=1&pagesize=1"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
                if data.get("data"):
                    entry = data["data"][0]
                    return entry["setid"], entry["title"]
        except Exception as e:
            print(f"  Warning: API error for '{name}': {e}")
        time.sleep(0.5)
    return None, None


def download_pdf(setid, filename):
    pdf_url = (
        f"https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={setid}&type=pdf"
    )
    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            if len(content) < 1000:
                print(f"  Warning: PDF too small ({len(content)} bytes), trying XML...")
                return download_xml(setid, filename.replace(".pdf", ".xml"))
            with open(filepath, "wb") as f:
                f.write(content)
            print(f"  Downloaded PDF: {filename} ({len(content):,} bytes)")
            return True
    except Exception as e:
        print(f"  PDF download failed: {e}")
        return download_xml(setid, filename.replace(".pdf", ".xml"))


def download_xml(setid, filename):
    xml_url = f"{BASE_API}/spls/{setid}.xml"
    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        req = urllib.request.Request(xml_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            with open(filepath, "wb") as f:
                f.write(content)
            print(f"  Downloaded XML: {filename} ({len(content):,} bytes)")
            return True
    except Exception as e:
        print(f"  XML download also failed: {e}")
        return False


def main():
    results = []
    for i, (brand, generic) in enumerate(DRUGS, 1):
        # Clean filename
        safe_brand = brand.replace(" ", "_")
        print(f"\n[{i}/30] Processing {brand.upper()} ({generic})...")
        setid, title = get_setid(brand, generic)
        if not setid:
            print(f"  ERROR: Could not find {brand} on DailyMed")
            results.append((brand, False))
            continue
        print(f"  Found: {title[:80]}...")
        print(f"  Set ID: {setid}")
        filename = f"{safe_brand}_prescribing_info.pdf"
        success = download_pdf(setid, filename)
        results.append((brand, success))
        time.sleep(1)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for brand, success in results:
        status = "OK" if success else "FAILED"
        print(f"  {brand.upper():20s} [{status}]")

    succeeded = sum(1 for _, s in results if s)
    print(f"\nDownloaded {succeeded}/{len(results)} prescribing information documents.")


if __name__ == "__main__":
    main()
