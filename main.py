from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import uuid
from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import random
import os
import json
import tempfile
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

def scrape_twitter_trends():
    driver = None
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
        # chrome_options.add_argument('--headless')  # Uncomment for headless mode

        # Initialize driver
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        except Exception as e:
            raise Exception(f"Failed to initialize Chrome driver: {str(e)}")

        try:
            driver.get('https://twitter.com/login')
            wait = WebDriverWait(driver, 20)

            username = os.getenv('TWITTER_USERNAME')
            password = os.getenv('TWITTER_PASSWORD')

            if not username or not password:
                raise Exception("Twitter credentials not configured in .env file")

            username_input = wait.until(EC.presence_of_element_located((By.NAME, "text")))
            username_input.send_keys(username)

            next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']")))
            next_button.click()

            password_input = wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(password)

            login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']")))
            login_button.click()

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

            try:
                collection.insert_one(document)
            except Exception as e:
                raise Exception(f"Failed to save to MongoDB: {str(e)}")

            return document

        except Exception as e:
            raise Exception(f"Failed during Twitter scraping: {str(e)}")

    finally:
        if driver:
            driver.quit()
        # Clean up the temporary extension directory
        if os.path.exists(extension_dir):
            import shutil
            shutil.rmtree(extension_dir)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/scrape')
def scrape():
    try:
        result = scrape_twitter_trends()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)