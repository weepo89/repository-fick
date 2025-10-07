import time, logging, functools, requests
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from requests import Session

logger = logging.getLogger("thermite.scraper")

class RequestError(Exception): pass

class Tire(BaseModel):
    brand: str
    model: str
    size: str
    price: float = Field(..., gt=0)
    stock: int = Field(0, ge=0)
    @validator('size')
    def valid_size(cls, v):
        if '/' not in v:
            raise ValueError("size must look like 225/45R17")
        return v

def default_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "ThermiteMiddleware/4.0"})
    return s

def retry(times=3, backoff_factor=0.5, allowed_exceptions=(Exception,)):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            last=None
            for i in range(times):
                try: return fn(*a, **kw)
                except allowed_exceptions as e:
                    last=e; logging.warning(f"retry {i+1}/{times}: {e}")
                    time.sleep(backoff_factor*(2**i))
            raise RequestError(str(last))
        return wrapper
    return deco

@retry(times=3, backoff_factor=0.5, allowed_exceptions=(requests.RequestException,))
def safe_request(session:Optional[Session], method:str, url:str, **kw)->Any:
    sess=session or default_session()
    r=sess.request(method,url,timeout=10,**kw); r.raise_for_status()
    try: return r.json()
    except Exception: return r.text
