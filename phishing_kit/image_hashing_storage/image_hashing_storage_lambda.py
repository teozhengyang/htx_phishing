import base64
import boto3
import cairosvg
import imagehash
import io
import json
import numpy as np
import onnxruntime
import requests
import tempfile
import tldextract
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from models.PhishIntention.phishintention import PhishIntentionWrapper
from selenium.webdriver.chrome.options import Options as ChromeOptions
from extractor_lambda import Extractor
from extractor_lambda import lambda_handler as extractor_lambda_handler

urls_ministries =["http://www.mci.gov.sg", "http://www.mccy.gov.sg", "http://www.mindef.gov.sg", "http://www.moe.gov.sg", 
                    "http://www.mof.gov.sg", "http://www.mfa.gov.sg", "http://www.moh.gov.sg", "http://www.mha.gov.sg", 
                    "http://www.mlaw.gov.sg", "http://www.mom.gov.sg", "http://www.mnd.gov.sg", "http://www.msf.gov.sg",
                    "http://www.mse.gov.sg", "http://www.mti.gov.sg", "http://www.mot.gov.sg", "http://www.pmo.gov.sg"
                    ]
urls_stats_boards = ["https://www.acra.gov.sg", "https://www.a-star.edu.sg", "https://www.boa.gov.sg", "https://www.bca.gov.sg",
                       "https://www.cpf.gov.sg/", "https://www.caas.gov.sg/", "https://www.csc.gov.sg/", "https://www.cccs.gov.sg/",
                       "https://www.cea.gov.sg/", "https://www.dsta.gov.sg/", "https://www.edb.gov.sg/", "https://www.ema.gov.sg/",
                       "https://www.entreprisesg.gov.sg/", "https://www.gra.gov.sg/", "https://www.tech.gov.sg/", "https://www.hpb.gov.sg/",
                       "https://www.hsa.gov.sg/", "https://www.htx.gov.sg/", "https://www.hlb.gov.sg/", "https://www.hdb.gov.sg/", 
                       "https://www.imdb.gov.sg/", "https://www.iras.gov.sg/", "https://www.ipos.gov.sg/", "https://www.jtc.gov.sg/",
                       "https://www.lsb.mlaw.gov.sg/", "https://www.lta.gov.sg/", "https://www.muis.gov.sg/", "https://www.mpa.gov.sg/",
                       "https://www.mas.gov.sg/", "https://www.nac.gov.sg/", "https://www.ncss.gov.sg/", "https://www.nea.gov.sg/",
                       "https://www.nhb.gov.sg/", "https://www.nlb.gov.sg/", "https://www.nparks.gov.sg/", "https://www.pa.gov.sg/",
                       "https://www.peb.gov.sg/", "https://www.pub.gov.sg/", "https://www.ptc.gov.sg/", "https://www.sdc.gov.sg/",
                       "https://www.seab.gov.sg/", "https://www.sfa.gov.sg/", "https://www.sla.gov.sg/", "https://www.smc.gov.sg/",
                       "https://www.snb.gov.sg/", "https://www.spc.gov.sg/", "https://www.stb.gov.sg/", "https://www.sportsingapore.gov.sg/",
                       "https://www.toteboard.gov.sg/", "https://www.tcmpb.gov.sg/", "https://www.ura.gov.sg/", "https://www.ssg-wsg.gov.sg/",
                       "https://www.yellowribbon.gov.sg/"
                       ]
urls_organs_of_state = ["https://www.agc.gov.sg/", "https://www.ago.gov.sg/", "https://www.iac.gov.sg/", "https://www.istana.gov.sg/",
                          "https://www.judiciary.gov.sg/", "https://www.parliament.gov.sg/", "https://www.psc.gov.sg/", "https://www.cabinet.gov.sg/"
                        ]
urls_others = ["https://www.google.com", "https://www.facebook.com", "https://www.instagram.com", "https://www.x.com",
                 "https://www.shopee.com", "https://www.lazada.com", "https://www.amazon.com", "https://www.ticketmaster.com",
                 "https://www.carousell.sg", "https://www.dbs.com.sg", "https://www.ocbc.com", "https://www.uob.com.sg", 
                 "https://www.citibank.com.sg", "https://www.hsbc.com.sg", "https://www.maybank.com.sg", "https://www.sc.com/sg",
                 "https://www.posb.com.sg"
                ]

s3_client = boto3.client('s3')

def lambda_handler(event, context):
  url = event.get('url')
  storage = event.get('storage')
  whitelisted = event.get('whitelisted')
    
  if not url:
    return {
      'statusCode': 400,
      'body': json.dumps('URL not provided')
    }
    
  # purely extract
  if not storage:
    extractor_lambda_handler(event, context)

  main_login_url_info = []
  extractor = Extractor(url, whitelisted)
  result = extractor.run()
  result_dict = json.loads(result)

  main_login_url_info.append(result_dict["Main page"])
  for i, login_page in enumerate(result_dict["Login pages"]):
    main_login_url_info.append(login_page)
      
  for url_info in main_login_url_info:
    hashStorage = ImageHashingStorage(url_info, whitelisted)
    result = hashStorage.run()
    results_json = json.dumps(result)
    if whitelisted:
      try:
        bucket_name = 'whitelisted-urls-images'
        object_name = f'{url_info["url"]}.json'
        s3_client.put_object(
          Bucket=bucket_name,
          Key=object_name,
          Body=results_json,
          ContentType='application/json'
        )   
      except Exception as e:
        return {
          'statusCode': 500,
          'body': json.dumps(f'Error storing JSON result for website {url_info["url"]}')
        }
        
  return {
    'statusCode': 200,
    'body': results_json
  }
        
class ImageHashingStorage:
  
  def __init__(self, url_info, whitelisted):
    self.url_info = url_info
    self.phishintention_cls = PhishIntentionWrapper()
    self.whitelisted = whitelisted
      
  # use detectron v2 model to get logo from screenshot
  def encode_logo_from_screenshot(self, screenshot_path):
    self.phishintention_cls.test_orig_phishintention(screenshot_path)
    with open("logo.png", "rb") as file:
      data = file.read()
      encoded_data = base64.b64encode(data).decode('utf-8')
    self.url_info["encoding_logo"] = encoded_data
  
  # encode logo from url or screenshot
  def encode_logo(self, screenshot_path):
    try:
      if self.url_info["logo"]:
        logo_url = self.url_info["logo"]
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
        self.url_info["encoding_logo"] = encoded_data
      else:
        self.encode_logo_from_screenshot(screenshot_path)
    except:
      self.encode_logo_from_screenshot(screenshot_path)
  
  # encode favicon
  def encode_favicon(self):
    try:
      if self.url_info["favicon"]:
        favicon_url = self.url_info["favicon"]
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
        self.url_info["encoding_favicon"] = encoded_data
      else:
        self.url_info["favicon"] = None
        self.url_info["encoding_favicon"] = None
    except:
      self.url_info["encoding_favicon"] = None
    
  # encode logo, favicon and screenshots
  def encode_logo_favicon_screenshots(self):
    
    # customisation of options
    LOCAL_DL_PATH = ""
    def mkdtemp():
      tempfile.mkdtemp()
    
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
    chrome_options.add_argument("--window-size=1280x1696")
    chrome_options.add_experimental_option("prefs", {
      "download.prompt_for_download": False,
      "download.directory_upgrade": True,
      "safebrowsing.enabled": False
    })
    chrome_options.binary_location = "/opt/chrome/chrome-linux64/chrome"

    service = Service(
        executable_path="/opt/chrome-driver/chromedriver-linux64/chromedriver",
        service_log_path="/tmp/chromedriver.log"
    )

    driver = webdriver.Chrome(
        service=service,
        options=chrome_options
    )
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
    
    driver.get(self.url_info["url"])
    screenshot = driver.get_screenshot_as_png()
    encoded_screenshot = base64.b64encode(screenshot).decode('utf-8')
    self.url_info["encoding_screenshot"] = encoded_screenshot
    with open("screenshot.png", "wb") as file:
      file.write(screenshot)
    
    self.encode_logo("screenshot.png")
    self.encode_favicon()
  
  # load neural hash model
  def load_neural_hash_model(self):
    self.nh_session = onnxruntime.InferenceSession("./models/neuralhash_model.onnx")
    self.nh_seed = open("./models/neuralhash_128x96_seed1.dat", "rb").read()[128:]
    self.nh_seed = np.frombuffer(self.nh_seed, dtype=np.float32).reshape([96,128])
  
  # neural hash image
  def neural_hash_image(self, type):
    try:
      if self.url_info[f"encoding_{type}"]:
        encoded_data = self.url_info[f"encoding_{type}"]
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
        self.url_info[f"hash_{type}"] = str(hash_hex)
      else:
        self.url_info[f"hash_{type}"] = None
    except:
      self.url_info[f"hash_{type}"] = None
  
  # hash logo, favicon and screenshots (neural hash for logo and favicon, dhash for screenshots)
  def hash_logo_favicon_screenshots(self):
    self.load_neural_hash_model()
    self.neural_hash_image("logo")
    self.neural_hash_image("favicon")
      
    decoded_screenshot = base64.b64decode(self.url_info["encoding_screenshot"])
    screenshot = Image.open(io.BytesIO(decoded_screenshot))
    screenshot_hash = imagehash.dhash(screenshot)
    self.url_info["hash_screenshot"] = str(screenshot_hash)
    
  # store encodings and hashes in db
  def store_logo_images_favicon_screenshots(self):
    if self.whitelisted:
      brand = tldextract.extract(self.url_info["url"]).domain
      self.url_info["brand"] = brand  
      dyanmo = boto3.resource(service_name='dynamodb')
      url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
      url_table.put_item(Item={'url': self.url_info["url"], 'brand': self.url_info["brand"],'hash_logo': self.url_info["hash_logo"], 'hash_favicon': self.url_info["hash_favicon"], 'hash_screenshot': self.url_info["hash_screenshot"]})

  def run(self):
    self.encode_logo_favicon_screenshots()
    self.hash_logo_favicon_screenshots()
    self.store_logo_images_favicon_screenshots()
    return self.url_info