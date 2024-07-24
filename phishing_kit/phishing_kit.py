import anthropic
import boto3
import os
import requests
import ollama
import json
import tldextract
from dotenv import load_dotenv
from phishing_kit.image_hashing_storage import ImageHashingStorage
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from extractor.extractor_lambda import Extractor

class PhishingKit:
  
  # obtain the hashes of the logo, favicon and screenshot
  def __init__(self, url, url_info):
    self.url = url
    self.logo_hash = url_info["hash_logo"]
    self.favicon_hash = url_info["hash_favicon"]
    self.screenshot_hash = url_info["hash_screenshot"]
    self.dom_tree = self.get_dom_tree(url)
  
  # get entire dom tree
  def get_dom_tree(self, url):
      try:
        response = requests.get(url)
        response.raise_for_status() 
        html_content = response.content
        soup = BeautifulSoup(html_content, 'html.parser')
        return soup.prettify()
      except:
        print("Error in fetching the URL")
  
  # get most similar whitelisted urls with url
  def get_similar_whitelisted_urls(self):
    load_dotenv()
    access_key = os.getenv("access_key")
    secret_access_key = os.getenv("secret_access_key")
    dyanmo = boto3.resource(service_name='dynamodb', region_name='ap-southeast-1', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    response = dyanmo.Table('htx_phishing').scan()
    all_urls = [item["url"] for item in response['Items'] if "url" in item]
    best_match_url = None
    best_match_score = 0
    for url in all_urls:
      score = fuzz.ratio(url, self.url)
      if score > best_match_score:
        best_match_score = score
        best_match_url = url
    self.whitelisted_url = best_match_url
  
  # get hashes from dynamo db
  def get_hashes(self):
    load_dotenv()
    access_key = os.getenv("access_key")
    secret_access_key = os.getenv("secret_access_key")
    dyanmo = boto3.resource(service_name='dynamodb', region_name='ap-southeast-1', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
    response = url_table.get_item(Key={'url': self.whitelisted_url})
    self.whitelisted_logo_hash = response["Item"]["hash_logo"]
    self.whitelisted_favicon_hash = response["Item"]["hash_favicon"]
    self.whitelisted_screenshot_hash = response["Item"]["hash_screenshot"]
    
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

    response = ollama.chat(
      model="llama3",
      messages=[
          {
              "role": "user",
              "content": f"Output the following in JSON format. Decide whether dom tree is phishing or not. {self.dom_tree}. If yes provide links and features as keys and relevant values. If no, provide a message saying not phishing. Also provide the logo, favicon and screenshot similarity scores. Logo: {self.logo_similarity}, Favicon: {self.favicon_similarity}, Screenshot: {self.screenshot_similarity}.",
          },
      ],
    )
    return response["message"]["content"]
  
  # obtain final verdict
  def run(self):
    self.get_similar_whitelisted_urls()
    self.get_hashes()
    self.compare_hashes()
    return self.ask_llama3()
    
if __name__ == "__main__":
  url = input("Enter the URL: ")  
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
  urls_all_info = hashStorage.run()
  
  org_url_info = hashStorage.all_urls[0]
  phishing_kit = PhishingKit(url, org_url_info)
  pk_result = phishing_kit.run()
  pk_result_dict = {}
  pk_result_dict["phishing_kit_result"] = pk_result
  
  with open('phishing_kit_result.json', 'w') as json_file:
      json.dump(pk_result_dict, json_file, indent=4)

