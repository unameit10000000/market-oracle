# Market Oracle 🔮

**AI-Powered Crypto Market Analysis & Prediction Tool**

Market Oracle is an intelligent cryptocurrency market analysis system that combines economic calendar data, YouTube analyst transcripts, and historical event analysis to generate actionable trading insights and short-term price predictions for Bitcoin, XRP, and other major cryptocurrencies.

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

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Anthropic API key (for AI analysis)
- Internet connection (for scraping and YouTube downloads)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cryptowizard
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   Copy `.env.template` to `.env` and configure your settings:
   ```bash
   cp .env.template .env
   ```
   
   Then edit `.env` and set your configuration values. See `.env.template` for all available options.

### Configuration

All configuration is done through the `.env` file. Copy `.env.template` to `.env` and customize the following:

1. **Anthropic API Key** (required)
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```
   Get your API key from: https://console.anthropic.com/

2. **ForexFactory Configuration**
   ```env
   # Start date for ForexFactory scraping (format: YYYY-MM-DD)
   # Leave empty or set to "None" to use current week
   FOREXFACTORY_START_DATE=2025-12-14
   
   # Whether to use week-based scraping (true) or day-based scraping (false)
   FOREXFACTORY_USE_WEEK=true
   ```

3. **TradingEconomics Configuration**
   ```env
   # Start date for TradingEconomics scraping (format: YYYY-MM-DD)
   # Leave empty or set to "None" to use default recent dates
   TRADINGECONOMICS_START_DATE=2025-12-15
   
   # End date for TradingEconomics scraping (format: YYYY-MM-DD)
   TRADINGECONOMICS_END_DATE=2025-12-21
   ```

4. **YouTube URLs**
   ```env
   # Comma-separated list of YouTube URLs to extract transcripts from
   YOUTUBE_URLS=https://www.youtube.com/watch?v=VIDEO_ID_1,https://www.youtube.com/watch?v=VIDEO_ID_2
   ```

See `.env.template` for a complete example with all configuration options and detailed comments.

### Usage

Run the full analysis pipeline:

```bash
python main.py
```

This will:
1. Scrape economic calendars from ForexFactory and TradingEconomics
2. Extract YouTube transcripts from configured videos
3. Analyze historical events using AI
4. Process all data and generate comprehensive analysis
5. Save all outputs to `analysis/<timestamp>/` directory

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

### AI Model
- Uses **Claude Sonnet 4.5** (claude-sonnet-4-5-20250929)
- Max tokens: 32,000-56,000 depending on analysis type
- Streaming responses for real-time output

## 📝 Notes

- The app uses HTML files from `temp/htmlsources/` for testing scraping logic
- In production, it fetches live data from ForexFactory and TradingEconomics
- YouTube transcripts are cached locally to avoid re-downloading
- All analysis outputs are timestamped and saved for historical reference

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
