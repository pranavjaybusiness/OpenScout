import json
import logging
import time

from botocore.exceptions import ClientError

from src.database.db_core import dynamodb, clean_url

logger = logging.getLogger(__name__)

cache_table = dynamodb.Table('OpenScoutCache')
TTL_SECONDS = 21600  # 6 hours

def get_cached_product(url: str):
    base_url = clean_url(url)
    if not base_url: return None

    try:
        response = cache_table.get_item(Key={'product_url': base_url})
        item = response.get('Item')
        
        if item and item['expires_at'] > int(time.time()):
            logger.info("Cache hit for %s", base_url)
            return json.loads(item['product_data'])
        elif item:
            logger.info("Cache expired for %s", base_url)

    except ClientError as e:
        logger.warning("DynamoDB cache read error: %s", e)
        
    return None

def save_to_cache(url: str, product_data: str):
    base_url = clean_url(url)
    if not base_url: return
        
    try:
        cache_table.put_item(
            Item={
                'product_url': base_url,
                'product_data': product_data, 
                'expires_at': int(time.time()) + TTL_SECONDS
            }
        )
        logger.info("Wrote cache entry for %s", base_url)
    except ClientError as e:
        logger.warning("DynamoDB cache write error: %s", e)