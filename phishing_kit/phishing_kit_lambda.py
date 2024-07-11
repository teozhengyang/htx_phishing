from extractor import Extractor
from extractor.extractor import Extractor
from image_hashing_storage import ImageHashingStorage
from phishing_kit import PhishingKit
import json
import tldextract

def lambda_handler(event, context):
    url = event.get('url')
    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps('URL not provided')
        }

    url_info = []
    extractor = Extractor(url)
    result = extractor.run()
    brand = tldextract.extract(url).domain
    result = json.loads(result)
    result["Main page"]["brand"] = brand
    url_info.append(result["Main page"])
    for i, login_page in enumerate(result["Login pages"]):
      result["Login pages"][i]["brand"] = brand
      url_info.append(login_page)
      
    hashStorage = ImageHashingStorage(url_info)
    hashStorage.run()
    
    org_url_info = hashStorage.all_urls[0]
    phishing_kit = PhishingKit(url, org_url_info)
    pk_result = phishing_kit.run()
    pk_result_dict = {}
    pk_result_dict["phishing_kit_result"] = pk_result
    pk_result_json = json.dumps(pk_result_dict)
    
    with open('phishing_kit_result.json', 'w') as json_file:
        json.dump(pk_result_dict, json_file, indent=4)
        
    return {
        'statusCode': 200,
        'body': pk_result_json
    }
