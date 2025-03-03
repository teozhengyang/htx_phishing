import boto3
import hashlib
import json
import re
import os
import requests
from datetime import datetime
from tempfile import mkdtemp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions

def lambda_handler(event, context):
    url = event.get('url')
    storage = event.get('storage')
    id = event.get('id')
    
    if not url:
        return {
            'statusCode': 400,
            'body': json.dumps('URL not provided')
        }

    extractor = Extractor(url, storage, id)
    result = extractor.run()
    return {
        'statusCode': 200,
        'body': result
    }

class Extractor:
  
  def __init__(self, main_url, storage, id):
    self.main_url = main_url
    self.storage = storage  
    self.id = id
    self.aws_access_key_id = "AKIA2CY6Z3QHIPGGY2TD"
    self.aws_secret_access_key = "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"
    self.region_name = "ap-southeast-1"
  
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument(f"--user-data-dir={mkdtemp()}")
    chrome_options.add_argument(f"--data-path={mkdtemp()}")
    chrome_options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    chrome_options.add_argument("--remote-debugging-pipe")
    chrome_options.add_argument("--verbose")
    chrome_options.add_argument("--log-path=/tmp")
    chrome_options.add_argument("enable-automation")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--dns-prefetch-disable")
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"
    chrome_options.add_experimental_option("prefs", {
      "download.prompt_for_download": False,
      "download.directory_upgrade": True,
      "safebrowsing.enabled": False
    })

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    self.driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )
    
    self.driver.set_page_load_timeout(20)
    
    self.driver.execute_script(""" 
                // Function to remove elements by selector 
                function removeElementsBySelector(selector) { 
                    var elements = document.querySelectorAll(selector); 
                    elements.forEach(function(element) { 
                        element.remove(); 
                    }); 
                } 
 
                // Common ad and video elements selectors 
                var adAndVideoSelectors = [ 
                    'video',  // Remove all video tags 
                    'iframe',  // Remove all iframe tags (often used for embedded ads and videos) 
                    '.advertisement',  
                    '.ad',  
                    '.ads',  
                    '.ad-container',  
                    '.ad-banner', 
                    '.ad-block',  
                    '.ad-wrapper',  
                    '.ad-embed',  
                    '.sponsored', 
                    '[class*="ad"]',  // Elements with 'ad' in the class name 
                    '[id*="ad"]',  // Elements with 'ad' in the ID 
                    '[class*="banner"]',  // Elements with 'banner' in the class name 
                    '[id*="banner"]',  // Elements with 'banner' in the ID 
                    '.popup',  
                    '.modal',  
                    '.carousel',  
                    '.slider', 
                    '[data-ad]',  // Elements with data attributes related to ads 
                    '[data-video]',  // Elements with data attributes related to videos 
                    '[data-dynamic]', 
                    '.sponsored-content', 
                    '.sponsored-link', 
                    '.promoted',  // Promoted content or links 
                    '.promo',  // Promotional content or links 
                    '.ad-slot', 
                    '.adsbygoogle' 
                ]; 
 
                // Remove all identified ad and video elements 
                adAndVideoSelectors.forEach(function(selector) { 
                    removeElementsBySelector(selector); 
                }); 
 
                // Handling any ads or videos added dynamically after page load 
                var observer = new MutationObserver(function(mutations) { 
                    mutations.forEach(function(mutation) { 
                        if (mutation.addedNodes) { 
                            mutation.addedNodes.forEach(function(node) { 
                                if (node.nodeType === 1) {  // Check if it's an element node 
                                    adAndVideoSelectors.forEach(function(selector) { 
                                        if (node.matches(selector)) { 
                                            node.remove(); 
                                        } 
                                    }); 
                                } 
                            }); 
                        } 
                    }); 
                }); 
 
                // Observe changes to the body element and its children 
                observer.observe(document.body, { childList: true, subtree: true }); 
            """)
    
    self.login_urls = []
    self.result = {
      "Main page": {},
      "Login pages": [],
    }
    
    self.result_without_dom_tree = {
      "Main page": {},
      "Login pages": [],
    }
  
  # obtain login pages from main page
  def get_login_pages(self):
    links = self.driver.find_elements(By.XPATH, '//a[contains(translate(@href, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "login") or '
                                                    'contains(translate(@href, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "log-in") or '
                                                    'contains(translate(@href, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "sign-in") or '
                                                    'contains(translate(@href, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "signin")]')    
    for link in links:
      href = link.get_attribute('href')
      if href and href not in self.login_urls:
        self.login_urls.append(href)
    self.result["Login pages"] = [{"url": url} for url in self.login_urls]
    self.result_without_dom_tree["Login pages"] = [{"url": url} for url in self.login_urls]
  
  # get all scripts in website
  def get_js_scripts(self):
    try: 
      js_links = []
      scripts = self.driver.find_elements(By.TAG_NAME, "script")
      for script in scripts:
        src = script.get_attribute('src')
        if src:
          js_links.append(src)
      return js_links
    except:
      return None
  
  # get possible links to files in website
  def get_files(self):
    try:
      file_links = []
      links = self.driver.find_elements(By.TAG_NAME, "a")
      keywords = ["pdf", "doc", "docx", "csv", "xlsx", "exe", "bin", "img", "png", "jpg", "jpeg", "zip", "tar", "gz", "rar", "7z", "apk"]
      
      for link in links:
        href = link.get_attribute('href')
        for keyword in keywords:
          if href and href.endswith(keyword):
            file_links.append(href)
            break
      return file_links
    except:
      return None
    
  # get logo from div tag
  def get_logo_from_div(self):
    try:
      logo = self.driver.find_element(By.XPATH, "//div[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'logo')]")
      logo_link = logo.find_element(By.TAG_NAME, "img").get_attribute('src')
      return logo_link
    except:
      return None
  
  # get logo from anchor tag
  def get_logo_from_a(self):
    try:
      logo = self.driver.find_element(By.XPATH, "//a[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'logo')]")
      logo_link = logo.find_element(By.TAG_NAME, "img").get_attribute('src')
      return logo_link
    except:
      return None
  
  # get logo from image tag
  def get_logo_from_img(self):
    try:
      logo = self.driver.find_element(By.XPATH, "//img[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'logo') or "
                                                        "contains(translate(@src, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'logo')]")
      logo_link = logo.get_attribute('src')
      return logo_link
    except:
      return None  
  
  # get logo from website (div then anchor then image)
  def get_logo(self):
    div_logo = self.get_logo_from_div()
    a_logo = self.get_logo_from_a()
    img_logo = self.get_logo_from_img()
    if div_logo:
      return div_logo
    elif a_logo:
      return a_logo
    elif img_logo:
      return img_logo
    else:
      return None
    
  # get favicon from website
  def get_favicon(self):
    try: 
      favicon = self.driver.find_element(By.XPATH, "//link[@rel='icon']")
      favicon_link = favicon.get_attribute('href')
      return favicon_link
    except:
      return None
  
  # get dom tree from website
  def get_dom_tree(self):
    try:
      return self.driver.page_source
    except:
      return None
  
  # insert data for main page
  def insert_main_data(self):
    self.driver.get(self.main_url)
    
    self.result["Main page"]["url"] = self.main_url
    self.result["Main page"]["js"] = self.get_js_scripts()
    self.result["Main page"]["files"] = self.get_files()
    self.result["Main page"]["logo"] = self.get_logo()
    self.result["Main page"]["favicon"] = self.get_favicon()
    self.result["Main page"]["dom_tree"] = self.get_dom_tree()
    
    self.result_without_dom_tree["Main page"]["url"] = self.main_url
    self.result_without_dom_tree["Main page"]["js"] = self.get_js_scripts()
    self.result_without_dom_tree["Main page"]["files"] = self.get_files()
    self.result_without_dom_tree["Main page"]["logo"] = self.get_logo()
    self.result_without_dom_tree["Main page"]["favicon"] = self.get_favicon()
    
    main_url_stripped = self.main_url.replace("/", "") 
    
    s3 = boto3.client('s3', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    
    try:
      
      screenshot = self.driver.get_screenshot_as_png()
      
      content = f'{self.id}/{main_url_stripped}-screenshot.png'
      hash_object = hashlib.sha256(content.encode('utf-8'))  
      hex_dig = hash_object.hexdigest()
      self.result["Main page"]["s3_screenshot_id"] = hex_dig
      
      s3.put_object(
        Bucket='extractor-result',
        Key=f'{self.id}/{main_url_stripped}-screenshot.png',
        Body=screenshot,
        ContentType='image/png'
      )
      print("Got main page screenshot")
    except:
      print("Error getting main page screenshot")
    
    try:
      if self.result["Main page"]["logo"]:
        logo = requests.get(self.result["Main page"]["logo"],timeout=10,verify=False).content
        content = f'{self.id}/{main_url_stripped}-logo.png'
        hash_object = hashlib.sha256(content.encode('utf-8'))  
        hex_dig = hash_object.hexdigest()
        self.result["Main page"]["s3_logo_id"] = hex_dig
        s3.put_object(
          Bucket='extractor-result',
          Key=f'{self.id}/{main_url_stripped}-logo.png',
          Body=logo,
          ContentType='image/png'
        )
        print("Got main page logo")
    except:
      print("Error getting main page logo")  
        
    try:
      if self.result["Main page"]["favicon"]:
        favicon = requests.get(self.result["Main page"]["favicon"],timeout=10,verify=False).content
        content = f'{self.id}/{main_url_stripped}-favicon.ico'
        hash_object = hashlib.sha256(content.encode('utf-8'))  
        hex_dig = hash_object.hexdigest()
        self.result["Main page"]["s3_favicon_id"] = hex_dig
        s3.put_object(
          Bucket='extractor-result',
          Key=f'{self.id}/{main_url_stripped}-favicon.ico',
          Body=favicon,
          ContentType='image/x-icon'
        )
        print("Got main page favicon")
    except:
      print("Error getting main page favicon")
    
  # insert data for login pages
  def insert_login_data(self):
    self.get_login_pages()
    for page in self.result["Login pages"]:
      self.driver.get(page["url"])
      login_url_stripped = page["url"].replace("/", "")
      page["js"] = self.get_js_scripts()
      page["files"] = self.get_files()
      page["logo"] = self.get_logo()
      page["favicon"] = self.get_favicon()
      page["dom_tree"] = self.get_dom_tree()
      s3 = boto3.client('s3', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
      content = f'{self.id}/{login_url_stripped}-screenshot.png'
      hash_object = hashlib.sha256(content.encode('utf-8'))  
      hex_dig = hash_object.hexdigest()
      page["s3_screenshot_id"] = hex_dig
    
    try:
      screenshot = self.driver.get_screenshot_as_png()
      
      s3.put_object(
        Bucket='extractor-result',
        Key=f'{self.id}/{login_url_stripped}-screenshot.png',
        Body=screenshot,
        ContentType='image/png'
      )
      print("Got login page screenshot")
    except:
      print("Error getting login page screenshot")
      
      try:
        if page["logo"]:
          logo = requests.get(page["logo"],timeout=10,verify=False).content
          content = f'{self.id}/{login_url_stripped}-logo.png'
          hash_object = hashlib.sha256(content.encode('utf-8'))  
          hex_dig = hash_object.hexdigest()
          page["s3_logo_id"] = hex_dig
          s3.put_object(
            Bucket='extractor-result',
            Key=f'{self.id}/{login_url_stripped}-logo.png',
            Body=logo,
            ContentType='image/png'
          )
          print("Got login page logo")
      except:
        print("Error getting login page logo")
      
      try:
        if page["favicon"]:
          favicon = requests.get(page["favicon"],timeout=10,verify=False).content
          content = f'{self.id}/{login_url_stripped}-favicon.ico'
          hash_object = hashlib.sha256(content.encode('utf-8'))  
          hex_dig = hash_object.hexdigest()
          page["s3_favicon_id"] = hex_dig
          s3.put_object(
            Bucket='extractor-result',
            Key=f'{self.id}/{login_url_stripped}-favicon.ico',
            Body=favicon,
            ContentType='image/x-icon'
          )
          print("Got login page favicon")
      except:
        print("Error getting login page favicon")
  
  # insert data for login pages
  def insert_login_data_other(self):
    for page in self.result_without_dom_tree["Login pages"]:
      self.driver.get(page["url"])
      page["js"] = self.get_js_scripts()
      page["files"] = self.get_files()
      page["logo"] = self.get_logo()
      page["favicon"] = self.get_favicon()
  
  def run(self):
    print("Extracting main page data")
    # extract main page data
    self.insert_main_data()
    
    print("Extracting login pages data")
    # extract all login pages data
    self.insert_login_data()
      
    self.insert_login_data_other()
    
    # close the driver
    self.driver.close()
    
    print("Storing extractor result in S3")
    s3 = boto3.client('s3', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    
    s3.put_object(
      Bucket='extractor-result',
      Key=f'{self.id}.json',
      Body=json.dumps(self.result_without_dom_tree),
      ContentType='application/json'
    )
        
    if self.storage == "True":
      print("Storing extractor result in dynamodb")
      table_name = "extractor_result"
      table = boto3.resource('dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name).Table(table_name)
      table.put_item(Item={'id': self.id, 'result': self.result_without_dom_tree})
    
    self.result["datetime"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return json.dumps(self.result)