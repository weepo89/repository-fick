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
    combined = []
    
    try:
        print("🔍 Fetching data from WTWD...")
        wtwd = WTWD(os.getenv("WTWD_USERNAME"), os.getenv("WTWD_PASSWORD"))
        wtwd_tires = wtwd.fetch_tires("225/45R17")
        print(f"✅ WTWD fetched: {len(wtwd_tires)} tires")
        combined.extend(wtwd_tires)
    except Exception as e:
        print(f"❌ Error fetching from WTWD: {str(e)}")
    
    try:
        print("🔍 Fetching data from WTD...")
        wtd = WTD(os.getenv("WTD_USERNAME"), os.getenv("WTD_PASSWORD"))
        wtd_tires = wtd.fetch_tires("225/45R17")
        print(f"✅ WTD fetched: {len(wtd_tires)} tires")
        combined.extend(wtd_tires)
    except Exception as e:
        print(f"❌ Error fetching from WTD: {str(e)}")
    
    try:
        print("🔍 Fetching data from Tireco...")
        tireco = Tireco(os.getenv("TIRECO_API_KEY"))
        tireco_tires = tireco.fetch_tires("225/45R17")
        print(f"✅ Tireco fetched: {len(tireco_tires)} tires")
        combined.extend(tireco_tires)
    except Exception as e:
        print(f"❌ Error fetching from Tireco: {str(e)}")

    print(f"✅ Total tires fetched: {len(combined)}")

    if combined:
        try:
            sync = ShopifySync(os.getenv("SHOPIFY_API_KEY"), os.getenv("SHOPIFY_PASSWORD"), os.getenv("SHOPIFY_STORE_URL"))
            sync.sync_products(combined)
            print("✅ Products synced to Shopify")
        except Exception as e:
            print(f"❌ Error syncing to Shopify: {str(e)}")

        try:
            with open("output.json", "w") as f:
                json.dump([t.model_dump() for t in combined], f, indent=2)
            print("✅ Output saved to output.json")
        except Exception as e:
            print(f"❌ Error saving output: {str(e)}")
    else:
        print("⚠️ No tires were fetched from any distributor")

if __name__ == "__main__":
    main()