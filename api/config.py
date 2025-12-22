"""
Configuration module - Loads and manages all configuration from environment variables
"""

import os
import logging
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Loaded from .env file
# ============================================================================

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a date string from environment variable.
    
    Args:
        date_str: Date string in format YYYY-MM-DD, "None", or empty string
        
    Returns:
        datetime object or None
    """
    if not date_str or date_str.strip().lower() in ('none', ''):
        return None
    try:
        return datetime.strptime(date_str.strip(), '%Y-%m-%d')
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}. Expected YYYY-MM-DD. Using None.")
        return None

def parse_bool(bool_str: Optional[str]) -> bool:
    """
    Parse a boolean string from environment variable.
    
    Args:
        bool_str: String "true", "false", "True", "False", "1", "0", etc.
        
    Returns:
        bool value
    """
    if not bool_str:
        return False
    return bool_str.strip().lower() in ('true', '1', 'yes', 'on')

def parse_youtube_urls(urls_str: Optional[str]) -> List[str]:
    """
    Parse comma-separated YouTube URLs from environment variable.
    
    Args:
        urls_str: Comma-separated list of YouTube URLs
        
    Returns:
        List of YouTube URLs (stripped of whitespace)
    """
    if not urls_str:
        return []
    # Split by comma and strip whitespace
    urls = [url.strip() for url in urls_str.split(',') if url.strip()]
    return urls

# ForexFactory date/week configuration
FOREXFACTORY_START_DATE = parse_date(os.getenv('FOREXFACTORY_START_DATE'))
FOREXFACTORY_USE_WEEK = parse_bool(os.getenv('FOREXFACTORY_USE_WEEK', 'true'))

# TradingEconomics date configuration
TRADINGECONOMICS_START_DATE = parse_date(os.getenv('TRADINGECONOMICS_START_DATE'))
TRADINGECONOMICS_END_DATE = parse_date(os.getenv('TRADINGECONOMICS_END_DATE'))

# YouTube transcript configuration
YOUTUBE_URLS = parse_youtube_urls(os.getenv('YOUTUBE_URLS'))

# AI API Type configuration
AI_API_TYPE = os.getenv('AI_API_TYPE', 'ANTHROPIC')
logger.info(f"AI API Type set to: {AI_API_TYPE}")

# Model lists for each API type
OPENROUTER_MODELS = [
    "anthropic/claude-sonnet-4.5",
    "anthropic/claude-opus-4.5", 
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-opus",
    "anthropic/claude-3.7-sonnet",
    "openai/gpt-5.1",
    "openai/gpt-5-nano",
    "openai/gpt-5.2",
    "openai/gpt-5.2-pro",
    "openai/gpt-5.1-codex-max",
    "openai/gpt-4",
    "openai/gpt-4o-mini",
    "openai/o3-mini",
    "google/gemini-3-pro-preview",
    "google/gemini-2.5-pro-preview",
    "deepseek/deepseek-v3.2",
    "deepseek/deepseek-r1",
    "minimax/minimax-m2:exacto",
    "openrouter/auto",
    "openrouter/bodybuilder"
]

ANTHROPIC_MODELS = [
    "claude-opus-4-1",                 # alias for latest 4.1 snapshot
    "claude-opus-4-1-20250805",        # specific snapshot
    "claude-opus-4",                   # alias for latest 4.0 snapshot
    "claude-opus-4-20250514",          # specific snapshot
    "claude-sonnet-4",                 # alias for Sonnet-4
    "claude-sonnet-4-20250514",        # specific snapshot
    # Claude 3.7 Sonnet
    "claude-3-7-sonnet",               # alias
    "claude-3-7-sonnet-20250219",      # specific snapshot
    # Claude 3.5 – two variants
    "claude-3-5-sonnet",               # alias for Sonnet 3.5
    "claude-3-5-sonnet-20241022",      # specific snapshot
    "claude-3-5-haiku",                # alias for Haiku 3.5
    "claude-3-5-haiku-20241022",       # specific snapshot
    # Older smaller models (still available)
    "claude-3-haiku",                  # alias
    "claude-3-haiku-20240307",         # specific snapshot
]

# Default models (latest Sonnet for each API type)
DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4.5"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4"

# Get the default model based on API type
DEFAULT_MODEL = DEFAULT_OPENROUTER_MODEL if AI_API_TYPE == 'OPENROUTER' else DEFAULT_ANTHROPIC_MODEL

# Initialize API keys and client
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# Initialize Anthropic client (or OpenRouter wrapper)
anthropic_client = None
if AI_API_TYPE == 'OPENROUTER':
    if OPENROUTER_API_KEY:
        try:
            anthropic_client = Anthropic(
                api_key=OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api"
            )
            logger.info("OpenRouter client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenRouter client: {e}")
            anthropic_client = None
    else:
        logger.warning("OPENROUTER_API_KEY not found in .env file")
else:
    if ANTHROPIC_API_KEY:
        try:
            anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("Anthropic client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic client: {e}")
            anthropic_client = None
    else:
        logger.warning("ANTHROPIC_API_KEY not found in .env file")

# Global variable for analysis directory
ANALYSIS_DIR = None


def init_analysis_directory() -> str:
    """
    Initialize and create the analysis/<datetime>/ directory.
    
    Returns:
        Path to the analysis directory
    """
    global ANALYSIS_DIR
    from datetime import datetime
    datetime_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    ANALYSIS_DIR = os.path.join("analysis", datetime_str)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    logger.info(f"Initialized analysis directory: {ANALYSIS_DIR}")
    return ANALYSIS_DIR

