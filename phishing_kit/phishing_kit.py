import boto3
import hashlib
import os
import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime
from fuzzywuzzy import fuzz

class PhishingKit:
  
  # obtain the hashes of the logo, favicon and screenshot
  def __init__(self, url, error, id):
    self.url = url
    self.id = id
    self.phishing_kit_result_db = os.environ["phishing_kit_result_db"]
    self.aws_access_key_id = os.environ["aws_access_key_id"]
    self.aws_secret_access_key = os.environ["aws_secret_access_key"]
    self.region_name = os.environ["region_name"]
    
    if not error:
      self.whitelisted_images_hashes_db = os.environ["whitelisted_image_hashes_db"]
      self.tested_url_images_s3 = os.environ["tested_url_images_s3"]
      stripped_url = self.url.replace("/", "")
      s3 = boto3.client('s3', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
      s3.download_file(self.tested_url_images_s3, f'{self.id}.json', f'/tmp/{stripped_url}.json')
      with open(f'/tmp/{stripped_url}.json', 'r') as file:
        url_info = json.load(file)
      self.logo_hash = url_info["hash_logo"]
      self.favicon_hash = url_info["hash_favicon"]
      self.screenshot_hash = url_info["hash_screenshot"]
      self.dom_tree = url_info["dom_tree"]
  
  # get most similar whitelisted urls with url
  def get_similar_whitelisted_urls(self):
    dynamo = boto3.resource(service_name='dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    response = dynamo.Table(self.whitelisted_images_hashes_db).scan()
    all_urls = [item for item in response['Items']]
    best_match_url = all_urls[0]["url"]
    best_match_score = 0
    best_match_id = all_urls[0]["id"]
    for url in all_urls:
      score = fuzz.ratio(url["url"], self.url)
      if score > best_match_score:
        best_match_score = score
        best_match_url = url["url"]
        best_match_id = url["id"]
    if best_match_score < 75:
      raise Exception("No matching brand found")
    else:
      self.whitelisted_url = best_match_url
      self.whitelisted_id = best_match_id
  
  # get hashes from dynamo db
  def get_hashes(self):
    dynamo = boto3.resource(service_name='dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    url_table = dynamo.Table(self.whitelisted_images_hashes_db)
    response = url_table.get_item(Key={'id': str(self.whitelisted_id)})
    self.whitelisted_logo_hash = response["Item"]["hash_logo"]
    self.whitelisted_favicon_hash = response["Item"]["hash_favicon"]
    self.whitelisted_screenshot_hash = response["Item"]["hash_screenshot"]
    self.whitelisted_brand = response["Item"]["brand"]
    
  # compare hashes
  def compare_hashes(self):
    self.logo_similarity = fuzz.ratio(str(self.logo_hash), str(self.whitelisted_logo_hash))
    self.favicon_similarity = fuzz.ratio(str(self.favicon_hash), str(self.whitelisted_favicon_hash))
    self.screenshot_similarity = fuzz.ratio(str(self.screenshot_hash), str(self.whitelisted_screenshot_hash))
  
  # ask Llama 3 whether phishing (dom structures/texts)
  def ask_llama3(self):

    #client = anthropic.Anthropic()

    #message = client.messages.create(
                #model="claude-3-opus-20240229",
                #max_tokens=1000,
                #temperature=0.0,
                #system="Respond in short and clear sentences.",
                #messages=[
                  #{
                      #"role": "user",
                      #"content": "Can you explain the concept of neural networks?"
                  #}
                #]
              #)

    #print(message.content)

    #response = ollama.chat(
    #  model="llama3",
    #  messages=[
    #      {
    #          "role": "user",
    #          "content": f"Output the following in JSON format. Decide whether dom tree is phishing or not. {self.dom_tree}. If yes provide links and features as keys and relevant values. If no, provide a message saying not phishing. Also provide the logo, favicon and screenshot similarity scores. Logo: {self.logo_similarity}, Favicon: {self.favicon_similarity}, Screenshot: {self.screenshot_similarity}.",
    #      },
    #  ],
    #)
    #return response["message"]["content"]
    return None
  
  # obtain final verdict
  def run(self):
    try:
      self.get_similar_whitelisted_urls()
      self.get_hashes()
      self.compare_hashes()
      # return self.ask_llama3()
      stripped_url = self.url.replace("/", "")
      result = {
        "tested_url": self.url,
        "tested_url_logo_hash": f"tested_url_images/{self.id}.json",
        "tested_url_favicon_hash": f"tested_url_images/{self.id}.json",
        "tested_url_screenshot_hash": f"tested_url_images/{self.id}.json",
        "whitelisted_url": self.whitelisted_url,
        "whitelisted_url_logo_hash": f"whitelisted_url_images/{self.id}.json",
        "whitelisted_url_favicon_hash": f"whitelisted_url_images/{self.id}.json",
        "whitelisted_url_screenshot_hash": f"whitelisted_url_images/{self.id}.json",
        "logo_similarity": self.logo_similarity,
        "favicon_similarity": self.favicon_similarity,
        "screenshot_similarity": self.screenshot_similarity,
        "result": f"match found for {self.whitelisted_brand}"
      }
      phishing_table = boto3.resource('dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name).Table(self.phishing_kit_result_db)
      phishing_table.put_item(Item={'id': self.id, "tested_url": self.url,
                                    "tested_url_logo_hash": f"tested_url_images/{self.id}.json",
                                    "tested_url_favicon_hash": f"tested_url_images/{self.id}.json",
                                    "tested_url_screenshot_hash": f"tested_url_images/{self.id}.json",
                                    "whitelisted_url": self.whitelisted_url,
                                    "whitelisted_url_logo_hash": f"whitelisted_url_images/{self.id}.json",
                                    "whitelisted_url_favicon_hash": f"whitelisted_url_images/{self.id}.json",
                                    "whitelisted_url_screenshot_hash": f"whitelisted_url_images/{self.id}.json",
                                    "logo_similarity": str(self.logo_similarity),
                                    "favicon_similarity": str(self.favicon_similarity),
                                    "screenshot_similarity": str(self.screenshot_similarity),
                                    "result": f"match found for {self.whitelisted_brand}"})
      
      result["datetime"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
      db_content = self.id
      db_hash_object = hashlib.sha256(db_content.encode('utf-8'))  
      db_hex_dig = db_hash_object.hexdigest()
      result["db_id"] = db_hex_dig
      return json.dumps(result, indent=4)
    except Exception as e:
      self.run_error(e)
    
  def run_error(self, reason):
    result = {
        "tested_url": self.url,
        "result": "Phishing kit did not run",
        "reason": str(reason)
      }
    phishing_table = boto3.resource('dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name).Table(self.phishing_kit_result_db)
    phishing_table.put_item(Item={'id': self.id, "tested_url": self.url,
                                  "result": f"Phishing kit did not run due to {reason}"})
    result["datetime"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    db_content = self.id
    db_hash_object = hashlib.sha256(db_content.encode('utf-8'))  
    db_hex_dig = db_hash_object.hexdigest()
    result["db_id"] = db_hex_dig
    return json.dumps(result, indent=4)
