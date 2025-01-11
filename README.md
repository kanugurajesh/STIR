# STIR (Social Trends Information Retriever)

A web application that scrapes Twitter trends in real-time using Selenium WebDriver and displays them through a modern web interface. The application uses proxies for reliable data collection and stores the results in MongoDB.

## Features

- Real-time Twitter trends scraping
- Proxy rotation system using ProxyMesh
- MongoDB integration for data persistence
- Modern, responsive web interface with:
  - Loading indicators during data fetch
  - Error handling with user-friendly messages
  - Clean, professional styling
  - Real-time updates

## Prerequisites

- Python 3.7+
- Chrome browser
- MongoDB
- ProxyMesh account
- Twitter account

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/stir.git
cd stir
```

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following configurations:
```env
MONGODB_URI=your_mongodb_connection_string
PROXYMESH_USERNAME=your_proxymesh_username
PROXYMESH_PASSWORD=your_proxymesh_password
TWITTER_USERNAME=your_twitter_username
TWITTER_PASSWORD=your_twitter_password
```

## Usage

1. Start the Flask application:
```bash
python main.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Click the "Fetch Latest Trends" button to retrieve current Twitter trends

## Technical Details

### Components

- **Frontend**: HTML, CSS, JavaScript
  - Modern UI with loading states
  - Error handling
  - Responsive design
  - Real-time updates

- **Backend**: Python Flask
  - Selenium WebDriver for scraping
  - Proxy rotation system
  - MongoDB integration
  - Error handling and logging

### Data Flow

1. User initiates scraping through web interface
2. Backend selects random proxy from ProxyMesh pool
3. Selenium WebDriver launches Chrome with proxy configuration
4. Application logs into Twitter and scrapes trend data
5. Data is stored in MongoDB and returned to frontend
6. Frontend displays formatted results with loading states and error handling

## Error Handling

The application includes comprehensive error handling for:
- MongoDB connection failures
- Proxy authentication issues
- Twitter login problems
- Network timeouts
- Data scraping errors

All errors are properly logged and displayed to users through the UI.

## Security

- Environment variables for sensitive credentials
- Proxy authentication for IP rotation
- Secure MongoDB connection
- Error messages sanitized for user display

## Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/YourFeature`
3. Commit your changes: `git commit -am 'Add YourFeature'`
4. Push to the branch: `git push origin feature/YourFeature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Twitter for providing the trend data
- ProxyMesh for proxy services
- Selenium WebDriver team
- MongoDB team

## Future Improvements

- [x] Add trend history visualization
- [x] Implement trend analysis features
- [x] Add user authentication
- [x] Support for multiple Twitter accounts
- [x] Advanced proxy configuration options
- [x] Data export functionality
- [x] Real-time trend notifications

## Demo
[![STIR](https://img.youtube.com/vi/LoME2QhzJSo/0.jpg)](https://youtu.be/LoME2QhzJSo)
