import os, logging
from typing import List, Optional
from .utils import Tire, safe_request, default_session, retry, RequestError

logger=logging.getLogger("thermite.scraper.wtd")

class WTD:
    BASE_URL=os.getenv("WTD_BASE_URL","https://api.wtdtires.com/v1/inventory")
    AUTH_TYPE=os.getenv("WTD_AUTH_TYPE","basic")
    def __init__(self, username, password_or_token, session=None):
        self.username=username; self.password_or_token=password_or_token
        self.session=session or default_session()
    @retry(times=3, backoff_factor=0.6, allowed_exceptions=(RequestError,))
    def fetch_tires(self,size:Optional[str]=None)->List[Tire]:
        q={"size":size} if size else {}; headers={}; auth=None
        if self.AUTH_TYPE=="basic": auth=(self.username,self.password_or_token)
        else: headers["Authorization"]=f"Bearer {self.password_or_token}"
        data=safe_request(self.session,"GET",self.BASE_URL,params=q,headers=headers,auth=auth)
        tires=[]
        entries=data.get("results") if isinstance(data,dict) else []
        for item in entries:
            try:
                tires.append(Tire(
                    brand=item.get("brand","UNK"),
                    model=item.get("model","UNK"),
                    size=item.get("size",size),
                    price=float(item.get("price",0)),
                    stock=int(item.get("qty",0))
                ))
            except Exception as e: logger.debug(f"skip {e}")
        return tires
