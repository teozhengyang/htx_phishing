import boto3
import json
import datetime

def run_lambda():
  session = boto3.Session(aws_access_key_id="AKIA2CY6Z3QHIPGGY2TD", aws_secret_access_key="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", region_name="ap-southeast-1")
  lambda_client = session.client('lambda')
  urls = []
  stripped_urls = []
  for i, url in enumerate(urls):
    current_datetime = datetime.datetime.now()
    id = str(current_datetime.strftime("%Y%m%d%H%M%S")) + '-' + stripped_urls[i] + '-' + 'main'
    payload = {
      "url": url,
      "storage": True,
      "id": id
    }
    print('Processing ' + url)
    print(id)
    response = lambda_client.invoke(
      FunctionName='arn:aws:lambda:ap-southeast-1:693164956686:function:phishing_kit',
      InvocationType='RequestResponse',
      Payload=json.dumps(payload)
    )
    response_payload = response['Payload'].read()
    response_dict = json.loads(response_payload)
    response_body = response_dict['body']
    with open(f'storage_result/{stripped_urls[i]}.json', 'w') as f:
      json.dump(response_body, f, indent=4)
    print('Processed ' + response_body)
    
if __name__ == "__main__":
  run_lambda()