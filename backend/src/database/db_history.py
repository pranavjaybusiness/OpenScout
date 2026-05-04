import logging
import time

from botocore.exceptions import ClientError

from src.database.db_core import dynamodb, clean_url

logger = logging.getLogger(__name__)

history_table = dynamodb.Table('OpenScoutHistory')

def log_analysis(url: str, product_data: str):
    base_url = clean_url(url)
    if not base_url: return

    try:
        timestamp_ms = int(time.time() * 1000) 

        item = {
            'product_url': base_url,          # PARTITION KEY
            'analyzed_at': timestamp_ms,      # SORT KEY
            'product_data': product_data,
            'ebay_listing_url': (ebay_listing_url or "").strip(),
        }
        item['ebay_match_found'] = bool(item['ebay_listing_url'])

        history_table.put_item(Item=item)
        logger.info("Logged analysis to history for %s at %s", base_url, timestamp_ms)
    except ClientError as e:
        logger.warning("DynamoDB history write error: %s", e)