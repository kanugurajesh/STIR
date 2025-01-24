import pytest
from main import app, create_proxy_extension, get_random_proxy
import os
from unittest.mock import patch, MagicMock
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_route(client):
    """Test the home route returns correct template"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Twitter Trends Scraper' in response.data

def test_get_random_proxy():
    """Test random proxy selection"""
    proxy = get_random_proxy()
    assert isinstance(proxy, str)
    assert '.proxymesh.com:31280' in proxy
    assert proxy.startswith('us-')

@patch.dict(os.environ, {
    'PROXYMESH_USERNAME': 'test_user',
    'PROXYMESH_PASSWORD': 'test_pass'
})
def test_create_proxy_extension():
    """Test proxy extension creation"""
    extension_dir, proxy_host = create_proxy_extension()
    
    # Check if extension directory was created
    assert os.path.exists(extension_dir)
    
    # Check if manifest.json exists
    manifest_path = os.path.join(extension_dir, "manifest.json")
    assert os.path.exists(manifest_path)
    
    # Check if background.js exists
    background_path = os.path.join(extension_dir, "background.js")
    assert os.path.exists(background_path)
    
    # Check proxy host format
    assert '.proxymesh.com:31280' in proxy_host

@patch.dict(os.environ, {})
def test_create_proxy_extension_missing_credentials():
    """Test proxy extension creation with missing credentials"""
    with pytest.raises(Exception) as exc_info:
        create_proxy_extension()
    assert "ProxyMesh credentials not configured" in str(exc_info.value)

@patch('main.webdriver.Chrome')
@patch('main.handle_twitter_login')
def test_scrape_twitter_trends_success(mock_login, mock_chrome):
    """Test successful scraping of Twitter trends"""
    # Mock the Chrome driver and its methods
    mock_driver = MagicMock()
    mock_chrome.return_value = mock_driver
    
    # Mock finding trending topics
    mock_elements = [MagicMock() for _ in range(3)]
    for i, element in enumerate(mock_elements):
        element.text = f"Trend {i+1}"
    
    mock_driver.find_elements.return_value = mock_elements
    
    # Call the endpoint
    with app.test_client() as client:
        response = client.get('/scrape')
        assert response.status_code == 200
        data = response.get_json()
        assert '_id' in data
        assert 'nameoftrend1' in data
        assert 'datetime' in data
        assert 'ip_address' in data

@patch('main.webdriver.Chrome')
def test_scrape_twitter_trends_failure(mock_chrome):
    """Test scraping failure handling"""
    # Mock Chrome driver to raise an exception
    mock_chrome.side_effect = TimeoutException("Failed to load page")
    
    # Call the endpoint
    with app.test_client() as client:
        response = client.get('/scrape')
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
