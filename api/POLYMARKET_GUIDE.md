# Polymarket API Usage Guide

This guide explains how to set up, run, and use the Polymarket API integration.

## 📋 Prerequisites

- Python 3.8+
- Dependencies installed (`pip install -r requirements.txt`)
- Flask API server running

## 🔧 Setup

### 1. Environment Variables (Optional)

The Polymarket API works with public endpoints by default, but you can configure optional environment variables in your `.env` file:

```env
# Optional: Custom API base URL (default: https://gamma-api.polymarket.com)
POLYMARKET_API_BASE_URL=https://gamma-api.polymarket.com

# Optional: API credentials (only needed for authenticated endpoints)
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_API_SECRET=your_api_secret_here
POLYMARKET_API_PASSPHRASE=your_passphrase_here
```

**Note:** For most use cases (fetching market data, probabilities, etc.), no API key is required as these are public endpoints.

### 2. Start the API Server

```bash
cd api
python main.py --api
```

The server will start on `http://localhost:5000`

## 🚀 Using the API

### Method 1: Using HTTP Requests (REST Client)

You can use the provided `poly.http` file with REST Client extensions (VS Code, IntelliJ, etc.) or use `curl`, Postman, or any HTTP client.

### Method 2: Using Python

```python
import requests

base_url = "http://localhost:5000"

# Get event data
url = "https://polymarket.com/event/bitcoin-price-on-december-22"
response = requests.get(f"{base_url}/poly/event?url={url}")
print(response.json())
```

### Method 3: Direct Python Module Usage

```python
from poly import get_event_data, get_market_by_id

# Get event data directly
url = "https://polymarket.com/event/bitcoin-price-on-december-22"
event_data = get_event_data(url)
print(event_data)

# Get market by ID
market = get_market_by_id("949335")
print(market)
```

## 📡 Available Endpoints

### 1. Get Complete Event Data

**Endpoint:** `GET /poly/event?url=<polymarket_event_url>`

**Example:**
```bash
curl "http://localhost:5000/poly/event?url=https://polymarket.com/event/bitcoin-price-on-december-22"
```

**Response:**
```json
{
  "status": "success",
  "url": "https://polymarket.com/event/bitcoin-price-on-december-22",
  "event_slug": "bitcoin-price-on-december-22",
  "event": {
    "id": "105983",
    "title": "Bitcoin price on December 22?",
    "markets": [
      {
        "id": "941452",
        "question": "Will the price of Bitcoin be between $88,000 and $90,000 on December 22?",
        "outcomes": "[\"Yes\", \"No\"]",
        "outcomePrices": "[\"0.39\", \"0.61\"]",
        ...
      }
    ],
    ...
  }
}
```

### 2. Get Event Data by Slug

**Endpoint:** `GET /poly/event/slug/<slug>`

**Example:**
```bash
curl "http://localhost:5000/poly/event/slug/bitcoin-price-on-december-22"
```

### 3. Get Reduced List of Markets

**Endpoint:** `GET /poly/event/markets/list?url=<event_url>` or `?slug=<event_slug>`

**Example:**
```bash
curl "http://localhost:5000/poly/event/markets/list?url=https://polymarket.com/event/bitcoin-price-on-december-22"
```

**Response:**
```json
{
  "status": "success",
  "event_slug": "bitcoin-price-on-december-22",
  "markets_count": 11,
  "markets": [
    {
      "id": "941452",
      "details": {
        "outcomes": "[\"Yes\", \"No\"]",
        "outcomePrices": "[\"0.39\", \"0.61\"]",
        "volume": "93224.094799",
        "active": true,
        "closed": false
      }
    },
    ...
  ]
}
```

### 4. Get Detailed Market Data by ID

**Endpoint:** `GET /poly/market/<market_id>`

**Example:**
```bash
curl "http://localhost:5000/poly/market/949335"
```

**Response:**
```json
{
  "status": "success",
  "market_id": "949335",
  "market": {
    "id": "949335",
    "question": "Will the price of Bitcoin be between $86,000 and $88,000 on December 23?",
    "outcomes": "[\"Yes\", \"No\"]",
    "outcomePrices": "[\"0.2\", \"0.8\"]",
    "outcomeProbabilities": {
      "Yes": 0.2,
      "No": 0.8
    },
    "volume": "31828.792012",
    "active": true,
    "closed": false,
    ...
  }
}
```

### 5. Get Outcome Probabilities

**Endpoint:** `GET /poly/probabilities?url=<event_url>&market_slug=<market_slug>`

**Example:**
```bash
# Get probabilities for first market in event
curl "http://localhost:5000/poly/probabilities?url=https://polymarket.com/event/bitcoin-price-on-december-22"

# Get probabilities for specific market
curl "http://localhost:5000/poly/probabilities?url=https://polymarket.com/event/bitcoin-price-on-december-22&market_slug=will-the-price-of-bitcoin-be-between-88000-90000-on-december-22"
```

**Response:**
```json
{
  "status": "success",
  "url": "https://polymarket.com/event/bitcoin-price-on-december-22",
  "event_slug": "bitcoin-price-on-december-22",
  "market_slug": "first",
  "probabilities": {
    "Yes": 0.39,
    "No": 0.61
  }
}
```

## 💡 Usage Examples

### Example 1: Get Market List and Then Detailed Data

```python
import requests

base_url = "http://localhost:5000"
event_url = "https://polymarket.com/event/bitcoin-price-on-december-22"

# Step 1: Get reduced list of markets
response = requests.get(f"{base_url}/poly/event/markets/list?url={event_url}")
data = response.json()

if data['status'] == 'success':
    markets = data['markets']
    print(f"Found {len(markets)} markets")
    
    # Step 2: Get detailed data for first market
    if markets:
        market_id = markets[0]['id']
        market_response = requests.get(f"{base_url}/poly/market/{market_id}")
        market_data = market_response.json()
        print(f"Market: {market_data['market']['question']}")
        print(f"Probabilities: {market_data['market']['outcomeProbabilities']}")
```

### Example 2: Get All Markets with Probabilities

```python
import requests
import json

base_url = "http://localhost:5000"
event_url = "https://polymarket.com/event/bitcoin-price-on-december-22"

# Get event data
response = requests.get(f"{base_url}/poly/event?url={event_url}")
event_data = response.json()

if event_data['status'] == 'success':
    markets = event_data['event']['markets']
    for market in markets:
        # Parse JSON strings
        outcomes = json.loads(market['outcomes'])
        prices = json.loads(market['outcomePrices'])
        
        print(f"\nMarket: {market['question']}")
        for outcome, price in zip(outcomes, prices):
            print(f"  {outcome}: {float(price) * 100:.2f}%")
```

## 🔍 Understanding the Data

### Outcome Probabilities

- **Format**: Decimal values from 0.0 to 1.0
- **Meaning**: 0.39 = 39% probability
- **Sum**: All outcome probabilities for a market should sum to approximately 1.0

### Market Data Structure

- **`id`**: Unique market identifier (use this with `/poly/market/<id>`)
- **`question`**: The market question
- **`outcomes`**: JSON string array of possible outcomes (e.g., `"[\"Yes\", \"No\"]"`)
- **`outcomePrices`**: JSON string array of current prices/probabilities (e.g., `"[\"0.39\", \"0.61\"]"`)
- **`outcomeProbabilities`**: Parsed probabilities as a dictionary (added by our API)
- **`active`**: Whether the market is currently active
- **`closed`**: Whether the market has closed
- **`volume`**: Trading volume
- **`liquidity`**: Market liquidity

### Reduced Market List Format

The `/poly/event/markets/list` endpoint returns a simplified structure:

```json
{
  "id": "949335",
  "details": {
    "outcomes": "[\"Yes\", \"No\"]",
    "outcomePrices": "[\"0.21\", \"0.79\"]",
    "volume": "31785.392012",
    "active": true,
    "closed": false
  }
}
```

Use the `id` from this list to get full market details via `/poly/market/<id>`.

## ⚠️ Error Handling

All endpoints return JSON with a `status` field:

- **`"status": "success"`**: Request succeeded
- **`"status": "error"`**: Request failed, check `error` field

**Example Error Response:**
```json
{
  "status": "error",
  "error": "Failed to fetch event data. Check the URL and try again."
}
```

## 🐛 Troubleshooting

### Server Not Running
```bash
# Make sure the server is running
python main.py --api
```

### Connection Refused
- Check that the server is running on port 5000
- Verify the URL: `http://localhost:5000`

### Invalid URL Error
- Ensure the Polymarket URL is complete and valid
- Check that the URL contains a valid event slug (format: `/event/event-slug`)

### Market Not Found
- Verify the market ID exists
- Check that you're using the correct event slug

### API Rate Limits
- Polymarket's Gamma API has rate limits (~300 requests/10s)
- If you hit limits, add delays between requests

## 📚 Additional Resources

- [Polymarket API Documentation](https://docs.polymarket.com/developers/gamma-markets-api/overview)
- [Gamma Markets API Reference](https://docs.polymarket.com/api-reference/events/get-event-by-slug)
