import os, logging
from typing import List, Optional
from .utils import Tire, safe_request, default_session, retry, RequestError

logger=logging.getLogger("thermite.scraper.wtwd")

class WTWD:
    BASE_URL=os.getenv("WTWD_BASE_URL","https://portal.tirevault.com/api/v1/tires")
    def __init__(self, username:str, password:str, session=None):
        self.auth=(username,password); self.session=session or default_session()
    @retry(times=3, backoff_factor=0.6, allowed_exceptions=(RequestError,))
    def fetch_tires(self, size:Optional[str]=None)->List[Tire]:
        q={"size":size} if size else {}
        data=safe_request(self.session,"GET",self.BASE_URL,params=q,auth=self.auth)
        tires=[]
        entries=data.get("tires") if isinstance(data,dict) else []
        for item in entries:
            try:
                tires.append(Tire(
                    brand=item.get("brand","UNK"),
                    model=item.get("model","UNK"),
                    size=item.get("size",size),
                    price=float(item.get("price",0)),
                    stock=int(item.get("stock",0))
                ))
            except Exception as e: logger.debug(f"skip {e}")
        return tires
