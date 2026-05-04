import json
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.services.llm_service import parse_product_text
from src.services.ebay_service import get_ebay_comparison
from src.database.db_cache import get_cached_product, save_to_cache
from src.database.db_history import log_analysis

def _log_level() -> int:
    name = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, name, logging.INFO)


logging.basicConfig(
    level=_log_level(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Update the model to match the frontend key exactly
class ScrapeRequest(BaseModel):
    raw_text: str  

@app.post("/parse")
async def parse_endpoint(request: ScrapeRequest):
    try:
        
        incoming_data = json.loads(request.raw_text)
        
        product_url = incoming_data.get("identifiers", {}).get("url", "")

        cached_result = get_cached_product(product_url)
        if cached_result:
            ebay = get_ebay_comparison(cached_result)
            ebay_listing_url = ((ebay.get("listing") or {}).get("url") or "").strip()
            log_analysis(product_url, json.dumps(cached_result), ebay_listing_url=ebay_listing_url)
            return {"status": "success", "data": cached_result, "ebay": ebay}

        logger.info("Cache miss; calling Gemini API")
        
        llm_response_string = parse_product_text(request.raw_text) 
        
        parsed_product_data = json.loads(llm_response_string)

        ebay = get_ebay_comparison(parsed_product_data)
        ebay_listing_url = ((ebay.get("listing") or {}).get("url") or "").strip()

        save_to_cache(product_url, llm_response_string)
        log_analysis(product_url, llm_response_string, ebay_listing_url=ebay_listing_url)
        return {"status": "success", "data": parsed_product_data, "ebay": ebay}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format received from extension.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))