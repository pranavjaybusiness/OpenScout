import boto3

dynamodb = boto3.resource('dynamodb')

def clean_url(url: str) -> str:
    if not url:
        return ""
    return url.split('?')[0]