import boto3
import os
from dotenv import load_dotenv
from image_hashing_storage import ImageHashingStorage
from fuzzywuzzy import fuzz
import requests
from bs4 import BeautifulSoup
import ollama

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
    response = ollama.chat(
      model="llama3",
      messages=[
          {
              "role": "user",
              "content": f"Decide whether following dom tree is phishing and exactly the phishing portion. Dom tree: {self.dom_tree}. Can integrate logo similarity: {self.logo_similarity}, favicon similarity: {self.favicon_similarity}, screenshot similarity: {self.screenshot_similarity} as whitelisted urls. and other features like page text eg click here to submit, paynow, login here or html like structure of buttons surrounding phishing element hyperlink and other appropriate features.",
          },
      ],
    )
    print(response["message"]["content"])
  
  # obtain final verdict
  def run(self):
    self.get_similar_whitelisted_urls()
    self.get_hashes()
    self.compare_hashes()
    self.ask_llama3()
    
if __name__ == "__main__":
  url = input("Enter the URL: ")  
  hash_storage = ImageHashingStorage([url])
  hash_storage.extract_all_pages()
  hash_storage.encode_logo_favicon_screenshots()
  hash_storage.hash_logo_favicon_screenshots()
  url_info = hash_storage.all_urls[0]
  phishing_kit = PhishingKit(url, url_info)
  phishing_kit.run()



