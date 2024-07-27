import json
import boto3
from datetime import datetime
from phishing_kit import PhishingKit

# Define the client to interact with AWS Lambda
client = boto3.client('lambda')

def lambda_handler(event, context):
    url = event.get("url")
    storage = event.get("storage")
    
    extractor_input = {
        "url": url,
        "storage": storage
    }
        
    response = client.invoke(
        FunctionName = 'arn:aws:lambda:ap-southeast-1:693164956686:function:extractor',
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
        "storage": storage
    }
    
    response = client.invoke(
        FunctionName = 'arn:aws:lambda:ap-southeast-1:693164956686:function:storage',
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
    
    phishing_kit = PhishingKit(url)
    result = phishing_kit.run()
    
    return {
        "statusCode": 200,
        "body": result
    }
    
