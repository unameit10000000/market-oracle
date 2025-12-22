# Market Oracle API 🔮

**Flask REST API for AI-Powered Crypto Market Analysis**

This is the backend API server for Market Oracle. It provides REST endpoints for validating YouTube URLs, running AI-powered analysis, and processing results. The API can be used standalone via HTTP requests or integrated with the Market Oracle frontend application.

> **Note:** This API is part of the Market Oracle system. See the [main README](../README.md) for the complete system overview and quick start guide.

## 🌟 Features

### 📅 Economic Calendar Integration
- **ForexFactory Scraper**: Automatically scrapes economic events from ForexFactory calendar
- **TradingEconomics Scraper**: Extracts events from TradingEconomics calendar
- **Date Filtering**: Configurable date ranges for targeted event analysis
- **Event Parsing**: Extracts event details including dates, countries, impact levels, and forecasts

### 🎥 YouTube Transcript Analysis
- **Automated Transcript Extraction**: Downloads and processes YouTube video transcripts using `yt-dlp`
- **Multi-Video Support**: Processes multiple analyst videos simultaneously
- **Content Deduplication**: Intelligently removes duplicate content from transcripts
- **Analyst Insights**: Extracts predictions, scenarios, and technical analysis from crypto analyst videos

### 🤖 AI-Powered Analysis
- **Historical Event Analysis**: Uses Anthropic Claude AI to analyze historical market events (2020-2025) and their impact on crypto prices
- **Pattern Recognition**: Identifies correlations between economic events and price movements
- **Short-Term Predictions**: Generates directional predictions (PUMP/DUMP) with magnitude estimates based on historical precedents
- **Comprehensive Reports**: Creates detailed analysis reports combining all data sources

### 📊 Prediction Engine
- **Directional Predictions**: Makes clear directional calls (PUMP, DUMP, MAJOR PUMP, MAJOR DUMP, CRITICAL PUMP, CRITICAL DUMP)
- **Conditional Predictions**: Handles conditional scenarios (e.g., "PUMP IF CUT", "DUMP IF WEAK")
- **Magnitude Estimates**: Provides percentage-based magnitude estimates (e.g., 3-5%, 4-8%) based on historical patterns
- **Risk Assessment**: Includes risk management advice and scenario probabilities

## 🏗️ Architecture

The API is built with **Flask** and provides a RESTful interface for:

1. **YouTube Transcript Extraction** - Validates YouTube URLs and extracts video transcripts
2. **Economic Calendar Scraping** - Scrapes events from ForexFactory and TradingEconomics
3. **AI-Powered Analysis** - Uses Claude AI to analyze events and generate predictions
4. **Data Processing** - Generates CSV data and comprehensive analysis reports

### How It Works

1. **Analysis Directory Structure**: Each analysis run creates a timestamped directory (`analysis/YYYYMMDD_HHMMSS/`) that stores all outputs
2. **State Management**: The API uses `analysis_id` (timestamp) to track and retrieve analysis results
3. **Workflow**: Validate → Analyze → Process (3-step workflow)
4. **CORS**: Configured to allow requests from the frontend application

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Anthropic API key or OpenRouter API key (for AI analysis)
- Internet connection (for scraping and YouTube downloads)

### Installation

1. **Navigate to the API directory**
   ```bash
   cd api
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv env
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     env\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source env/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the `/api` directory with your configuration:
   ```env
   # Required: Choose AI provider
   AI_API_TYPE=ANTHROPIC  # or OPENROUTER
   
   # Required: API key (choose based on AI_API_TYPE)
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   # or
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   
   # Optional: Economic calendar configuration
   FOREXFACTORY_START_DATE=2025-12-14
   FOREXFACTORY_USE_WEEK=true
   TRADINGECONOMICS_START_DATE=2025-12-15
   TRADINGECONOMICS_END_DATE=2025-12-21
   ```

### Running the API Server

**As a Flask API server (for frontend integration):**
```bash
python main.py --api
```

The API will start on `http://localhost:5000`

**As a standalone script (original behavior):**
```bash
python main.py
```

This runs the full analysis pipeline using environment variables for configuration.

### Configuration

All configuration is done through the `.env` file. Copy `.env.template` to `.env` and customize the following:

#### Required Variables

1. **AI Provider Selection**
   ```env
   # Choose which AI provider to use: 'ANTHROPIC' or 'OPENROUTER'
   # Default: ANTHROPIC
   AI_API_TYPE=ANTHROPIC
   ```

2. **API Key** (choose based on `AI_API_TYPE`)
   ```env
   # If AI_API_TYPE=ANTHROPIC:
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   # Get your API key from: https://console.anthropic.com/
   
   # If AI_API_TYPE=OPENROUTER:
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   # Get your API key from: https://openrouter.ai/
   ```

#### Optional Variables

These variables are optional and used as defaults. When using the API endpoints, they can be overridden per request.

3. **ForexFactory Configuration**
   ```env
   # Start date for ForexFactory scraping (format: YYYY-MM-DD)
   # Leave empty or set to "None" to use current week
   FOREXFACTORY_START_DATE=
   
   # Whether to use week-based scraping (true) or day-based scraping (false)
   # Default: true
   FOREXFACTORY_USE_WEEK=true
   ```

4. **TradingEconomics Configuration**
   ```env
   # Start date for TradingEconomics scraping (format: YYYY-MM-DD)
   # Leave empty or set to "None" to use default recent dates
   TRADINGECONOMICS_START_DATE=
   
   # End date for TradingEconomics scraping (format: YYYY-MM-DD)
   # Leave empty or set to "None" to use default recent dates
   TRADINGECONOMICS_END_DATE=
   ```

5. **YouTube URLs** (only needed for standalone script mode)
   ```env
   # This is only used when running the script directly (python main.py without --api)
   # When using the API endpoints, YouTube URLs are provided in the /validate request
   # Comma-separated list of YouTube URLs to extract transcripts from
   YOUTUBE_URLS=https://www.youtube.com/watch?v=bgV5FnP8gpA,https://www.youtube.com/watch?v=FZyVMrIZ26Q,...
   ```

6. **Polymarket API Keys** (optional - for enhanced features)
   ```env
   # These keys are optional. The Polymarket API works without keys for public data access.
   # API keys are only needed for enhanced features like authenticated endpoints.
   POLY_API_KEY=your_polymarket_api_key_here
   POLY_API_SECRET=your_polymarket_api_secret_here
   POLY_API_PASSPHRASE=your_polymarket_api_passphrase_here
   ```

**Note:** When using the API mode (`python main.py --api`), `YOUTUBE_URLS` is not needed since URLs are provided via the `/validate` endpoint. It's only required when running the standalone script mode.

See `.env.template` for a complete example with all configuration options and detailed comments.

### Polymarket API Keys

The Polymarket Tracking module works **without API keys** for accessing public market data. However, if you want to access enhanced features or authenticated endpoints, you can optionally configure API keys.

#### How to Get Polymarket API Keys

1. **Navigate to Polymarket Settings:**
   - Go to [https://polymarket.com/settings?tab=builder](https://polymarket.com/settings?tab=builder)
   - Or click your profile icon → "Builders" in the Polymarket interface

2. **Create API Keys:**
   - Click the "Create" or "Create New" button
   - A popup will appear with your API credentials:
     - `apiKey` - Your Polymarket API key
     - `secret` - Your API secret
     - `passphrase` - Your API passphrase

3. **Add to .env File:**
   Copy the values into your `.env` file:
   ```env
   POLY_API_KEY=your_api_key_here
   POLY_API_SECRET=your_secret_here
   POLY_API_PASSPHRASE=your_passphrase_here
   ```

4. **Restart the API Server:**
   After adding the keys, restart your API server for the changes to take effect.

**Important Notes:**
- API keys are **optional** - the Polymarket module works with public data without keys
- The frontend will warn you if keys are not configured but allow you to continue
- Keep your API keys secure and never commit them to version control
- Legacy variable names (`POLYMARKET_API_KEY`, etc.) are also supported for backward compatibility

## 📡 API Endpoints

The API provides the following REST endpoints:

### `GET /`
**Status endpoint** - Returns API status and available endpoints

**Response:**
```json
{
  "status": "running",
  "app": "Crypto Analysis Market Oracle API",
  "version": "1.0.0",
  "endpoints": { ... },
  "api_key_configured": true,
  "api_type": "ANTHROPIC"
}
```

### `POST /validate`
**Validate YouTube URLs and extract transcripts**

**Request Body:**
```json
{
  "youtube_urls": [
    "https://www.youtube.com/watch?v=VIDEO_ID_1",
    "https://www.youtube.com/watch?v=VIDEO_ID_2"
  ]
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_id": "20251220_152704",
  "transcripts": [
    {
      "url": "https://www.youtube.com/watch?v=VIDEO_ID_1",
      "success": true,
      "video_id": "VIDEO_ID_1",
      "error": null
    }
  ],
  "summary": {
    "total": 2,
    "successful": 2,
    "failed": 0
  },
  "message": "Validation completed"
}
```

**What it does:**
- Validates YouTube URLs
- Downloads and extracts transcripts using `yt-dlp`
- Creates an analysis directory with timestamp (`analysis_id`)
- Saves transcripts to the analysis directory
- Returns validation results and `analysis_id` for subsequent requests

### `POST /analyze`
**Run AI analysis with economic calendar data**

**Request Body:**
```json
{
  "analysis_id": "20251220_152704",
  "forexfactory_start_date": "2025-12-14",
  "forexfactory_use_week": true,
  "tradingeconomics_start_date": "2025-12-15",
  "tradingeconomics_end_date": "2025-12-21"
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_id": "20251220_152704",
  "message": "Analysis completed successfully"
}
```

**What it does:**
- Scrapes economic calendar events from ForexFactory and TradingEconomics
- Loads transcripts from the analysis directory
- Runs AI analysis combining:
  - Historical event patterns (2020-2025)
  - Recent economic events
  - YouTube analyst insights
- Generates comprehensive analysis with predictions
- Saves results to `comprehensive_analysis.txt` in the analysis directory

**Note:** All calendar configuration fields are optional. If not provided, defaults from `.env` or system defaults are used.

### `POST /process`
**Process analysis and generate CSV data**

**Request Body:**
```json
{
  "analysis_id": "20251220_152704"
}
```

**Response:**
```json
{
  "status": "success",
  "analysis_directory": "analysis/20251220_152704",
  "csv_data": "Token,Date,Event_Type,Title,...",
  "comprehensive_analysis": "Full analysis text...",
  "forexfactory_events_count": 130,
  "tradingeconomics_events_count": 65,
  "youtube_transcripts_count": 7,
  "message": "Processing completed successfully"
}
```

**What it does:**
- Reads the comprehensive analysis from the analysis directory
- Parses the analysis and generates structured CSV data
- Returns CSV data, full analysis text, and event counts
- Saves CSV to `output.csv` in the analysis directory

### `POST /ask-ai`
**Ask AI about a specific event with web search**

**Request Body:**
```json
{
  "question": "What is the current status of this event?",
  "event": {
    "Token": "Bitcoin",
    "Date": "2025-12-25",
    "Title": "Fed Interest Rate Decision",
    ...
  },
  "analysis_id": "20251220_212438",
  "max_searches": 5,
  "max_tokens": 4000
}
```

**Response:**
```json
{
  "status": "success",
  "response": "AI-generated response with current information...",
  "question": "What is the current status of this event?",
  "event": { ... },
  "api_type": "ANTHROPIC"
}
```

**What it does:**
- Uses web search to find current information about the event
- Optionally includes comprehensive analysis context if `analysis_id` is provided
- Returns AI-generated response with up-to-date information

## 🔄 API Workflow

The API follows a 3-step workflow:

1. **Validate** (`POST /validate`)
   - Input: YouTube URLs
   - Output: `analysis_id` and validation results
   - Creates analysis directory and extracts transcripts

2. **Analyze** (`POST /analyze`)
   - Input: `analysis_id` + optional calendar configuration
   - Output: Analysis completion status
   - Scrapes calendars, runs AI analysis, saves results

3. **Process** (`POST /process`)
   - Input: `analysis_id`
   - Output: CSV data and comprehensive analysis
   - Generates structured data for frontend consumption

## 🔐 Security Notes

- **API keys are server-side only** - Never send API keys in request bodies
- **API keys must be in `.env` file** - The API reads keys from environment variables only
- **CORS is configured** - Only allows requests from `http://localhost:3000` and `http://127.0.0.1:3000`
- **Request validation** - All endpoints validate required parameters and return appropriate error messages

### Output Structure

Each analysis run creates a timestamped directory with:

```
analysis/
└── YYYYMMDD_HHMMSS/
    ├── forexfactory_events.json          # Scraped ForexFactory events
    ├── tradingeconomics_events.json      # Scraped TradingEconomics events
    ├── historic_events_analysis.txt      # AI analysis of historical events
    ├── recent_events_analysis.txt         # AI analysis of recent events
    ├── comprehensive_analysis.txt        # Full combined analysis
    ├── ai_prompt.txt                     # Full AI prompt used
    ├── *_transcript.txt                  # Individual YouTube transcripts
    └── analysis/                         # VTT subtitle files
```

### 📌 Final Analysis Result

> **The final comprehensive analysis result is saved to:** `analysis/<datetime>/comprehensive_analysis.txt`
>
> This file contains the complete AI-powered analysis combining:
> - Economic calendar events (ForexFactory & TradingEconomics)
> - YouTube analyst transcripts and insights
> - Historical event pattern analysis
> - Directional predictions with magnitude estimates
> - Risk assessment and scenario analysis

## 📋 Key Components

### Economic Calendar Scrapers
- **`scrape_forexfactory()`**: Scrapes ForexFactory calendar events
- **`scrape_tradingeconomics()`**: Scrapes TradingEconomics calendar events
- Both support date filtering and return structured event data

### YouTube Transcript Processing
- **`extract_youtube_transcripts()`**: Downloads and extracts transcripts from multiple videos
- **`collect_transcripts()`**: Combines all transcripts into a single text
- **`extract_vtt_content()`**: Parses VTT subtitle files and removes duplicates

### AI Analysis Functions
- **`get_historic_events()`**: Analyzes historical market events and their impact
- **`insert_recently_predicted_events()`**: Analyzes recent events and price correlations
- **`process_events()`**: Combines all data sources into comprehensive analysis

## 🎯 Use Cases

- **Traders**: Get AI-powered predictions on upcoming economic events and their potential impact on crypto prices
- **Analysts**: Combine multiple data sources (economic calendars, analyst videos, historical patterns) in one place
- **Researchers**: Study correlations between economic events and cryptocurrency price movements
- **Content Creators**: Extract and analyze insights from multiple crypto analyst videos simultaneously

## 🔧 Technical Details

### Dependencies
- `beautifulsoup4`: HTML parsing for web scraping
- `requests`: HTTP requests for web scraping
- `anthropic`: Anthropic Claude AI API client
- `python-dotenv`: Environment variable management
- `yt-dlp`: YouTube video and subtitle downloading

### AI Models

**Anthropic (default):**
- Default: `claude-sonnet-4` (latest Sonnet 4)
- Available models: Claude Opus 4, Claude Sonnet 4, Claude 3.7 Sonnet, Claude 3.5 Sonnet, Claude 3 Haiku
- Max tokens: 32,000-56,000 depending on analysis type
- Streaming responses for real-time output

**OpenRouter:**
- Default: `anthropic/claude-sonnet-4.5`
- Available models: Multiple Claude models, GPT models, Gemini, DeepSeek, and more
- Supports model selection via API configuration
- Max tokens: Configurable per request

### Flask Configuration
- **Host**: `0.0.0.0` (all interfaces)
- **Port**: `5000`
- **Debug Mode**: Enabled when running with `--api` flag
- **CORS**: Enabled for frontend integration

## 📝 Important Notes

- **Analysis directories persist** - All analysis results are saved in `analysis/` directory for historical reference
- **Transcript caching** - YouTube transcripts are saved locally to avoid re-downloading
- **HTML test files** - The app can use HTML files from `temp/htmlsources/` for testing scraping logic
- **Production scraping** - In production, it fetches live data from ForexFactory and TradingEconomics
- **Error handling** - All endpoints return structured error responses with appropriate HTTP status codes
- **Logging** - The API logs all operations to help with debugging

## 🧪 Testing the API

You can test the API endpoints using:

1. **HTTP client files** - See `api.http` for example requests
2. **cURL** - Use curl commands to test endpoints
3. **Frontend application** - Use the Market Oracle frontend for interactive testing
4. **Postman/Insomnia** - Import the endpoints for API testing

Example using cURL:

```bash
# Check API status
curl http://localhost:5000/

# Validate YouTube URLs
curl -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -d '{"youtube_urls": ["https://www.youtube.com/watch?v=VIDEO_ID"]}'
```

## 🤝 Contributing

We welcome all contributions! Whether it's fixing bugs, adding features, improving documentation, or adding new data sources - every contribution helps.

**Quick start:**
1. Check out [contributing.md](contributing.md) for simple guidelines
2. Fork the repo, create a branch, make your changes
3. Test locally and submit a pull request

See our [code of conduct](code-of-conduct.md) for community guidelines.

## ⚠️ Disclaimer

This tool is for informational and research purposes only. The predictions and analysis generated by Market Oracle are based on historical patterns and AI analysis, not financial advice. Always do your own research and consult with financial professionals before making trading decisions. Cryptocurrency trading involves substantial risk of loss.

## 📄 License

[Add your license here]

---

**Built with ❤️ for the crypto trading community**
