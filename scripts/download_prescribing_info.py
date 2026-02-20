"""Download prescribing information PDFs from DailyMed for top 20 drugs."""
import json
import os
import time
import urllib.request
import urllib.error

DRUGS = [
    ("keytruda", "pembrolizumab"),
    ("ozempic", "semaglutide"),
    ("mounjaro", "tirzepatide"),
    ("dupixent", "dupilumab"),
    ("skyrizi", "risankizumab"),
    ("eliquis", "apixaban"),
    ("darzalex", "daratumumab"),
    ("zepbound", "tirzepatide"),
    ("wegovy", "semaglutide"),
    ("opdivo", "nivolumab"),
    ("jardiance", "empagliflozin"),
    ("entresto", "sacubitril valsartan"),
    ("farxiga", "dapagliflozin"),
    ("ocrevus", "ocrelizumab"),
    ("rinvoq", "upadacitinib"),
    ("tagrisso", "osimertinib"),
    ("stelara", "ustekinumab"),
    ("cosentyx", "secukinumab"),
    ("prevnar", "pneumococcal"),
    ("verzenio", "abemaciclib"),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "prescribing_info")
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

def get_setid(brand_name, generic_name):
    """Get the DailyMed set ID for a drug by brand name, fallback to generic."""
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
    """Download the prescribing information PDF from DailyMed."""
    pdf_url = f"https://dailymed.nlm.nih.gov/dailymed/getFile.cfm?setid={setid}&type=pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            if len(content) < 1000:
                print(f"  Warning: PDF seems too small ({len(content)} bytes), may not be valid")
                # Try alternative: download XML instead
                return download_xml(setid, filename.replace(".pdf", ".xml"))
            with open(filepath, "wb") as f:
                f.write(content)
            print(f"  Downloaded PDF: {filepath} ({len(content):,} bytes)")
            return True
    except Exception as e:
        print(f"  PDF download failed: {e}")
        return download_xml(setid, filename.replace(".pdf", ".xml"))

def download_xml(setid, filename):
    """Fallback: download the SPL XML from DailyMed."""
    xml_url = f"{BASE_API}/spls/{setid}.xml"
    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        req = urllib.request.Request(xml_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            with open(filepath, "wb") as f:
                f.write(content)
            print(f"  Downloaded XML: {filepath} ({len(content):,} bytes)")
            return True
    except Exception as e:
        print(f"  XML download also failed: {e}")
        return False

def main():
    results = []
    for i, (brand, generic) in enumerate(DRUGS, 1):
        print(f"\n[{i}/20] Processing {brand.upper()} ({generic})...")
        setid, title = get_setid(brand, generic)
        if not setid:
            print(f"  ERROR: Could not find {brand} on DailyMed")
            results.append((brand, False))
            continue
        print(f"  Found: {title[:80]}...")
        print(f"  Set ID: {setid}")
        filename = f"{brand}_prescribing_info.pdf"
        success = download_pdf(setid, filename)
        results.append((brand, success))
        time.sleep(1)  # Be polite to the API

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for brand, success in results:
        status = "OK" if success else "FAILED"
        print(f"  {brand.upper():15s} [{status}]")

    succeeded = sum(1 for _, s in results if s)
    print(f"\nDownloaded {succeeded}/{len(results)} prescribing information documents.")

if __name__ == "__main__":
    main()
