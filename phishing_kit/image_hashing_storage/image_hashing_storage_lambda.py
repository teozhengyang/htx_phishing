import base64
import boto3
import imagehash
import io
import json
import numpy as np
import onnxruntime
import requests
import tldextract
import hashlib
from datetime import datetime
from PIL import Image
from models.PhishIntention.phishintention import PhishIntentionWrapper

def lambda_handler(event, context):
  all_urls_info = event.get('all_urls_info')
  storage = event.get('storage')
  id = event.get('id')
  aws_access_key_id = "AKIA2CY6Z3QHIPGGY2TD"
  aws_secret_access_key = "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"
  region_name = "ap-southeast-1"

  result_dict = json.loads(all_urls_info)

  main_login_url_info = []
  all_results_json = []
  
  main_login_url_info.append(result_dict["Main page"])
  for _, login_page in enumerate(result_dict["Login pages"]):
    main_login_url_info.append(login_page)
      
  for i, url_info in enumerate(main_login_url_info):
    hash_storage = ImageHashingStorage(url_info, storage, id, i)
    stripped_url = url_info["url"].replace("/", "")
    result = hash_storage.run()
    data = {
      "url": result["url"],
      "brand": result["brand"],
      "encoding_logo": result["encoding_logo"],
      "encoding_favicon": result["encoding_favicon"],
      "encoding_screenshot": result["encoding_screenshot"],
      "hash_logo": result["hash_logo"],
      "hash_favicon": result["hash_favicon"],
      "hash_screenshot": result["hash_screenshot"],
      "dom_tree": result["dom_tree"],
    }

    if storage:
      try: 
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
        s3.put_object(
            Bucket='whitelisted-urls-images',
            Key=f'{id}/{stripped_url}.json',
            Body=json.dumps(data),
            ContentType='application/json'
          )
        all_results_json.append(data)
      except:
        return {
          'statusCode': 500,
          'body': json.dumps(f'Error storing relevant hashes of {url_info["url"]} in S3')
        }
    if not storage:
      try:
        s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name)
        s3.put_object(
            Bucket='tested-urls-images',
            Key=f'{id}.json',
            Body=json.dumps(data),
            ContentType='application/json'
          )
        all_results_json.append(data)
      except:
        return {
          'statusCode': 500,
          'body': json.dumps(f'Error storing relevant hashes of {url_info["url"]} in S3')
        }
  
  stripped_url = main_login_url_info[0]["url"].replace("/", "") 
  s3_content = f'{id}/{stripped_url}.json'
  s3_hash_object = hashlib.sha256(s3_content.encode('utf-8'))  
  s3_hex_dig = s3_hash_object.hexdigest()
  db_hash_object = hashlib.sha256(id.encode('utf-8'))  
  db_hex_dig = db_hash_object.hexdigest()
  identifier = {
    "datetime": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    "s3_id": s3_hex_dig,
    "db_id": db_hex_dig
  }
  all_results_json.append(identifier)
  
  return {
    'statusCode': 200,
    'body': json.dumps(all_results_json)
  }
        
        
class ImageHashingStorage:
  
  def __init__(self, url_info, storage, id, i):
    self.url_info = url_info
    self.storage = storage
    self.id = id
    self.i = i
    self.phishintention_cls = PhishIntentionWrapper()
    self.aws_access_key_id = "AKIA2CY6Z3QHIPGGY2TD"
    self.aws_secret_access_key = "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"
    self.region_name = "ap-southeast-1"
      
  # use detectron v2 model to get logo from screenshot
  def encode_logo_from_screenshot(self, screenshot_path):
    self.phishintention_cls.test_orig_phishintention(screenshot_path)
    with open("/tmp/logo.png", "rb") as file:
      data = file.read()
      encoded_data = base64.b64encode(data).decode('utf-8')
    self.url_info["encoding_logo"] = encoded_data
  
  # encode logo from url or screenshot
  def encode_logo(self, screenshot_path):
    try:
      if self.url_info["logo"]:
        logo_url = self.url_info["logo"]
        response = requests.get(logo_url,timeout=10,verify=False)
        response.raise_for_status()
        data = response.content
        image = data
        with open("/tmp/logo.png", "wb") as file:
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
        response = requests.get(favicon_url,timeout=10,verify=False)
        response.raise_for_status()
        data = response.content
        image = data
        with open("/tmp/favicon.ico", "wb") as file:
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
    stripped_url = self.url_info["url"].replace("/", "")
    s3 = boto3.client('s3', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    s3.download_file('extractor-result', f'{self.id}/{stripped_url}-screenshot.png', '/tmp/screenshot.png')
    screenshot = Image.open('/tmp/screenshot.png')
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    screenshot = buf.getvalue()
    encoded_screenshot = base64.b64encode(screenshot).decode('utf-8')
    self.url_info["encoding_screenshot"] = encoded_screenshot
    
    self.encode_logo("/tmp/screenshot.png")
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
  def store_whitelisted_logo_images_favicon_screenshots(self):
    if self.i == 0:
      id = self.id
    else:
      id = f"{self.id}-{self.i}"
    brand = tldextract.extract(self.url_info["url"]).domain
    self.url_info["brand"] = brand  
    dyanmo = boto3.resource(service_name='dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes')
    url_table.put_item(Item={'id': id, 'url': self.url_info["url"], 'brand': self.url_info["brand"],'hash_logo': self.url_info["hash_logo"], 'hash_favicon': self.url_info["hash_favicon"], 'hash_screenshot': self.url_info["hash_screenshot"]})

  def store_tested_logo_images_favicon_screenshots(self):
    if self.i == 0:
      id = self.id
    else:
      id = f"{self.id}-{self.i}"
    brand = tldextract.extract(self.url_info["url"]).domain
    self.url_info["brand"] = brand  
    dyanmo = boto3.resource(service_name='dynamodb', aws_access_key_id=self.aws_access_key_id, aws_secret_access_key=self.aws_secret_access_key, region_name=self.region_name)
    url_table = dyanmo.Table('ddb-htx-le-devizapp-imagehashes-tested')
    url_table.put_item(Item={'id': id, 'url': self.url_info["url"], 'brand': self.url_info["brand"],'hash_logo': self.url_info["hash_logo"], 'hash_favicon': self.url_info["hash_favicon"], 'hash_screenshot': self.url_info["hash_screenshot"]})
  
  def run(self):
    if self.storage:    
      self.encode_logo_favicon_screenshots()
      self.hash_logo_favicon_screenshots()
      self.store_whitelisted_logo_images_favicon_screenshots()
      return self.url_info
    else: 
      self.encode_logo_favicon_screenshots()
      self.hash_logo_favicon_screenshots()
      self.store_tested_logo_images_favicon_screenshots()
      return self.url_info
  