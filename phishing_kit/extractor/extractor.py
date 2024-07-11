import json
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class Extractor:
  
  def __init__(self, main_url):
    self.main_url = main_url
    
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
    self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    self.login_urls = []
    self.result = {
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
  
  # insert data for main page
  def insert_main_data(self):
    self.driver.get(self.main_url)
    self.result["Main page"]["url"] = self.main_url
    self.result["Main page"]["js"] = self.get_js_scripts()
    self.result["Main page"]["files"] = self.get_files()
    self.result["Main page"]["logo"] = self.get_logo()
    self.result["Main page"]["favicon"] = self.get_favicon()

  # insert data for login pages
  def insert_login_data(self):
    self.get_login_pages()
    for page in self.result["Login pages"]:
      page["js"] = self.get_js_scripts()
      page["files"] = self.get_files()
      page["logo"] = self.get_logo()
      page["favicon"] = self.get_favicon()
  
  def run(self):
    # extract main page data
    self.insert_main_data()
    
    # extract all login pages data
    self.insert_login_data()
      
    # close the driver
    self.driver.close()
    
    with open('extractor_result.json', 'w') as json_file:
      json.dump(self.result, json_file, indent=4)
    
    return json.dumps(self.result)
    
if __name__ == "__main__":
  url = input("Enter the URL: ")
  extractor = Extractor(url)
  result = extractor.run()
  print(result) 