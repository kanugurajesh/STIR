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
    # Add more proxy addresses as needed
]

def get_random_proxy():
    return random.choice(PROXY_LIST)

def scrape_twitter_trends():
    driver = None
    try:
        # Setup Chrome options
        chrome_options = webdriver.ChromeOptions()
        proxy = get_random_proxy()
        chrome_options.add_argument(f'--proxy-server={proxy}')
        chrome_options.add_argument('--headless')

        # Initialize driver
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), 
                                    options=chrome_options)
        except Exception as e:
            raise Exception(f"Failed to initialize Chrome driver: {str(e)}")

        # Login to Twitter
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
                "ip_address": proxy
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