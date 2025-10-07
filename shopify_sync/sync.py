import shopify
from scraper.utils import Tire

class ShopifySync:
    def __init__(self, api_key:str,password:str,store_url:str):
        shop_url=f"https://{api_key}:{password}@{store_url}/admin"
        shopify.ShopifyResource.set_site(shop_url)
    def sync_products(self, tires:list[Tire]):
        for tire in tires:
            product=shopify.Product()
            product.title=f"{tire.brand} {tire.model} {tire.size}"
            product.body_html=f"<strong>{tire.brand}</strong> {tire.model} - {tire.size}"
            product.variants=[{"price":tire.price,"inventory_quantity":tire.stock}]
            product.save()
            print(f"⬆️ Uploaded {product.title}")
