import json
import boto3
import os
from datetime import datetime
from phishing_kit import PhishingKit

# Define the client to interact with AWS Lambda
client = boto3.client('lambda')

def lambda_handler(event, context):
    url = event.get("url")
    storage = event.get("storage")
    id = event.get("id")
    phishing_kit_bool = event.get("phishing_kit")
    
    extractor_input = {
        "url": url,
        "storage": storage,
        "id": id
    }
    
    extractor_function = os.environ["extractor_function"]
    storage_function = os.environ["storage_function"]
    
    try: 
        response = client.invoke(
            FunctionName = extractor_function,
            InvocationType = 'RequestResponse',
            Payload = json.dumps(extractor_input)
        )
    
         # Read the streaming body
        response_payload = response['Payload'].read()
    
        # Parse the JSON response
        response_dict = json.loads(response_payload)
        
        response_body = response_dict['body']
        storage_input = {
            "all_urls_info": response_body,
            "storage": storage,
            "id": id
        }
        
        response = client.invoke(
            FunctionName = storage_function,
            InvocationType = 'RequestResponse',
            Payload = json.dumps(storage_input)
        )
        
        # Read the streaming body
        response_payload = response['Payload'].read()
        response_dict = json.loads(response_payload)
        response_body = response_dict['body']
        
        
        if storage == "True":
            body = {
                "stored_url": url,
                "result": "Successfully stored data",
                "id": id
              }
            return {
                "statusCode": 200,
                "body": json.dumps(body),
            }
        elif phishing_kit_bool == "True":
            phishing_kit = PhishingKit(url, False, id, phishing_kit_bool)
            phishing_kit.run()
            body = {
                "tested_url": url,
                "result": "Phishing kit was deployed",
                "id": id
            }
            return {
                "statusCode": 200,
                "body": json.dumps(body),
            }
        else:
            body = {
                "extracted_url": url,
                "result": "Extractor was deployed",
                "id": id
            }
            return {
                "statusCode": 200,
                "body": json.dumps(body),
                
            }
    except Exception as e:
        phishing_kit = PhishingKit(url, True, id, phishing_kit_bool)
        error = phishing_kit.run_error(repr(e))
        return {
            "statusCode": 500,
            "body": error
        }
