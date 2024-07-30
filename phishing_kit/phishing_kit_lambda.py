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
        if storage:
            return {
                "statusCode": 200,
                "body": json.dumps("Successfully stored data")
            }
        
        phishing_kit = PhishingKit(url, False, id)
        result = phishing_kit.run()
        
        return {
            "statusCode": 200,
            "body": result
        }
    except Exception as e:
        print(e)
        phishing_kit = PhishingKit(url, True, id)
        result = phishing_kit.run_error()
        return {
            "statusCode": 500,
            "body": result
        }
