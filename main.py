import os, json, logging
from dotenv import load_dotenv
from scraper.wtwd_scraper import WTWD
from scraper.wtd_scraper import WTD
from scraper.tireco_scraper import Tireco
from shopify_sync.sync import ShopifySync

load_dotenv()
logging.basicConfig(level=logging.INFO)

def main():
    print("🚀 Starting Thermite Tactical Middleware 4.0")
    wtwd = WTWD(os.getenv("WTWD_USERNAME"), os.getenv("WTWD_PASSWORD"))
    wtd = WTD(os.getenv("WTD_USERNAME"), os.getenv("WTD_PASSWORD"))
    tireco = Tireco(os.getenv("TIRECO_API_KEY"))

    print("🔍 Fetching data from distributors...")
    combined = wtwd.fetch_tires("225/45R17") + wtd.fetch_tires("225/45R17") + tireco.fetch_tires("225/45R17")
    print(f"✅ Total fetched: {len(combined)}")

    sync = ShopifySync(os.getenv("SHOPIFY_API_KEY"), os.getenv("SHOPIFY_PASSWORD"), os.getenv("SHOPIFY_STORE_URL"))
    sync.sync_products(combined)

    with open("output.json", "w") as f:
        json.dump([t.model_dump() for t in combined], f, indent=2)
    print("✅ Output saved to output.json")

if __name__ == "__main__":
    main()

@hi added by mike