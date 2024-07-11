import base64
import boto3
import cairosvg
import imagehash
import io
import json
import numpy as np
import onnxruntime
import os
import requests
import tempfile
import tldextract
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from extractor.extractor import Extractor
from models.PhishIntention.phishintention import PhishIntentionWrapper

class ImageHashingStorage:
  
  def __init__(self, urls_info):
    self.urls_info = urls_info
    self.phishintention_cls = PhishIntentionWrapper()
      
  # use detectron v2 model to get logo from screenshot
  def encode_logo_from_screenshot(self, url, screenshot_path):
    self.phishintention_cls.test_orig_phishintention(screenshot_path)
    with open("logo.png", "rb") as file:
      data = file.read()
      encoded_data = base64.b64encode(data).decode('utf-8')
    url["encoding_logo"] = encoded_data
  
  # encode logo from url or screenshot
  def encode_logo(self, url, screenshot_path):
    try:
      if url["logo"]:
        logo_url = url["logo"]
        response = requests.get(logo_url)
        response.raise_for_status()
        data = response.content
        if logo_url.endswith(".svg"):
          image = cairosvg.svg2png(bytestring=data)
        else:
          image = data
        with open("logo.png", "wb") as file:
          file.write(image)
        encoded_data = base64.b64encode(image).decode('utf-8')
        url["encoding_logo"] = encoded_data
      else:
        self.encode_logo_from_screenshot(url, screenshot_path)
    except:
      self.encode_logo_from_screenshot(url, screenshot_path)
  
  # encode favicon
  def encode_favicon(self, url):
    try:
      if url["favicon"]:
        favicon_url = url["favicon"]
        response = requests.get(favicon_url)
        response.raise_for_status()
        data = response.content
        if favicon_url.endswith(".svg"):
          image = cairosvg.svg2png(bytestring=data)
        else:
          image = data
        with open("favicon.ico", "wb") as file:
          file.write(image)
        encoded_data = base64.b64encode(image).decode('utf-8')
        url["encoding_favicon"] = encoded_data
      else:
        url["favicon"] = None
        url["encoding_favicon"] = None
    except:
      url["encoding_favicon"] = None
    
  # encode logo, favicon and screenshots
  def encode_logo_favicon_screenshots(self):
    
    # customisation of options
    LOCAL_DL_PATH = ""
    def mkdtemp():
      tempfile.mkdtemp()
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_experimental_option("prefs", {
      "profile.default_content_setting_values.automatic_downloads": 1,
      "download.default_directory": LOCAL_DL_PATH
    })
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script(""" 
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
    
    for url in self.urls_info:
      driver.get(url["url"])
      screenshot = driver.get_screenshot_as_png()
      encoded_screenshot = base64.b64encode(screenshot).decode('utf-8')
      url["encoding_screenshot"] = encoded_screenshot
      with open("screenshot.png", "wb") as file:
        file.write(screenshot)
      
      self.encode_logo(url, "screenshot.png")
      self.encode_favicon(url)
  
  # load neural hash model
  def load_neural_hash_model(self):
    self.nh_session = onnxruntime.InferenceSession("./models/neuralhash_model.onnx")
    self.nh_seed = open("./models/neuralhash_128x96_seed1.dat", "rb").read()[128:]
    self.nh_seed = np.frombuffer(self.nh_seed, dtype=np.float32).reshape([96,128])
  
  # neural hash image
  def neural_hash_image(self, type, url):
    try:
      if url[f"encoding_{type}"]:
        encoded_data = url[f"encoding_{type}"]
        decoded_data = base64.b64decode(encoded_data)
        image = Image.open(io.BytesIO(decoded_data))
        image = image.convert("RGB")
        image = image.resize([360,360])
        arr = np.array(image).astype(np.float32) / 255.0
        arr = arr * 2.0 - 1.0
        arr = arr.transpose(2,0,1).reshape([1,3,360,360])
        inputs = {self.nh_session.get_inputs()[0].name: arr}
        outputs = self.nh_session.run(None, inputs)
        hash_output = self.nh_seed.dot(outputs[0].flatten()) 
        hash_bits = ''.join(['1' if x >= 0 else '0' for x in hash_output])
        hash_hex = '{:0{}x}'.format(int(hash_bits, 2), len(hash_bits) // 4)
        url[f"hash_{type}"] = str(hash_hex)
      else:
        url[f"hash_{type}"] = None
    except:
      url[f"hash_{type}"] = None
  
  # hash logo, favicon and screenshots (neural hash for logo and favicon, dhash for screenshots)
  def hash_logo_favicon_screenshots(self):
    for url in self.urls_info:
      self.load_neural_hash_model()
      self.neural_hash_image("logo", url)
      self.neural_hash_image("favicon", url)
      
      decoded_screenshot = base64.b64decode(url["encoding_screenshot"])
      screenshot = Image.open(io.BytesIO(decoded_screenshot))
      screenshot_hash = imagehash.dhash(screenshot)
      url["hash_screenshot"] = str(screenshot_hash)
    
  # store encodings and hashes in db
  def store_logo_images_favicon_screenshots(self):
    load_dotenv()
    access_key = os.getenv("access_key")
    secret_access_key = os.getenv("secret_access_key")
    dyanmo = boto3.resource(service_name='dynamodb', region_name='ap-southeast-1', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
    for url in self.urls_info:
      url_table.put_item(Item={'url': url["url"], 'encoding_logo': url["encoding_logo"], 'encoding_favicon': url["encoding_favicon"], 'encoding_screenshot': url["encoding_screenshot"], 'hash_logo': str(url["hash_logo"]), 'hash_favicon': str(url["hash_favicon"]), 'hash_screenshot': str(url["hash_screenshot"]), 'brand': url["brand"]})
      
  def run(self):
    self.encode_logo_favicon_screenshots()
    self.hash_logo_favicon_screenshots()
    self.store_logo_images_favicon_screenshots()
    return self.urls_info
  
if __name__ == "__main__":
  urls = []
  urls_info = []
  for url in urls:
    extractor = Extractor(url)
    result = extractor.run()
    brand = tldextract.extract(url).domain
    result = json.loads(result)
    result["Main page"]["brand"] = brand
    urls_info.append(result["Main page"])
    for i, login_page in enumerate(result["Login pages"]):
      result["Login pages"][i]["brand"] = brand
      urls_info.append(login_page)
  hashStorage = ImageHashingStorage(urls_info)
  urls_all_info = hashStorage.run()    
  with open('storage_result.json', 'w') as json_file:
      json.dump(urls_all_info, json_file, indent=4)
  