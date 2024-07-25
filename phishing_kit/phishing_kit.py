import boto3
import requests
import json
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup

class PhishingKit:
  
  # obtain the hashes of the logo, favicon and screenshot
  def __init__(self, url):
    self.url = url
    stripped_url = self.url.replace("/", "")
    s3 = boto3.client('s3', aws_access_key_id="AKIA2CY6Z3QHIPGGY2TD", aws_secret_access_key="pvuTaW3wNQ8Y5f+YzlLvMa7WauutBVahw6qhos96", region_name="ap-southeast-1")
    s3.download_file('tested-urls-images', f'{stripped_url}.json', f'/tmp/{stripped_url}.json')
    with open(f'/tmp/{stripped_url}.json', 'r') as file:
      url_info = json.load(file)
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
    dyanmo = boto3.resource(service_name='dynamodb', aws_access_key_id="AKIA2CY6Z3QHIPGGY2TD", aws_secret_access_key="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", region_name="ap-southeast-1")
    response = dyanmo.Table('ddb-htx-le-devizapp-imagehashes').scan()
    all_urls = [item["url"] for item in response['Items'] if "url" in item]
    print(all_urls)
    best_match_url = all_urls[0]
    best_match_score = 0
    for url in all_urls:
      score = fuzz.ratio(url, self.url)
      if score > best_match_score:
        best_match_score = score
        best_match_url = url
    self.whitelisted_url = best_match_url
  
  # get hashes from dynamo db
  def get_hashes(self):
    dyanmo = boto3.resource(service_name='dynamodb', aws_access_key_id="AKIA2CY6Z3QHIPGGY2TD", aws_secret_access_key="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", region_name="ap-southeast-1")
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
    response = url_table.get_item(Key={'url': str(self.whitelisted_url)})
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
    self.get_similar_whitelisted_urls()
    self.get_hashes()
    self.compare_hashes()
    # return self.ask_llama3()
    stripped_url = self.url.replace("/", "")
    result = {
      "tested_url": self.url,
      "tested_url_logo_hash": self.logo_hash,
      "tested_url_favicon_hash": self.favicon_hash,
      "tested_url_screenshot_hash": self.screenshot_hash,
      "whitelisted_url": self.whitelisted_url,
      "whitelisted_url_logo_hash": self.whitelisted_logo_hash,
      "whitelisted_url_favicon_hash": self.whitelisted_favicon_hash,
      "whitelisted_url_screenshot_hash": self.whitelisted_screenshot_hash,
      "logo_similarity": self.logo_similarity,
      "favicon_similarity": self.favicon_similarity,
      "screenshot_similarity": self.screenshot_similarity
    }
    s3 = boto3.client('s3', aws_access_key_id="AKIA2CY6Z3QHIPGGY2TD", aws_secret_access_key="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", region_name="ap-southeast-1")
    s3.put_object(
      Bucket='phishing-kit-result',
      Key=f'{stripped_url}.json',
      Body=json.dumps(result),
      ContentType='application/json'
    )
    return json.dumps(result, indent=4)
