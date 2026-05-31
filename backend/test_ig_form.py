from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

try:
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.instagram.com/accounts/login/")
    
    wait = WebDriverWait(driver, 20)
    print("Waiting for username...")
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@name='username' or @name='email']")))
    
    # Let's find all inputs
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"Found {len(inputs)} inputs:")
    for idx, inp in enumerate(inputs):
        print(f"Input {idx}: name='{inp.get_attribute('name')}', type='{inp.get_attribute('type')}', id='{inp.get_attribute('id')}', class='{inp.get_attribute('class')}'")
        
    # Let's find all clickable elements or form elements
    forms = driver.find_elements(By.TAG_NAME, "form")
    print(f"Found {len(forms)} form(s):")
    for idx, f in enumerate(forms):
        print(f"Form {idx} OuterHTML:\n{f.get_attribute('outerHTML')[:1000]}")
        
    driver.quit()
except Exception as e:
    import traceback
    traceback.print_exc()
