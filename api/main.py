"""
Crypto Analysis Bot - Scrapes economic calendars and analyzes events using Anthropic AI

This is the main entry point for the Flask application.
All functionality has been refactored into separate modules:
- config.py: Configuration and environment variables
- utils.py: Utility functions
- scrapers/: Web scraping modules (forexfactory.py, tradingeconomics.py)
- youtube.py: YouTube transcript extraction
- analysis.py: AI analysis functions
- routes/: Flask route handlers (main_routes.py, websearch_routes.py, poly_routes.py)
- poly.py: Polymarket API client (unchanged)
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Flask app from routes module
from routes import app

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Check if running as Flask app or as script
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        # Run as Flask API
        logger.info("Starting Flask API server...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Run as script (original behavior - now moved to separate modules)
        logger.warning("Script mode is deprecated. Use --api flag to run as Flask API, or import functions from modules directly.")
        logger.info("Available modules:")
        logger.info("  - config: Configuration and environment variables")
        logger.info("  - scrapers.forexfactory: ForexFactory scraping")
        logger.info("  - scrapers.tradingeconomics: TradingEconomics scraping")
        logger.info("  - youtube: YouTube transcript extraction")
        logger.info("  - analysis: AI analysis functions")
        logger.info("  - routes: Flask API routes")
