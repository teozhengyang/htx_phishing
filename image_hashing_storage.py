import base64
import boto3
import cairosvg
import imagehash
import io
import numpy as np
import onnxruntime
import os
import requests
import tempfile
import tldextract
from dotenv import load_dotenv
from extractor import Extractor
from PhishIntention.phishintention import PhishIntentionWrapper
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class ImageHashingStorage:
  
  def __init__(self, urls):
    self.main_urls = urls
    self.all_urls = []
    self.phishintention_cls = PhishIntentionWrapper()
  
  # extract all pages from main urls
  def extract_all_pages(self):
    for url in self.main_urls:
      extractor = Extractor(url)
      result = extractor.run()
      self.all_urls.append(result["Main page"])
      brand = tldextract.extract(url).domain
      result["Main page"]["brand"] = brand
      for i, login_page in enumerate(result["Login pages"]):
        self.all_urls.append(login_page)
        result["Login pages"][i]["brand"] = brand
      
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
    
    for url in self.all_urls:
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
    self.nh_session = onnxruntime.InferenceSession("neuralhash_model.onnx")
    self.nh_seed = open("neuralhash_128x96_seed1.dat", "rb").read()[128:]
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
        url[f"hash_{type}"] = hash_hex
      else:
        url[f"hash_{type}"] = None
    except:
      url[f"hash_{type}"] = None
  
  # hash logo, favicon and screenshots (neural hash for logo and favicon, dhash for screenshots)
  def hash_logo_favicon_screenshots(self):
    for url in self.all_urls:
      self.load_neural_hash_model()
      self.neural_hash_image("logo", url)
      self.neural_hash_image("favicon", url)
      
      decoded_screenshot = base64.b64decode(url["encoding_screenshot"])
      screenshot = Image.open(io.BytesIO(decoded_screenshot))
      screenshot_hash = imagehash.dhash(screenshot)
      url["hash_screenshot"] = screenshot_hash
    
  # store encodings and hashes in db
  def store_logo_images_favicon_screenshots(self):
    load_dotenv()
    access_key = os.getenv("access_key")
    secret_access_key = os.getenv("secret_access_key")
    dyanmo = boto3.resource(service_name='dynamodb', region_name='ap-southeast-1', aws_access_key_id=access_key, aws_secret_access_key=secret_access_key)
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
    for url in self.all_urls:
      url_table.put_item(Item={'url': url["url"], 'encoding_logo': url["encoding_logo"], 'encoding_favicon': url["encoding_favicon"], 'encoding_screenshot': url["encoding_screenshot"], 'hash_logo': str(url["hash_logo"]), 'hash_favicon': str(url["hash_favicon"]), 'hash_screenshot': str(url["hash_screenshot"]), 'brand': url["brand"]})
      
  def run(self):
    self.extract_all_pages()
    self.encode_logo_favicon_screenshots()
    self.hash_logo_favicon_screenshots()
    self.store_logo_images_favicon_screenshots()
    
if __name__ == "__main__":
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
                          "https://www.judiciary.gov.sg/", "https://www.parliment.gov.sg/", "https://www.psc.gov.sg/", "https://www.cabinet.gov.sg/"
                          ]
  urls_others = ["https://www.google.com", "https://www.facebook.com", "https://www.instagram.com", "https://www.x.com",
                 "https://www.shopee.com", "https://www.lazada.com", "https://www.amazon.com", "https://www.ticketmaster.com",
                 "https://www.carousell.sg", "https://www.dbs.com.sg", "https://www.ocbc.com", "https://www.uob.com.sg", 
                 "https://www.citibank.com.sg", "https://www.hsbc.com.sg", "https://www.maybank.com.sg", "https://www.sc.com/sg",
                 "https://www.posb.com.sg"
                 ]
  urls = urls_ministries + urls_stats_boards + urls_organs_of_state +  urls_others
  hashStorage = ImageHashingStorage(["https://www.google.com/", "https://www.facebook.com/"])
  hashStorage.run()

  