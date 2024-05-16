from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class Extractor:
  def __init__(self, main_url):
    self.main_url = main_url
    self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    self.login_urls = []
    self.result = {
      "Main page": {},
      "Login pages": [],
    }
  
  def get_login_pages(self):
    links = self.driver.find_elements(By.XPATH, '//a[contains(@href, "login") or contains(@href, "log-in") or contains(@href, "Login") or contains(@href, "sign-in") or contains(@href, "signin") or contains(@href, "Signin")]')    
    for link in links:
      href = link.get_attribute('href')
      if href and href not in self.login_urls:
        self.login_urls.append(href)
    self.result["Login pages"] = [{"url": url} for url in self.login_urls]
  
  def get_js_scripts(self):
    try: 
      js_links = []
      scripts = self.driver.find_elements(By.TAG_NAME, "script")
      for script in scripts:
        src = script.get_attribute('src')
        if src and src.endswith(".js"):
          js_links.append(src)
      return js_links
    except:
      return None
  
  def get_files(self):
    try:
      file_links = []
      links = self.driver.find_elements(By.TAG_NAME, "a")
      for link in links:
        href = link.get_attribute('href')
        if href:
          if href.endswith((".pdf", ".doc", ".docx", ".csv", ".xlsx", ".exe", ".bin", ".img", ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".rar", ".7z")):
            file_links.append(href)
      return file_links
    except:
      return None
    
  def get_logo(self):
    try:
      logos = self.driver.find_elements(By.TAG_NAME, "img")
      for logo in logos:
        src = logo.get_attribute('src')
        class_names = logo.get_attribute('class')
        if "logo" in src.lower() or "logo" in class_names.lower():
          return src
    except:
      return None
    
  def get_favicon(self):
    try: 
      favicon = self.driver.find_element(By.XPATH, "//link[@rel='icon']")
      favicon_link = favicon.get_attribute('href')
      return favicon_link
    except:
      return None
  
  def insert_main_data(self):
    self.driver.get(self.main_url)
    self.result["Main page"]["url"] = self.main_url
    self.result["Main page"]["js"] = self.get_js_scripts()
    self.result["Main page"]["files"] = self.get_files()
    self.result["Main page"]["logo"] = self.get_logo()
    self.result["Main page"]["favicon"] = self.get_favicon()

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
    
    return self.result

if __name__ == "__main__":
  url = input("Enter the URL: ")
  extractor = Extractor(url)
  result = extractor.run()
  print(result)
    
    