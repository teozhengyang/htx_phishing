from extractor import Extractor
import json

def lambda_handler(event, context):
    url = event.get('url')
    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps('URL not provided')
        }

    extractor = Extractor(url)
    result = extractor.run()
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }