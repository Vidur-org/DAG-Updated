import time
# from fundamental.scraper.browser import get_browser
# from fundamental.scraper.orchestrator import scrape_company
# from fundamental.exporters.json_writer import write_json
# from fundamental.exporters.excel_writer import write_excel
import json
from pathlib import Path
# import json

# BASE_DIR = Path(__file__).resolve().parent.parent  # project root
# DATA_PATH = BASE_DIR / ""
def run_nifty_scraper(
    symbol: str = "ADANI"
):
    print("Starting Nifty 50 chosing...")
    try:
        # Use absolute path relative to this file's parent directory
        nifty_file = Path(__file__).parent.parent / "merged_nifty50.json"
        with open(nifty_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Error loading merged nifty 50 data:", e)
        return None
    print("Loaded merged nifty 50 data.")
    print(f"finding {symbol} in {data}")


    if symbol in data:
        print
        return data[symbol]
    else:
        return None
        
if __name__ == "__main__":
    run_nifty_scraper()
    print("🎉 Scraping finished")
