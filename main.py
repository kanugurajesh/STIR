from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import uuid
from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import random
import os
import json
import tempfile
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# MongoDB connection
try:
    client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'), serverSelectionTimeoutMS=5000)
    client.server_info()  # will throw an exception if connection fails
    db = client['twitter_trends']
    collection = db['trends']
except Exception as e:
    print(f"Failed to connect to MongoDB: {str(e)}")
    raise

# ProxyMesh configuration
PROXY_LIST = [
    'us-wa.proxymesh.com:31280',
    'us-ny.proxymesh.com:31280',
    'us-ca.proxymesh.com:31280',
]

def get_random_proxy():
    """Get a random proxy from the PROXY_LIST"""
    return random.choice(PROXY_LIST)

def create_proxy_extension():
    """Create a Chrome extension to handle proxy authentication"""
    proxy_username = os.getenv('PROXYMESH_USERNAME')
    proxy_password = os.getenv('PROXYMESH_PASSWORD')
    
    if not proxy_username or not proxy_password:
        raise Exception("ProxyMesh credentials not configured in .env file")
    
    proxy_host = get_random_proxy()
    
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (
        proxy_host.split(':')[0],  # host
        proxy_host.split(':')[1],  # port
        proxy_username,
        proxy_password
    )

    # Create a temporary directory for the extension
    extension_dir = tempfile.mkdtemp()
    
    # Create manifest.json
    with open(os.path.join(extension_dir, "manifest.json"), "w") as f:
        f.write(manifest_json)
    
    # Create background.js
    with open(os.path.join(extension_dir, "background.js"), "w") as f:
        f.write(background_js)
    
    return extension_dir, proxy_host

def handle_twitter_login(driver, wait):
    """Handle Twitter login with various possible scenarios"""
    username = os.getenv('TWITTER_USERNAME')
    email = os.getenv('TWITTER_EMAIL')
    password = os.getenv('TWITTER_PASSWORD')

    if not username or not email or not password:
        raise Exception("Twitter credentials not configured in .env file")

    try:
        # Initial username/email input
        username_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        username_input.send_keys(username)
        time.sleep(1)  # Short pause for stability
        
        # Click Next
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']")))
        next_button.click()
        time.sleep(2)  # Wait for next screen to load

        # Check for unusual activity screen
        try:
            unusual_activity = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            print("Additional verification required - entering email")
            unusual_activity.send_keys(email)
            
            # Click Next after entering email
            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']")))
            next_button.click()
            time.sleep(2)
        except TimeoutException:
            print("No unusual activity screen detected")

        # Handle password input
        try:
            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(password)
            time.sleep(1)

            # Click login
            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']")))
            login_button.click()
            time.sleep(3)  # Wait for login to complete

            # Check for additional verification prompts
            try:
                confirm_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Confirm your identity')]"))
                )
                raise Exception("Additional identity verification required. Please verify account manually first.")
            except TimeoutException:
                print("No additional verification required")

        except Exception as e:
            raise Exception(f"Failed during password step: {str(e)}")

    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")

def scrape_twitter_trends():
    """Main function to scrape Twitter trends"""
    driver = None
    extension_dir = None
    try:
        # Create proxy extension
        extension_dir, proxy_address = create_proxy_extension()
        
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--load-extension={extension_dir}')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')

        # Initialize driver
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Chrome driver: {str(e)}")

        try:
            # Login to Twitter
            driver.get('https://twitter.com/login')
            wait = WebDriverWait(driver, 20)
            handle_twitter_login(driver, wait)
            
            # Go to home page and wait for it to load
            driver.get('https://twitter.com/home')
            time.sleep(5)  # Wait for page to load
            
            """
            print("Looking for What's happening section...")  # Debug log
            
            # Find the "What's happening" section and trends
            whats_happening = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//h2[text()=\"What's happening\"]")))
            print("Found What's happening section")  # Debug log
            
            # Get the parent container of the trends
            trends_container = whats_happening.find_element(By.XPATH, "./following-sibling::div")
            print("Found trends container")  # Debug log
            
            # Get all trend elements
            trends = trends_container.find_elements(By.XPATH, ".//div[@data-testid='trend']")[:5]
            print(f"Found {len(trends)} trends")  # Debug log
            
            # Extract trend text
            trend_texts = []
            for trend in trends:
                try:
                    # Try to get the trend text
                    trend_text = trend.find_element(By.XPATH, ".//span").text.strip()
                    if not trend_text:  # If span is empty, try getting the whole text
                        trend_text = trend.text.split('\n')[0].strip()
                    if trend_text:
                        trend_texts.append(trend_text)
                        print(f"Found trend: {trend_text}")  # Debug log
                except Exception as e:
                    print(f"Error extracting trend text: {str(e)}")  # Debug log
                    continue

            # Ensure we have exactly 5 trends
            while len(trend_texts) < 5:
                trend_texts.append("")

            # Create document
            document = {
                "_id": str(uuid.uuid4()),
                "nameoftrend1": trend_texts[0],
                "nameoftrend2": trend_texts[1],
                "nameoftrend3": trend_texts[2],
                "nameoftrend4": trend_texts[3],
                "nameoftrend5": trend_texts[4],
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": proxy_address
            }
            
            """
            
             # Wait for trends to load
            trends = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "[data-testid='trend']")))[:5]
            trend_texts = [trend.text.split('\n')[0] for trend in trends]
            document = {
                "_id": str(uuid.uuid4()),
                "nameoftrend1": trend_texts[0] if len(trend_texts) > 0 else "",
                "nameoftrend2": trend_texts[1] if len(trend_texts) > 1 else "",
                "nameoftrend3": trend_texts[2] if len(trend_texts) > 2 else "",
                "nameoftrend4": trend_texts[3] if len(trend_texts) > 3 else "",
                "nameoftrend5": trend_texts[4] if len(trend_texts) > 4 else "",
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ip_address": proxy_address
            }

            # Save to MongoDB
            try:
                collection.insert_one(document)
                print("Successfully saved to MongoDB")
            except Exception as e:
                raise Exception(f"Failed to save to MongoDB: {str(e)}")

            return document

        except Exception as e:
            raise Exception(f"Failed during Twitter scraping: {str(e)}")

    finally:
        if driver:
            driver.quit()
        if extension_dir and os.path.exists(extension_dir):
            import shutil
            shutil.rmtree(extension_dir)

@app.route('/')
def home():
    """Handle the home endpoint"""
    return render_template('index.html')

@app.route('/scrape')
def scrape():
    """Handle the scrape endpoint"""
    print("Scrape route accessed")
    try:
        result = scrape_twitter_trends()
        return jsonify(result)
    except Exception as e:
        print(f"Error in scrape route: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)