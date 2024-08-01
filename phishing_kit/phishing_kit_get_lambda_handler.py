import json
import os
import boto3

def lambda_handler(event, context):
    file_id = event.get('id')
    aws_access_key_id = os.environ["aws_access_key_id"]
    aws_secret_access_key = os.environ["aws_secret_access_key"]
    region_name = os.environ["region_name"]
    extractor_bucket_name = os.environ["extractor_bucket_name"]
    phishing_db_name = os.environ["phishing_db_name"]
    storage_db_name = os.environ["storage_db_name"]
    
    phishing_db_table = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name).Table(phishing_db_name)
    response = phishing_db_table.get_item(
        Key={
            'id': file_id
        }
    )
    print(response)
        
    # Check if 'Item' exists in response
    if 'Item' in response:
        return {
            'statusCode': 200,
            'result': json.dumps(response['Item'])
        }
    else:
        storage_db_table = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name).Table(storage_db_name)
        response = storage_db_table.get_item(
            Key={
                'id': file_id
            }
        )
            
        # Check if 'Item' exists in response
        if 'Item' in response:
            return {
                'statusCode': 200,
                'result': json.dumps(response['Item'])
            }
        
        else:
            s3_client = boto3.resource('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
            bucket = s3_client.Bucket(extractor_bucket_name)
            objs = list(bucket.objects.filter(Prefix=file_id))
            
            
            if objs:
                s3_client = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
                s3_client.download_file(extractor_bucket_name, f'{file_id}.json', f'/tmp/{file_id}.json')
                with open(f'/tmp/{file_id}.json', 'r') as file:
                    url_info = json.load(file)
                return {
                        'statusCode': 200,
                        'result': json.dumps(url_info)
                }
            
            else:
                return {
                    'statusCode': 500,
                    'result': json.dumps('No matching ID')
                }
