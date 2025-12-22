"""
Crypto Analysis Bot - Scrapes economic calendars and analyzes events using Anthropic AI
"""

import os
import json
import re
import logging
import subprocess
import glob
import shutil
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify
from flask_cors import CORS
import poly

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION - Loaded from .env file
# ============================================================================
# All configuration is now loaded from environment variables
# See .env.template for configuration options

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
# Loaded from environment variables (see .env.template)
FOREXFACTORY_START_DATE = parse_date(os.getenv('FOREXFACTORY_START_DATE'))
FOREXFACTORY_USE_WEEK = parse_bool(os.getenv('FOREXFACTORY_USE_WEEK', 'true'))

# TradingEconomics date configuration
# Loaded from environment variables (see .env.template)
TRADINGECONOMICS_START_DATE = parse_date(os.getenv('TRADINGECONOMICS_START_DATE'))
TRADINGECONOMICS_END_DATE = parse_date(os.getenv('TRADINGECONOMICS_END_DATE'))

# YouTube transcript configuration
# Loaded from environment variables (see .env.template)
YOUTUBE_URLS = parse_youtube_urls(os.getenv('YOUTUBE_URLS'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# Initialize API keys and client (define both at module level to avoid NameError)
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
    datetime_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    ANALYSIS_DIR = os.path.join("analysis", datetime_str)
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    logger.info(f"Initialized analysis directory: {ANALYSIS_DIR}")
    return ANALYSIS_DIR


def format_forexfactory_date(date: datetime) -> str:
    """
    Format a datetime for ForexFactory URL.
    
    Args:
        date: datetime object
        
    Returns:
        Formatted string like 'dec15.2025'
    """
    month_names = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    month = month_names[date.month - 1]
    day = date.day
    year = date.year
    return f"{month}{day}.{year}"


def get_forexfactory_url(start_date: Optional[datetime] = None, use_week: bool = True) -> str:
    """
    Generate ForexFactory URL based on date configuration.
    
    Args:
        start_date: datetime object or None (None = current week)
        use_week: True to use ?week=, False to use ?day=
        
    Returns:
        ForexFactory calendar URL
    """
    base_url = "https://www.forexfactory.com/calendar"
    
    if start_date is None:
        # Default to current week (Sunday of current week - ForexFactory weeks start on Sunday)
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7  # Monday=0, so +1 makes Sunday=0
        start_date = today - timedelta(days=days_since_sunday)
    
    date_str = format_forexfactory_date(start_date)
    
    if use_week:
        return f"{base_url}?week={date_str}"
    else:
        return f"{base_url}?day={date_str}"


def get_tradingeconomics_url(start_date: Optional[datetime] = None, 
                            end_date: Optional[datetime] = None) -> str:
    """
    Generate TradingEconomics URL based on date configuration.
    
    Args:
        start_date: datetime object or None (None = recent dates)
        end_date: datetime object or None (None = defaults)
        
    Returns:
        TradingEconomics calendar URL
    """
    base_url = "https://tradingeconomics.com/calendar"
    
    # TradingEconomics uses recent dates by default
    # If dates are specified, you might need to add query parameters
    # Check TradingEconomics documentation for exact parameter format
    if start_date and end_date:
        # Format: ?d1=YYYY-MM-DD&d2=YYYY-MM-DD (example format, verify with actual site)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        return f"{base_url}?d1={start_str}&d2={end_str}"
    elif start_date:
        start_str = start_date.strftime('%Y-%m-%d')
        return f"{base_url}?d1={start_str}"
    else:
        # Default: just the calendar URL (shows recent dates)
        return base_url


def scrape_forexfactory(url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scrape ForexFactory calendar events from the provided URL.
    
    Args:
        url: URL to scrape (None = uses FOREXFACTORY_START_DATE config)
        
    Returns:
        List of event dictionaries with date, title, description, etc.
    """
    if url is None:
        url = get_forexfactory_url(FOREXFACTORY_START_DATE, FOREXFACTORY_USE_WEEK)
    
    logger.info(f"Scraping ForexFactory: {url}")
    
    try:
        # Try to read from example file first (use absolute path relative to script location)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example_file = os.path.join(script_dir, "temp", "htmlsources", "forexfactory-calendar.html")
        
        if os.path.exists(example_file):
            logger.info(f"Using cached HTML file: {example_file}")
            with open(example_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            # Use realistic browser headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            logger.info("Fetching from ForexFactory URL with browser headers...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the script tag containing the calendar data
        script_tags = soup.find_all('script')
        events = []
        
        for script in script_tags:
            if script.string and 'days:' in script.string:
                # Extract JSON data from the script
                script_content = script.string
                
                # Find the days array - need to match until the next top-level property
                match = re.search(r'days:\s*(\[.*?\])\s*,', script_content, re.DOTALL)
                if not match:
                    # Try without trailing comma
                    match = re.search(r'days:\s*(\[.*?\])', script_content, re.DOTALL)
                
                if match:
                    days_json = match.group(1)
                    # Clean up escaped HTML entities
                    days_json = days_json.replace('\\/', '/')
                    days_json = days_json.replace('\\"', '"')
                    # Remove trailing commas before closing brackets/braces
                    days_json = re.sub(r',(\s*[}\]])', r'\1', days_json)
                    
                    try:
                        days_data = json.loads(days_json)
                        
                        for day in days_data:
                            date_str = day.get('date', '')
                            # Extract date from HTML span if present (handle escaped HTML)
                            date_match = re.search(r'<span>(.*?)</span>', date_str)
                            if date_match:
                                date_str = date_match.group(1)
                            elif '<span>' in date_str:
                                # Handle escaped version
                                date_match = re.search(r'<span>(.*?)<\\/span>', date_str)
                                if date_match:
                                    date_str = date_match.group(1)
                            
                            # Convert dateline to readable date if available
                            dateline = day.get('dateline', 0)
                            if dateline:
                                try:
                                    date_obj = datetime.fromtimestamp(dateline)
                                    date_str = date_obj.strftime('%Y-%m-%d')
                                except:
                                    pass
                            
                            for event in day.get('events', []):
                                event_data = {
                                    'date': date_str,
                                    'dateline': dateline,
                                    'title': event.get('name', '')[:50],  # Max 50 chars
                                    'description': event.get('soloTitle', event.get('name', ''))[:100],  # Max 100 chars
                                    'country': event.get('country', ''),
                                    'currency': event.get('currency', ''),
                                    'impact': event.get('impactName', ''),
                                    'time': event.get('timeLabel', ''),
                                    'actual': event.get('actual', ''),
                                    'forecast': event.get('forecast', ''),
                                    'previous': event.get('previous', ''),
                                    'source_url': url
                                }
                                events.append(event_data)
                        
                        break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON: {e}")
                        # Try a simpler extraction approach
                        try:
                            # Extract just event names as fallback
                            event_matches = re.findall(r'"name":"([^"]+)"', script_content)
                            for name in event_matches[:10]:  # Limit to first 10
                                events.append({
                                    'date': datetime.now().strftime('%Y-%m-%d'),
                                    'title': name[:50],
                                    'description': name[:100],
                                    'source_url': url
                                })
                        except:
                            pass
                        continue
        
        logger.info(f"Scraped {len(events)} events from ForexFactory (before date filtering)")
        
        # Filter events by date if start_date is specified
        if FOREXFACTORY_START_DATE:
            filtered_events = []
            # Calculate week range (Sunday to Saturday)
            week_start = FOREXFACTORY_START_DATE
            # Find the Sunday of that week
            days_since_sunday = (week_start.weekday() + 1) % 7
            week_start_sunday = week_start - timedelta(days=days_since_sunday)
            week_end = week_start_sunday + timedelta(days=6)  # Saturday
            
            for event in events:
                event_date_str = event.get('date', '')
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    # Check if event is within the week
                    if week_start_sunday <= event_date <= week_end:
                        filtered_events.append(event)
                except (ValueError, TypeError):
                    # If date parsing fails, include the event (better to include than exclude)
                    filtered_events.append(event)
            events = filtered_events
            logger.info(f"After date filtering (week {week_start_sunday.date()} to {week_end.date()}): {len(events)} events")
        
        logger.info(f"Scraped {len(events)} events from ForexFactory")
        return events
        
    except Exception as e:
        logger.error(f"Error scraping ForexFactory: {e}")
        return []


def scrape_tradingeconomics(url: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Scrape TradingEconomics calendar events from the provided URL.
    
    Args:
        url: URL to scrape (None = uses TRADINGECONOMICS_START_DATE config)
        
    Returns:
        List of event dictionaries with date, title, description, etc.
    """
    if url is None:
        url = get_tradingeconomics_url(TRADINGECONOMICS_START_DATE, TRADINGECONOMICS_END_DATE)
    
    logger.info(f"Scraping TradingEconomics: {url}")
    
    try:
        # Try to read from example file first (use absolute path relative to script location)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        example_file = os.path.join(script_dir, "temp", "htmlsources", "tradingeconomics-calendar-inspect.html")
        if not os.path.exists(example_file):
            example_file = os.path.join(script_dir, "temp", "htmlsources", "tradingeconomics-calendar.html")
        
        logger.info(f"Using HTML file: {example_file}")
        if os.path.exists(example_file):
            with open(example_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            logger.info(f"Loaded HTML file, size: {len(html_content)} characters")
        else:
            logger.warning(f"HTML file not found: {example_file}, fetching from URL...")
            # Use realistic browser headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all calendar event rows
        calendar_table = soup.find('table', class_='calendar-table')
        events = []
        
        if not calendar_table:
            # Try alternative search
            calendar_table = soup.find('table', class_=re.compile(r'calendar'))
            if not calendar_table:
                logger.warning("Could not find calendar table in HTML")
                # Debug: list all tables
                all_tables = soup.find_all('table')
                logger.warning(f"Found {len(all_tables)} tables in HTML")
                if all_tables:
                    for i, table in enumerate(all_tables[:5], 1):
                        classes = table.get('class', [])
                        logger.warning(f"  Table {i}: classes={classes}")
                return events
        
        logger.info(f"Found calendar table: {calendar_table is not None}")
        
        if calendar_table:
            # Debug: Check table structure
            logger.info(f"Calendar table found. Checking structure...")
            
            # Get ALL rows from the table (not just from tbody)
            # Use recursive=True to find rows at any depth
            all_table_rows = calendar_table.find_all('tr', recursive=True)
            logger.info(f"Total rows in calendar table (recursive): {len(all_table_rows)}")
            
            # Check tbody separately
            tbody = calendar_table.find('tbody')
            tbody_rows = tbody.find_all('tr', recursive=True) if tbody else []
            logger.info(f"Tbody found: {tbody is not None}, rows in tbody: {len(tbody_rows)}")
            
            # Also check rows directly in table (not in thead/tbody)
            direct_rows = [tr for tr in calendar_table.children if tr.name == 'tr']
            logger.info(f"Rows directly in table (not in thead/tbody): {len(direct_rows)}")
            
            # Find all rows with data-event attribute (search entire table, not just tbody)
            rows = calendar_table.find_all('tr', attrs={'data-event': True}, recursive=True)
            logger.info(f"Found {len(rows)} rows with data-event attribute (recursive search)")
            
            # If still no rows, try searching the entire soup for rows with data-event
            if not rows:
                logger.info("Trying to find rows with data-event in entire document...")
                all_rows_with_data_event = soup.find_all('tr', attrs={'data-event': True})
                logger.info(f"Found {len(all_rows_with_data_event)} rows with data-event in entire document")
                if all_rows_with_data_event:
                    # Check if they're near the calendar table
                    for row in all_rows_with_data_event[:3]:
                        parent_table = row.find_parent('table')
                        if parent_table:
                            parent_classes = parent_table.get('class', [])
                            logger.info(f"  Row's parent table classes: {parent_classes}")
                    rows = all_rows_with_data_event
            
            # Debug: Check first few rows from entire table
            if len(all_table_rows) > 0:
                logger.info(f"First row has 'th' tags: {all_table_rows[0].find('th') is not None}")
                logger.info(f"First row has 'data-event' attr: {'data-event' in all_table_rows[0].attrs}")
                if len(all_table_rows) > 1:
                    logger.info(f"Second row has 'data-event' attr: {'data-event' in all_table_rows[1].attrs}")
                    logger.info(f"Second row classes: {all_table_rows[1].get('class', [])}")
                    # Check if second row has calendar-event
                    event_link = all_table_rows[1].find('a', class_='calendar-event')
                    logger.info(f"Second row has calendar-event link: {event_link is not None}")
                    if event_link:
                        logger.info(f"  Second row event name: {event_link.get_text(strip=True)}")
            
            # Also try finding rows with calendar-event links (more flexible search)
            if not rows:
                logger.info(f"Searching through {len(all_table_rows)} total rows for calendar-event links")
                calendar_event_count = 0
                for row in all_table_rows:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    # Check if row has a calendar-event link
                    event_link = row.find('a', class_='calendar-event')
                    if event_link:
                        rows.append(row)
                        calendar_event_count += 1
                        if calendar_event_count <= 3:
                            logger.info(f"  Found calendar-event link in row: {event_link.get_text(strip=True)}")
                logger.info(f"Found {len(rows)} rows with calendar-event links")
            else:
                # Debug first few rows with data-event
                for i, row in enumerate(rows[:3], 1):
                    event_link = row.find('a', class_='calendar-event')
                    event_name = event_link.get_text(strip=True) if event_link else "N/A"
                    logger.info(f"  Row {i} with data-event: {event_name}")
            
            logger.info(f"Processing {len(rows)} rows...")
            for idx, row in enumerate(rows, 1):
                # Extract event data
                event_name_elem = row.find('a', class_='calendar-event')
                if not event_name_elem:
                    logger.debug(f"Row {idx}: No calendar-event link found")
                    continue
                
                event_name = event_name_elem.get_text(strip=True)
                if not event_name:
                    logger.debug(f"Row {idx}: Empty event name")
                    continue
                
                logger.debug(f"Row {idx}: Found event '{event_name}'")
                    
                event_url = event_name_elem.get('href', '')
                full_url = f"https://tradingeconomics.com{event_url}" if event_url and event_url.startswith('/') else (url if not event_url else event_url)
                
                # Extract date/time - look for td with date class or date in class name
                date_cell = None
                all_tds = row.find_all('td')
                for td in all_tds:
                    td_classes = td.get('class', [])
                    # Check if any class contains a date pattern (handle leading spaces)
                    for cls in td_classes:
                        if cls:
                            cls_str = str(cls).strip()  # Remove leading/trailing spaces
                            if re.search(r'\d{4}-\d{2}-\d{2}', cls_str):
                                date_cell = td
                                break
                    if date_cell:
                        break
                
                time_str = ''
                date_str = datetime.now().strftime('%Y-%m-%d')
                
                if date_cell:
                    time_span = date_cell.find('span', class_=re.compile(r'calendar-date'))
                    if time_span:
                        time_str = time_span.get_text(strip=True)
                    # Extract date from class name - check all classes (handle spaces)
                    for cls in date_cell.get('class', []):
                        if cls:
                            cls_str = str(cls).strip()
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', cls_str)
                            if date_match:
                                date_str = date_match.group(1)
                                break
                
                # Extract country
                country_elem = row.find('td', class_='calendar-iso')
                country = country_elem.get_text(strip=True) if country_elem else ''
                
                # Extract category
                category = row.get('data-category', '')
                
                # Extract reference period
                ref_elem = row.find('span', class_='calendar-reference')
                reference = ref_elem.get_text(strip=True) if ref_elem else ''
                
                # Extract values (actual, forecast, previous) - look for calendar-item cells
                # Based on the HTML structure: actual, previous, consensus, forecast
                value_cells = row.find_all('td', class_=re.compile(r'calendar-item'))
                actual = ''
                forecast = ''
                previous = ''
                
                # Try to find values - look for spans/links with IDs or specific patterns
                actual_elem = row.find('span', id='actual')
                if actual_elem:
                    actual = actual_elem.get_text(strip=True)
                
                previous_elem = row.find('span', id='previous')
                if previous_elem:
                    previous = previous_elem.get_text(strip=True)
                
                forecast_elem = row.find('a', id='forecast')
                if forecast_elem:
                    forecast = forecast_elem.get_text(strip=True)
                
                # Fallback: try to find values in calendar-item cells
                if not actual or not forecast or not previous:
                    for td in all_tds:
                        text = td.get_text(strip=True)
                        td_classes = ' '.join(td.get('class', []))
                        if 'calendar-item' in td_classes and text:
                            # Skip if it's just a link without text
                            if td.find('a') and not text.strip():
                                continue
                            # Try to identify which value this is
                            if not actual and text and '%' in text or any(c.isdigit() for c in text):
                                actual = text
                            elif not forecast and text != actual and ('%' in text or any(c.isdigit() for c in text)):
                                forecast = text
                            elif not previous and text not in [actual, forecast] and ('%' in text or any(c.isdigit() for c in text)):
                                previous = text
                
                event_data = {
                    'date': date_str,
                    'time': time_str,
                    'title': event_name[:50],  # Max 50 chars
                    'description': f"{event_name} - {category}"[:100] if category else event_name[:100],  # Max 100 chars
                    'country': country,
                    'category': category,
                    'reference': reference,
                    'actual': actual,
                    'forecast': forecast,
                    'previous': previous,
                    'source_url': full_url
                }
                events.append(event_data)
        
        logger.info(f"Scraped {len(events)} events from TradingEconomics (before date filtering)")
        
        # Filter events by date range if dates are specified
        if TRADINGECONOMICS_START_DATE or TRADINGECONOMICS_END_DATE:
            filtered_events = []
            for event in events:
                event_date_str = event.get('date', '')
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d')
                    # Check if event is within date range
                    if TRADINGECONOMICS_START_DATE and event_date < TRADINGECONOMICS_START_DATE:
                        continue
                    if TRADINGECONOMICS_END_DATE and event_date > TRADINGECONOMICS_END_DATE:
                        continue
                    filtered_events.append(event)
                except (ValueError, TypeError):
                    # If date parsing fails, include the event (better to include than exclude)
                    filtered_events.append(event)
            events = filtered_events
            logger.info(f"After date filtering ({TRADINGECONOMICS_START_DATE} to {TRADINGECONOMICS_END_DATE}): {len(events)} events")
        
        logger.info(f"Scraped {len(events)} events from TradingEconomics")
        return events
        
    except Exception as e:
        logger.error(f"Error scraping TradingEconomics: {e}")
        return []


def get_historic_events(events_data: List[Dict[str, Any]] = None) -> str:
    """
    Use Anthropic AI to analyze historic events and their impact on crypto prices.
    Uses AI's internal knowledge of historical market events.
    
    Args:
        events_data: List of scraped events (optional, not currently used)
        
    Returns:
        AI-generated analysis as a string
    """
    logger.info("Getting historic events analysis from Anthropic AI")
    
    if not anthropic_client:
        logger.warning("Anthropic client not initialized, returning dummy response")
        return "Anthropic API key not configured. This would analyze historic events and their impact on Bitcoin/XRP prices."
    
    prompt = """You are a master analyst in the crypto space and related financial markets.

Your goal is to analyze historic events and their impact on crypto prices, specifically Bitcoin and XRP.

Using your extensive training data and knowledge of historical market events, provide a comprehensive analysis of significant events from 2020-2025 that caused at least 4% price movements in Bitcoin or XRP.

Focus on:
- Major market-moving announcements or actions (e.g. COVID-19, U.S. elections, FOMC meetings, Jerome Powell speeches, SEC announcements, influential social media posts such as Elon Musk tweeting about Bitcoin)
- Both minor and major events
- Global events, not limited to the U.S.
- Events that caused price changes on the same day as the event
- Include notable isolated cases where relevant (e.g. XRP, LUNC, FTX-related events)

Format your response as a table with the following structure:
<date>: <title> (max 50 chars) - <description> (max 100 chars)

Provide a comprehensive analysis of these historic events and their market impact, including:
- The events themselves
- The price movements they triggered
- Patterns and correlations you identify
- Context about why these events moved markets
"""
    
    try:
        with anthropic_client.messages.stream(
            model=DEFAULT_MODEL,
            max_tokens=32000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        ) as stream:
            response_text = ""
            for text in stream.text_stream:
                response_text += text
        
        logger.info("Successfully received response from Anthropic AI")
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling Anthropic AI: {e}")
        return f"Error calling Anthropic AI: {str(e)}"


def insert_recently_predicted_events(recent_events_data: List[Dict[str, Any]] = None) -> str:
    """
    Use Anthropic AI to analyze recently predicted events and compare them to recent price changes.
    
    Args:
        recent_events_data: List of recent scraped events (optional, can be empty for now)
        
    Returns:
        AI-generated analysis as a string, or empty string if no events provided
    """
    logger.info("Analyzing recently predicted events with Anthropic AI")
    
    if not anthropic_client:
        logger.warning("Anthropic client not initialized, returning empty response")
        return ""
    
    # If no events provided, return empty string
    if not recent_events_data or len(recent_events_data) == 0:
        logger.info("No recent events provided, returning empty analysis")
        return ""
    
    prompt = """You are a master analyst in the crypto space and related financial markets.

Your goal is to analyze recently predicted events and compare them to recent price changes in Bitcoin and XRP.

Important: Find out relations and identify any other reasons why prices have changed which weren't previously mentioned. Provide your analysis of the whole situation.

Given the following recent events, analyze:
1. The relationship between these events and recent price movements
2. Any other factors that may have influenced prices
3. Your overall assessment of the situation

Format your response with:
- Event analysis
- Price correlation
- Additional factors
- Overall assessment

Recent events to analyze:
"""
    
    # Add real events to prompt if provided
    for event in recent_events_data:
        date = event.get('date', 'N/A')
        title = event.get('title', 'N/A')
        description = event.get('description', event.get('title', 'N/A'))
        prompt += f"\n- {date}: {title} - {description}\n"
    
    try:
        with anthropic_client.messages.stream(
            model=DEFAULT_MODEL,
            max_tokens=32000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        ) as stream:
            response_text = ""
            for text in stream.text_stream:
                response_text += text
        
        logger.info("Successfully received response from Anthropic AI for recent events")
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling Anthropic AI: {e}")
        return f"Error calling Anthropic AI: {str(e)}"


def process_events(
    historic_events: str = None,
    predicted_events: str = None,
    new_events: List[Dict[str, Any]] = None,
    transcripts: str = None
) -> str:
    """
    Process and combine historic, predicted, and new events using Anthropic AI.
    
    Args:
        historic_events: Analysis of historic events (string)
        predicted_events: Analysis of predicted events (string) - can be empty
        new_events: List of new scraped events from ForexFactory and TradingEconomics
        transcripts: Optional transcript text from TA analysts (if provided)
        
    Returns:
        Comprehensive AI-generated analysis
    """
    logger.info("Processing all events with Anthropic AI")
    
    if not anthropic_client:
        logger.warning("Anthropic client not initialized, returning dummy response")
        return "Anthropic API key not configured. This would combine all event analyses."
    
    # Use REAL data passed to function, not dummy data
    historic_events_text = historic_events if historic_events else "No historic events analysis provided."
    predicted_events_text = predicted_events if predicted_events else "No predicted events provided."
    
    # Format new events from actual scraped data
    if new_events and len(new_events) > 0:
        new_events_str = "\n".join([
            f"- {e.get('date', 'N/A')}: {e.get('title', 'N/A')} - {e.get('description', 'N/A')} (Source: {e.get('source_url', 'N/A')})"
            for e in new_events
        ])
    else:
        new_events_str = "No new events provided."
    
    # Build prompt with conditional transcript section
    prompt = """You are a master analyst in the crypto space and related financial markets.

Your PRIMARY GOAL is to PREDICT what will happen in the SHORT-TERM based on historical patterns and upcoming events. This is a PREDICTION tool, not a neutral analysis tool.

CRITICAL RULES:
- ONLY use data that is explicitly provided below
- ONLY analyze events from the provided scraped sources or transcripts
- Do NOT generate predictions beyond the dates of provided events
- Do NOT mention analysts or transcripts unless they are explicitly provided
- Do NOT create scenarios unless they are explicitly mentioned in transcripts

PREDICTION PHILOSOPHY:
- Your job is to MAKE CLEAR DIRECTIONAL PREDICTIONS, not to hedge with neutral labels
- When historical patterns show clear direction (e.g., weak China data = dump), make that prediction
- Use conditional predictions: "DUMP IF WEAK", "PUMP IF CUT", "DUMP IF STRONG" when outcomes depend on data
- Default to directional predictions based on historical patterns, NOT to "NEUTRAL" or "VOLATILITY"
- Only use NEUTRAL when historical patterns truly show no clear direction
- Prioritize historical precedents over being conservative
- If historical analysis shows "weak data = dump", predict "DUMP IF WEAK" not "NEUTRAL"
- Magnitude estimates should be based on similar historical events

You will be provided with:
- Historical events and their market impact (from AI's knowledge base)
- Upcoming or scheduled events (from scraped economic calendars: ForexFactory, TradingEconomics)
{transcript_section}

## REQUIRED OUTPUT FORMAT

You MUST structure your response exactly as follows:

# Key Short-Term Points and predictions from transcripts (if any)

{transcript_predictions_section}

## Transcript related Key Short-Term Predictions (timeframe)

{transcript_short_term_section}

## Transcript related scenarios

{transcript_scenarios_section}

# Calendar Updates based on both input events and transcripts

**<MONTH YEAR> - CRITICAL DATES:**

For EACH event from the "New Events" section below, format exactly as:
- <date>: <PREDICTION TYPE> (<magnitude>), <title> - <reasoning based on historical patterns>;

PREDICTION TYPES (PRIORITIZE DIRECTIONAL PREDICTIONS):
- PUMP, DUMP, MAJOR PUMP, MAJOR DUMP, CRITICAL PUMP, CRITICAL DUMP
- Use conditional predictions when outcomes depend on data: "PUMP IF CUT", "DUMP IF WEAK", "DUMP IF STRONG", "PUMP IF WEAK"
- Only use NEUTRAL when historical patterns show NO clear direction
- Use VOLATILITY only when both directions are equally likely based on history
- Use CRITICAL/MAJOR/EXTREME labels for high-impact events based on historical magnitude

MAGNITUDE (based on historical precedents - be specific):
- Format: (3-5%), (4-6%), (5-8%), (±5-10%), etc.
- Base magnitude on similar historical events from the Historical Events Analysis
- If historical shows "3-5% moves", use that range, not "±1-2%"
- Match the magnitude to historical precedents, don't be conservative

REASONING:
- Compare with similar historical events from the Historical Events Analysis
- Make a CLEAR prediction based on historical patterns
- If history shows "weak data = dump", predict "DUMP IF WEAK" not "NEUTRAL"
- Reference specific historical events and their outcomes

Example formats (based on historical patterns):
- 2025-12-18: PUMP IF CUT (4-6%), BOE Rate Decision - Historical: Rate cuts pump crypto 4-6% (2024 pattern);
- 2025-12-18: DUMP IF STRONG (4-8%), US Retail Sales - Historical: Strong retail sales = Fed hawkish = crypto dumps (Dec 2024: -6%);
- 2025-12-15: DUMP IF WEAK (3-5%), China Economic Data - Historical: Weak China data = global slowdown fears = dump (Aug 2015: -15%, Jan 2016: -22%);

# Overall Assessment

# **Final Verdict**

## **MOST LIKELY (probability%):**
[Scenario based on provided events and historical patterns]

## **SECOND LIKELY (probability%):**
[Alternative scenario]

## **OTHER**
[Third scenario if applicable]

---

# **Key Takeaways for Action:**

[Actionable insights based on provided events]

**Risk Management:**

[Risk management advice based on provided events]

---

## Analysis Instructions:

1. Extract ALL events from the "New Events" section below - these are from scraped sources:
   - ForexFactory: weeks start on Sunday
   - TradingEconomics: weeks start on Monday

2. For EACH event in "New Events", you MUST include it in the CRITICAL DATES section

3. For each event, find similar historical events from the "Historical Events Analysis" and use their outcomes as your prediction basis

4. MAKE CLEAR DIRECTIONAL PREDICTIONS:
   - If historical shows "weak data = dump", predict "DUMP IF WEAK (X-Y%)"
   - If historical shows "strong data = dump", predict "DUMP IF STRONG (X-Y%)"
   - If historical shows "rate cut = pump", predict "PUMP IF CUT (X-Y%)"
   - Only use NEUTRAL when historical patterns show no clear direction
   - Match magnitude to historical precedents (if history shows 3-5%, use 3-5%, not 1-2%)

5. Format each event as: <date>: <PREDICTION TYPE> (<magnitude>), <title> - <reasoning with historical reference>;

6. If transcripts are provided, extract predictions and scenarios from them in the transcript sections

7. If NO transcripts provided, write "No transcripts provided." in transcript sections

8. Group events by month in the CRITICAL DATES section (e.g., **DECEMBER 2025 - CRITICAL DATES:**)

9. ONLY include events that are explicitly in the "New Events" section - do NOT invent events

10. For scenarios in Final Verdict, base them ONLY on the provided events and historical patterns

11. REMEMBER: Your goal is to PREDICT short-term outcomes, not to be neutral. Make bold predictions based on historical patterns.

Historical Events Analysis:
{historic_events}

Predicted Events Analysis:
{predicted_events}

New Events (from scraped sources - USE THESE EVENTS ONLY):
{new_events}
{transcript_content}

Now provide the analysis in the exact format specified above. Every event in your CRITICAL DATES section must come from the "New Events" list above.
"""
    
    # Conditionally add transcript section
    if transcripts and transcripts.strip():
        transcript_section = "- Video-based transcripts from TA analysts (if provided)"
        transcript_content = f"\n\nTranscripts Provided:\n{transcripts}"
        transcript_predictions_section = "Extract and list key short-term predictions from the transcripts above."
        transcript_short_term_section = "Extract short-term predictions with timeframes from transcripts."
        transcript_scenarios_section = "Extract and analyze scenarios mentioned in transcripts."
    else:
        transcript_section = ""
        transcript_content = "\n\nNo transcripts provided. Skip all transcript-related sections."
        transcript_predictions_section = "No transcripts provided."
        transcript_short_term_section = "No transcripts provided."
        transcript_scenarios_section = "No transcripts provided."
    
    prompt = prompt.format(
        transcript_section=transcript_section,
        transcript_predictions_section=transcript_predictions_section,
        transcript_short_term_section=transcript_short_term_section,
        transcript_scenarios_section=transcript_scenarios_section,
        historic_events=historic_events_text,
        predicted_events=predicted_events_text,
        new_events=new_events_str,
        transcript_content=transcript_content
    )
    
    # Save the full prompt to a file for confirmation and analysis
    if ANALYSIS_DIR is None:
        raise ValueError("Analysis directory not initialized. Call init_analysis_directory() first.")
    prompt_filepath = os.path.join(ANALYSIS_DIR, "ai_prompt.txt")
    with open(prompt_filepath, 'w', encoding='utf-8') as f:
        f.write("# Full AI Prompt\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"MODEL: {DEFAULT_MODEL}\n")
        f.write("MAX_TOKENS: 32000\n\n")
        f.write("=" * 80 + "\n\n")
        f.write("USER PROMPT:\n\n")
        f.write(prompt)
    logger.info(f"Saved full AI prompt to {prompt_filepath}")
    
    try:
        with anthropic_client.messages.stream(
            model=DEFAULT_MODEL,
            max_tokens=56000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        ) as stream:
            response_text = ""
            for text in stream.text_stream:
                response_text += text
        
        logger.info("Successfully received comprehensive analysis from Anthropic AI")
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling Anthropic AI: {e}")
        return f"Error calling Anthropic AI: {str(e)}"


def perform_web_search(
    prompt: str,
    allowed_domains: Optional[List[str]] = None,
    blocked_domains: Optional[List[str]] = None,
    max_searches: int = 5,
    max_tokens: int = 4000
) -> str:
    """
    Perform a web search using Anthropic or OpenRouter API with optional domain filtering.
    
    Args:
        prompt: The search query/prompt to send to the AI
        allowed_domains: Optional list of domains to whitelist (Anthropic only)
        blocked_domains: Optional list of domains to blacklist (Anthropic only)
        max_searches: Maximum number of web searches the AI can perform (default: 5)
        max_tokens: Maximum tokens in the response (default: 4000)
        
    Returns:
        AI-generated response with web search results, or error message
    """
    logger.info(f"Performing web search with prompt: {prompt[:100]}...")
    
    if not anthropic_client:
        logger.warning("AI client not initialized, cannot perform web search")
        return "AI API key not configured. Cannot perform web search."
    
    try:
        # Determine model and build request parameters based on API type
        if AI_API_TYPE == 'OPENROUTER':
            # OpenRouter: Use direct HTTP request since SDK doesn't support plugins parameter
            model = DEFAULT_MODEL
            
            # Make direct HTTP request to OpenRouter API with web search plugin
            # Try non-streaming first to ensure we get a response, then we can optimize for streaming
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",  # Optional: for OpenRouter analytics
                "X-Title": "Market Oracle Web Search"  # Optional: for OpenRouter analytics
            }
            
            payload = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "plugins": [{"id": "web"}]
            }
            
            # Try non-streaming first to see the actual response format
            logger.info(f"Making OpenRouter web search request to {url} with model {model}")
            response = requests.post(url, headers=headers, json=payload, stream=False)
            response.raise_for_status()
            
            # Parse non-streaming response
            try:
                result = response.json()
                logger.debug(f"OpenRouter response keys: {list(result.keys())}")
                
                # Parse response
                response_text = ""
                if 'choices' in result and len(result['choices']) > 0:
                    choice = result['choices'][0]
                    if 'message' in choice and 'content' in choice['message']:
                        response_text = choice['message']['content']
                    elif 'delta' in choice and 'content' in choice['delta']:
                        # Handle streaming format even in non-streaming request
                        response_text = choice['delta']['content']
                    else:
                        logger.warning(f"Unexpected choice format: {json.dumps(choice)[:500]}")
                else:
                    logger.warning(f"No choices in response. Full response: {json.dumps(result)[:1000]}")
                
                if not response_text:
                    error_msg = result.get('error', {}).get('message', 'Unknown error')
                    logger.error(f"OpenRouter API error: {error_msg}")
                    return f"Error: OpenRouter web search failed - {error_msg}"
                
                logger.info(f"Successfully received web search response from OpenRouter (length: {len(response_text)})")
                return response_text
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse OpenRouter response as JSON: {e}")
                logger.error(f"Response text: {response.text[:500]}")
                return f"Error: Failed to parse OpenRouter response. Status: {response.status_code}"
            except Exception as e:
                logger.error(f"Unexpected error parsing OpenRouter response: {e}")
                return f"Error: {str(e)}"
            
        else:
            # Anthropic: Use regular model and add web_search tool
            model = DEFAULT_MODEL
            
            # Build web search tool configuration
            web_search_tool = {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_searches
            }
            
            # Add domain filters if provided (Anthropic only)
            if allowed_domains:
                web_search_tool["allowed_domains"] = allowed_domains
                logger.info(f"Allowed domains: {allowed_domains}")
            if blocked_domains:
                web_search_tool["blocked_domains"] = blocked_domains
                logger.info(f"Blocked domains: {blocked_domains}")
            
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "tools": [web_search_tool]
            }
            
            # Make API call with web search enabled using Anthropic SDK
            with anthropic_client.messages.stream(**request_params) as stream:
                response_text = ""
                for text in stream.text_stream:
                    response_text += text
            
            logger.info("Successfully received web search response from Anthropic")
            return response_text
        
    except Exception as e:
        logger.error(f"Error performing web search: {e}")
        return f"Error performing web search: {str(e)}"


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Args:
        url: YouTube URL (supports various formats)
        
    Returns:
        Video ID string or None if not found
    """
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Handle different YouTube URL formats
        if parsed.hostname in ['youtube.com', 'www.youtube.com']:
            if parsed.path == '/watch':
                # Standard format: https://www.youtube.com/watch?v=VIDEO_ID
                query_params = parse_qs(parsed.query)
                video_id = query_params.get('v', [None])[0]
                return video_id
            elif parsed.path.startswith('/embed/'):
                # Embed format: https://www.youtube.com/embed/VIDEO_ID
                return parsed.path.split('/embed/')[-1]
            elif parsed.path.startswith('/v/'):
                # Short format: https://www.youtube.com/v/VIDEO_ID
                return parsed.path.split('/v/')[-1]
        elif parsed.hostname in ['youtu.be', 'www.youtu.be']:
            # Short URL format: https://youtu.be/VIDEO_ID
            return parsed.path.lstrip('/')
        
        return None
    except Exception as e:
        logger.error(f"Error extracting video ID from URL {url}: {e}")
        return None


def download_youtube_subtitles(video_id: str, output_dir: str = ".") -> Optional[str]:
    """
    Download YouTube subtitles using yt-dlp.
    
    Args:
        video_id: YouTube video ID
        output_dir: Directory to save subtitle files
        
    Returns:
        Path to the downloaded VTT file, or None if download fails
    """
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    command = [
        'yt-dlp',
        '--write-auto-sub',
        '--skip-download',
        '--sub-lang', 'en',
        '--output', '%(title)s [%(id)s].%(ext)s',
        youtube_url
    ]
    
    try:
        logger.info(f"Downloading subtitles for video {video_id}")
        result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=output_dir)
        logger.info(f"Subtitles downloaded successfully for video {video_id}")
        
        # Find the downloaded VTT file (search recursively in case of nested directories)
        vtt_files = glob.glob(os.path.join(output_dir, f"*{video_id}*.vtt"))
        # Also search in subdirectories
        vtt_files.extend(glob.glob(os.path.join(output_dir, "**", f"*{video_id}*.vtt"), recursive=True))
        if vtt_files:
            # Prefer files directly in output_dir over nested ones
            direct_files = [f for f in vtt_files if os.path.dirname(f) == os.path.abspath(output_dir)]
            if direct_files:
                return direct_files[0]
            return vtt_files[0]
        return None
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error downloading subtitles: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading subtitles: {e}")
        return None


def find_overlap(text1: str, text2: str) -> int:
    """
    Find the length of the overlap between the end of text1 and the beginning of text2.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Length of the overlap (character count)
    """
    # No overlap possible if either string is empty
    if not text1 or not text2:
        return 0
    
    # Get words for easier comparison
    words1 = text1.split()
    words2 = text2.split()
    
    # Try different overlap lengths
    max_check = min(len(words1), len(words2))
    
    for overlap_size in range(max_check, 0, -1):
        if words1[-overlap_size:] == words2[:overlap_size]:
            # Found overlap, return character count
            return len(' '.join(words2[:overlap_size]))
    
    return 0


def extract_vtt_content(vtt_file: str, keep_timestamps: bool = False) -> str:
    """
    Parse VTT file and extract unique text content without duplications.
    Uses line-by-line processing and tracking of full text to avoid duplicates.
    Based on the implementation from youtube-caption/scan.py
    
    Args:
        vtt_file: Path to the VTT file
        keep_timestamps: Whether to preserve timestamps in the output
        
    Returns:
        Clean, non-duplicated text from the subtitles
    """
    try:
        with open(vtt_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        # Skip header (usually first few lines)
        start_index = 0
        for i, line in enumerate(lines):
            if re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', line):
                start_index = i
                break
        
        # Extract text from each subtitle block, ignoring style info
        subtitle_blocks = []
        
        i = start_index
        previous_text = None
        while i < len(lines):
            # If this is a timestamp line, process the timestamp and the text that follows
            if re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', lines[i]):
                # Extract timestamp range to detect very short duplicates
                timestamp_line = lines[i].strip()
                timestamp_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', timestamp_line)
                
                if timestamp_match:
                    start_ts = timestamp_match.group(1)
                    end_ts = timestamp_match.group(2)
                    
                    # Parse timestamps to calculate duration
                    def parse_timestamp(ts):
                        parts = ts.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        seconds_parts = parts[2].split('.')
                        seconds = int(seconds_parts[0])
                        milliseconds = int(seconds_parts[1])
                        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
                    
                    start_time = parse_timestamp(start_ts)
                    end_time = parse_timestamp(end_ts)
                    duration = end_time - start_time
                    
                    # Skip blocks with very short duration (< 0.1 seconds) - these are usually duplicates
                    if duration < 0.1:
                        i += 1
                        # Skip the text lines for this short block
                        while i < len(lines) and not re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', lines[i]) and lines[i].strip():
                            i += 1
                        continue
                
                # Extract only the beginning timestamp (HH:MM:SS.mmm)
                if keep_timestamps:
                    ts_match = re.match(r'(\d{2}:\d{2}:\d{2}\.\d{3})', timestamp_line)
                    timestamp = ts_match.group(1) if ts_match else ""
                else:
                    timestamp = ""
                i += 1
                
                # Collect all text lines until next timestamp or blank line
                text_lines = []
                while i < len(lines) and not re.match(r'\d{2}:\d{2}:\d{2}\.\d{3} -->', lines[i]) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                if text_lines:
                    # Join the text lines and clean them
                    text = ' '.join(text_lines)
                    # Remove all HTML-like tags
                    text = re.sub(r'<[^>]+>', '', text)
                    # Normalize whitespace
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    # Skip if this text is identical to the previous block (duplicate)
                    if text and text != previous_text:
                        subtitle_blocks.append((timestamp, text))
                        previous_text = text
                    elif text and text == previous_text:
                        # Skip exact duplicate
                        pass
                    elif text:
                        # First block
                        subtitle_blocks.append((timestamp, text))
                        previous_text = text
            else:
                i += 1
        
        # Now we have all subtitle blocks with timestamps (if requested)
        # Let's reconstruct unique content
        unique_text = ""
        
        for timestamp, text in subtitle_blocks:
            # Only add text that isn't already in our result
            if text not in unique_text:
                # Check if this text is partly included in our current result
                overlap = find_overlap(unique_text, text)
                if overlap:
                    # Only add the non-overlapping part
                    if keep_timestamps and timestamp and unique_text:
                        unique_text += f"\n{timestamp} {text[overlap:]}"
                    else:
                        # Add space before non-overlapping part if needed
                        if unique_text and not unique_text.endswith(' '):
                            unique_text += " "
                        unique_text += text[overlap:]
                else:
                    # First text or no overlap
                    if unique_text:
                        if keep_timestamps and timestamp:
                            unique_text += f"\n{timestamp} {text}"
                        else:
                            unique_text += " " + text
                    else:
                        if keep_timestamps and timestamp:
                            unique_text = f"{timestamp} {text}"
                        else:
                            unique_text = text
        
        # Final cleanup - normalize whitespace again if not keeping timestamps
        if not keep_timestamps:
            unique_text = re.sub(r'\s+', ' ', unique_text).strip()
        
        return unique_text
        
    except Exception as e:
        logger.error(f"Error extracting content from VTT file {vtt_file}: {e}")
        return ""


def extract_youtube_transcript(video_id: str, temp_dir: str = ".") -> Optional[str]:
    """
    Extract transcript from a YouTube video using yt-dlp.
    
    Args:
        video_id: YouTube video ID
        temp_dir: Temporary directory for downloading subtitle files
        
    Returns:
        Transcript text as string, or None if extraction fails
    """
    try:
        logger.info(f"Extracting transcript for video ID: {video_id}")
        
        # First, check if VTT file already exists (search recursively)
        existing_vtt = None
        vtt_files = glob.glob(os.path.join(temp_dir, f"*{video_id}*.vtt"))
        vtt_files.extend(glob.glob(os.path.join(temp_dir, "**", f"*{video_id}*.vtt"), recursive=True))
        if vtt_files:
            existing_vtt = vtt_files[0]
            logger.info(f"Found existing VTT file: {existing_vtt}")
        
        # Download subtitles if not found
        vtt_file = existing_vtt or download_youtube_subtitles(video_id, temp_dir)
        if not vtt_file:
            logger.error(f"Could not find or download subtitles for video {video_id}")
            return None
        
        # Extract text from VTT file
        transcript_text = extract_vtt_content(vtt_file, keep_timestamps=False)
        
        if not transcript_text:
            logger.error(f"Could not extract text from VTT file: {vtt_file}")
            return None
        
        logger.info(f"Successfully extracted transcript ({len(transcript_text)} characters)")
        return transcript_text
        
    except Exception as e:
        logger.error(f"Error extracting transcript for video {video_id}: {e}")
        return None


def validate_and_extract_youtube_transcripts(urls: List[str], analysis_dir: str) -> Dict[str, Any]:
    """
    Validate and extract transcripts from YouTube URLs, returning success/failure for each.
    
    Args:
        urls: List of YouTube URLs to validate and extract
        analysis_dir: Directory path where transcripts should be saved
        
    Returns:
        Dictionary with:
            - analysis_id: datetime string
            - transcripts: List of dicts with url, success (bool), video_id, error (optional)
    """
    logger.info(f"Validating and extracting transcripts for {len(urls)} URLs")
    
    # Extract datetime ID from directory path
    analysis_id = os.path.basename(analysis_dir)
    
    # Ensure directory exists
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Temporary directory for downloading subtitle files
    temp_dir = analysis_dir
    
    transcript_results = []
    
    for idx, url in enumerate(urls, 1):
        logger.info(f"Processing URL {idx}/{len(urls)}: {url}")
        
        result = {
            'url': url,
            'success': False,
            'video_id': None,
            'error': None
        }
        
        try:
            # Extract video ID
            video_id = extract_video_id(url)
            if not video_id:
                result['error'] = "Could not extract video ID from URL"
                logger.error(f"Could not extract video ID from URL: {url}")
                transcript_results.append(result)
                continue
            
            result['video_id'] = video_id
            
            # Extract transcript
            transcript = extract_youtube_transcript(video_id, temp_dir)
            if not transcript:
                result['error'] = "Could not extract transcript (video may not have subtitles)"
                logger.error(f"Could not extract transcript for video ID: {video_id}")
                transcript_results.append(result)
                continue
            
            # Save transcript to file
            safe_video_id = re.sub(r'[^\w\-_]', '_', video_id)
            filename = f"{safe_video_id}_transcript.txt"
            filepath = os.path.join(analysis_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# YouTube Transcript\n\n")
                f.write(f"Video URL: {url}\n")
                f.write(f"Video ID: {video_id}\n")
                f.write(f"Extracted: {datetime.now().isoformat()}\n\n")
                f.write("=" * 80 + "\n\n")
                f.write(transcript)
            
            logger.info(f"Successfully saved transcript to {filepath}")
            result['success'] = True
            transcript_results.append(result)
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error processing URL {url}: {e}")
            transcript_results.append(result)
    
    successful_count = sum(1 for r in transcript_results if r['success'])
    logger.info(f"Transcript validation completed: {successful_count}/{len(urls)} successful")
    
    return {
        'analysis_id': analysis_id,
        'transcripts': transcript_results
    }


def extract_youtube_transcripts(urls: List[str] = None) -> None:
    """
    Extract transcripts from multiple YouTube URLs and save them to text files.
    
    Args:
        urls: List of YouTube URLs (if None, uses YOUTUBE_URLS from config)
    """
    if urls is None:
        urls = YOUTUBE_URLS
    
    if not urls:
        logger.warning("No YouTube URLs provided. Add URLs to YOUTUBE_URLS list.")
        return
    
    logger.info(f"Starting YouTube transcript extraction for {len(urls)} URLs")
    
    if ANALYSIS_DIR is None:
        raise ValueError("Analysis directory not initialized. Call init_analysis_directory() first.")
    
    # Use analysis directory for transcripts
    transcripts_dir = ANALYSIS_DIR
    os.makedirs(transcripts_dir, exist_ok=True)
    
    # Temporary directory for downloading subtitle files
    temp_dir = transcripts_dir
    
    for idx, url in enumerate(urls, 1):
        logger.info(f"Processing URL {idx}/{len(urls)}: {url}")
        
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            logger.error(f"Could not extract video ID from URL: {url}")
            continue
        
        # Extract transcript
        transcript = extract_youtube_transcript(video_id, temp_dir)
        if not transcript:
            logger.error(f"Could not extract transcript for video ID: {video_id}")
            continue
        
        # Save transcript to file
        # Use video ID as filename (safe for filesystem)
        safe_video_id = re.sub(r'[^\w\-_]', '_', video_id)
        filename = f"{safe_video_id}_transcript.txt"
        filepath = os.path.join(transcripts_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# YouTube Transcript\n\n")
            f.write(f"Video URL: {url}\n")
            f.write(f"Video ID: {video_id}\n")
            f.write(f"Extracted: {datetime.now().isoformat()}\n\n")
            f.write("=" * 80 + "\n\n")
            f.write(transcript)
        
        logger.info(f"Saved transcript to {filepath}")
    
    logger.info(f"Completed YouTube transcript extraction. Transcripts saved to {transcripts_dir}/")


def collect_transcripts(urls: List[str] = None) -> str:
    """
    Collect all transcript files for the given YouTube URLs and combine them.
    
    Args:
        urls: List of YouTube URLs (if None, uses YOUTUBE_URLS from config)
        
    Returns:
        Combined transcript text with source information, or empty string if no transcripts found
    """
    if urls is None:
        urls = YOUTUBE_URLS
    
    if not urls:
        logger.info("No YouTube URLs provided, skipping transcript collection")
        return ""
    
    if ANALYSIS_DIR is None:
        logger.warning("Analysis directory not initialized. Cannot collect transcripts.")
        return ""
    
    transcripts_dir = ANALYSIS_DIR
    if not os.path.exists(transcripts_dir):
        logger.info(f"Analysis directory not found: {transcripts_dir}")
        return ""
    
    combined_transcripts = []
    
    for url in urls:
        # Extract video ID from URL
        video_id = extract_video_id(url)
        if not video_id:
            logger.warning(f"Could not extract video ID from URL: {url}")
            continue
        
        # Find transcript file (safe video ID for filename)
        safe_video_id = re.sub(r'[^\w\-_]', '_', video_id)
        transcript_filename = f"{safe_video_id}_transcript.txt"
        transcript_path = os.path.join(transcripts_dir, transcript_filename)
        
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                # Extract just the transcript text (skip metadata header)
                # Look for the separator line and get content after it
                lines = transcript_content.split('\n')
                transcript_text = ""
                in_transcript = False
                
                for line in lines:
                    if '=' * 80 in line:
                        in_transcript = True
                        continue
                    if in_transcript:
                        transcript_text += line + "\n"
                
                # If no separator found, use everything after the first few metadata lines
                if not transcript_text.strip():
                    # Skip header lines (usually first 7-8 lines)
                    transcript_text = '\n'.join(lines[7:])
                
                if transcript_text.strip():
                    combined_transcripts.append(f"=== Transcript from: {url} (Video ID: {video_id}) ===\n\n{transcript_text.strip()}\n\n")
                    logger.info(f"Added transcript for video {video_id} from {transcript_path}")
                else:
                    logger.warning(f"Transcript file {transcript_path} appears to be empty")
            except Exception as e:
                logger.error(f"Error reading transcript file {transcript_path}: {e}")
        else:
            logger.warning(f"Transcript file not found for video {video_id}: {transcript_path}")
    
    if combined_transcripts:
        result = "\n\n".join(combined_transcripts)
        logger.info(f"Collected {len(combined_transcripts)} transcript(s), total length: {len(result)} characters")
        return result
    else:
        logger.info("No transcript files found")
        return ""


def log_output_to_file(data: Any, filename: str, description: str = ""):
    """
    Log output data to a file in the analysis directory.
    
    Args:
        data: Data to log (can be string, dict, list, etc.)
        filename: Output filename
        description: Optional description to add to the log
    """
    if ANALYSIS_DIR is None:
        raise ValueError("Analysis directory not initialized. Call init_analysis_directory() first.")
    
    filepath = os.path.join(ANALYSIS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if description:
            f.write(f"# {description}\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("=" * 80 + "\n\n")
        
        if isinstance(data, (dict, list)):
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            f.write(str(data))
    
    logger.info(f"Logged output to {filepath}")




def test_all():
    """
    Test all functions and log outputs.
    """
    logger.info("Starting Crypto Analysis Bot - Full Test Suite")
    
    # Initialize analysis directory at the start
    init_analysis_directory()
    
    # Test 1: Scrape ForexFactory
    logger.info("=" * 80)
    logger.info("TEST 1: Scraping ForexFactory")
    logger.info("=" * 80)
    ff_events = scrape_forexfactory()
    log_output_to_file(
        ff_events,
        "forexfactory_events.json",
        "ForexFactory Scraped Events"
    )
    logger.info(f"Scraped {len(ff_events)} events from ForexFactory")
    if ff_events:
        logger.info(f"Sample event: {ff_events[0]}")
    
    # Test 2: Scrape TradingEconomics
    logger.info("=" * 80)
    logger.info("TEST 2: Scraping TradingEconomics")
    logger.info("=" * 80)
    te_events = scrape_tradingeconomics()
    log_output_to_file(
        te_events,
        "tradingeconomics_events.json",
        "TradingEconomics Scraped Events"
    )
    logger.info(f"Scraped {len(te_events)} events from TradingEconomics")
    if te_events:
        logger.info(f"Sample event: {te_events[0]}")
    
    # Test 3: Get Historic Events Analysis
    logger.info("=" * 80)
    logger.info("TEST 3: Analyzing Historic Events with Anthropic AI")
    logger.info("=" * 80)
    historic_analysis = get_historic_events()
    log_output_to_file(
        historic_analysis,
        "historic_events_analysis.txt",
        "Historic Events Analysis (Anthropic AI)"
    )
    logger.info("Historic events analysis completed")
    logger.info(f"Analysis preview: {historic_analysis[:200]}...")
    
    # Test 4: Insert Recently Predicted Events
    logger.info("=" * 80)
    logger.info("TEST 4: Analyzing Recently Predicted Events with Anthropic AI")
    logger.info("=" * 80)
    recent_analysis = insert_recently_predicted_events()
    log_output_to_file(
        recent_analysis,
        "recent_events_analysis.txt",
        "Recently Predicted Events Analysis (Anthropic AI)"
    )
    logger.info("Recent events analysis completed")
    logger.info(f"Analysis preview: {recent_analysis[:200]}...")
    
    # Test 5: Extract and Collect YouTube Transcripts
    logger.info("=" * 80)
    logger.info("TEST 5: Extracting YouTube Transcripts")
    logger.info("=" * 80)
    extract_youtube_transcripts()
    
    logger.info("=" * 80)
    logger.info("TEST 5 (continued): Collecting YouTube Transcripts")
    logger.info("=" * 80)
    transcripts = collect_transcripts()
    if transcripts:
        logger.info(f"Collected transcripts ({len(transcripts)} characters)")
        logger.info(f"Transcript preview: {transcripts[:200]}...")
    else:
        logger.info("No transcripts found or collected")
    
    # Test 6: Process All Events (including transcripts)
    logger.info("=" * 80)
    logger.info("TEST 6: Processing All Events with Anthropic AI (including transcripts)")
    logger.info("=" * 80)
    comprehensive_analysis = process_events(
        historic_events=historic_analysis,
        predicted_events=recent_analysis,
        new_events=ff_events + te_events,
        transcripts=transcripts
    )
    log_output_to_file(
        comprehensive_analysis,
        "comprehensive_analysis.txt",
        "Full Comprehensive Events Analysis"
    )
    logger.info("Comprehensive analysis completed")
    logger.info(f"Analysis preview: {comprehensive_analysis[:200]}...")
    
    logger.info("=" * 80)
    logger.info(f"All tests completed! Check the {ANALYSIS_DIR} directory for output files.")
    logger.info("=" * 80)


def test_tradingeconomics():
    """
    Test function for TradingEconomics scraping (for isolated testing).
    """
    logger.info("=" * 80)
    logger.info("TESTING TRADINGECONOMICS SCRAPER")
    logger.info("=" * 80)
    
    # Test TradingEconomics scraping with detailed debugging
    te_events = scrape_tradingeconomics()
    
    log_output_to_file(
        te_events,
        "tradingeconomics_events.json",
        "TradingEconomics Scraped Events"
    )
    
    logger.info("=" * 80)
    logger.info(f"RESULT: Scraped {len(te_events)} events from TradingEconomics")
    logger.info("=" * 80)
    
    if te_events:
        logger.info("SUCCESS! Sample events:")
        for i, event in enumerate(te_events[:5], 1):
            logger.info(f"  Event {i}: {event}")
    else:
        logger.error("FAILED: No events found. Check the HTML structure and scraper logic.")
    
    logger.info("=" * 80)
    return te_events


def run_analysis_with_config(config: Dict[str, Any], analysis_id: str) -> Dict[str, Any]:
    """
    Run the full analysis with configuration from a dictionary.
    
    Note: ANTHROPIC_API_KEY must be configured in .env file (never in config dict for security).
    
    Args:
        config: Dictionary containing (all optional):
            - forexfactory_start_date: Optional date string (YYYY-MM-DD) or None
            - forexfactory_use_week: Optional boolean (default: True)
            - tradingeconomics_start_date: Optional date string (YYYY-MM-DD) or None
            - tradingeconomics_end_date: Optional date string (YYYY-MM-DD) or None
        analysis_id: Datetime ID of the analysis directory (created by /validate endpoint)
    
    Returns:
        Dictionary with analysis results and directory path
    """
    global FOREXFACTORY_START_DATE, FOREXFACTORY_USE_WEEK
    global TRADINGECONOMICS_START_DATE, TRADINGECONOMICS_END_DATE
    global anthropic_client, ANTHROPIC_API_KEY, OPENROUTER_API_KEY
    
    # Store original values
    original_ff_start = FOREXFACTORY_START_DATE
    original_ff_week = FOREXFACTORY_USE_WEEK
    original_te_start = TRADINGECONOMICS_START_DATE
    original_te_end = TRADINGECONOMICS_END_DATE
    # Store API key based on current API type (for restoration later)
    original_api_key = OPENROUTER_API_KEY if AI_API_TYPE == 'OPENROUTER' else ANTHROPIC_API_KEY
    original_client = anthropic_client
    
    try:
        # Override global config with provided values
        if 'forexfactory_start_date' in config:
            FOREXFACTORY_START_DATE = parse_date(config.get('forexfactory_start_date'))
        if 'forexfactory_use_week' in config:
            FOREXFACTORY_USE_WEEK = parse_bool(str(config.get('forexfactory_use_week', True)))
        if 'tradingeconomics_start_date' in config:
            TRADINGECONOMICS_START_DATE = parse_date(config.get('tradingeconomics_start_date'))
        if 'tradingeconomics_end_date' in config:
            TRADINGECONOMICS_END_DATE = parse_date(config.get('tradingeconomics_end_date'))
        # API key is always from .env (never from request body for security)
        # The anthropic_client is already initialized from .env at startup
        
        # Use existing analysis directory (created by /validate endpoint)
        analysis_dir = os.path.join("analysis", analysis_id)
        
        # Check if analysis directory exists
        if not os.path.exists(analysis_dir):
            raise ValueError(f"Analysis directory not found: {analysis_dir}. Run /validate endpoint first.")
        
        # Set global ANALYSIS_DIR so other functions can use it
        global ANALYSIS_DIR
        ANALYSIS_DIR = analysis_dir
        
        # Run the analysis
        logger.info("Starting analysis with provided configuration")
        
        # Scrape ForexFactory
        ff_events = scrape_forexfactory()
        log_output_to_file(ff_events, "forexfactory_events.json", "ForexFactory Scraped Events")
        
        # Scrape TradingEconomics
        te_events = scrape_tradingeconomics()
        log_output_to_file(te_events, "tradingeconomics_events.json", "TradingEconomics Scraped Events")
        
        # Get historic events analysis
        historic_analysis = get_historic_events()
        log_output_to_file(historic_analysis, "historic_events_analysis.txt", "Historic Events Analysis")
        
        # Get recent events analysis
        recent_analysis = insert_recently_predicted_events(te_events + ff_events)
        log_output_to_file(recent_analysis, "recent_events_analysis.txt", "Recent Events Analysis")
        
        # Collect YouTube transcripts from existing directory (extracted by /validate endpoint)
        # Find all transcript files in the analysis directory
        transcript_files = glob.glob(os.path.join(analysis_dir, "*_transcript.txt"))
        transcripts = ""
        if transcript_files:
            # Collect transcripts from files
            combined_transcripts = []
            for transcript_path in transcript_files:
                try:
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        transcript_content = f.read()
                    
                    # Extract just the transcript text (skip metadata header)
                    lines = transcript_content.split('\n')
                    transcript_text = ""
                    in_transcript = False
                    
                    for line in lines:
                        if '=' * 80 in line:
                            in_transcript = True
                            continue
                        if in_transcript:
                            transcript_text += line + "\n"
                    
                    # If no separator found, use everything after the first few metadata lines
                    if not transcript_text.strip():
                        transcript_text = '\n'.join(lines[7:])
                    
                    if transcript_text.strip():
                        # Extract URL from metadata
                        url = "N/A"
                        for line in lines[:7]:
                            if line.startswith("Video URL:"):
                                url = line.replace("Video URL:", "").strip()
                                break
                        
                        combined_transcripts.append(f"=== Transcript from: {url} ===\n\n{transcript_text.strip()}\n\n")
                        logger.info(f"Added transcript from {transcript_path}")
                except Exception as e:
                    logger.error(f"Error reading transcript file {transcript_path}: {e}")
            
            if combined_transcripts:
                transcripts = "\n\n".join(combined_transcripts)
                logger.info(f"Collected {len(combined_transcripts)} transcript(s) from existing directory")
        else:
            logger.info("No transcript files found in analysis directory")
        
        # Process all events
        comprehensive_analysis = process_events(
            historic_events=historic_analysis,
            predicted_events=recent_analysis,
            new_events=ff_events + te_events,
            transcripts=transcripts
        )
        log_output_to_file(comprehensive_analysis, "comprehensive_analysis.txt", "Comprehensive Analysis")
        
        # Collect warnings/errors
        warnings = []
        errors = []
        
        if len(ff_events) == 0:
            warnings.append("No ForexFactory events found. This may be due to date filtering or scraping issues.")
        if len(te_events) == 0:
            warnings.append("No TradingEconomics events found. This may be due to date filtering or scraping issues.")
        if "Error calling Anthropic AI" in historic_analysis:
            errors.append("Historic events analysis failed - check Anthropic API key")
        if "Error calling Anthropic AI" in recent_analysis:
            errors.append("Recent events analysis failed - check Anthropic API key")
        if "Error calling Anthropic AI" in comprehensive_analysis:
            errors.append("Comprehensive analysis failed - check Anthropic API key")
        
        # Extract datetime ID from analysis directory (format: analysis/YYYYMMDD_HHMMSS)
        datetime_id = os.path.basename(analysis_dir) if analysis_dir else None
        
        response = {
            'status': 'success' if not errors else 'partial_success',
            'analysis_id': datetime_id,
            'message': f'Analysis completed. Use /process endpoint with analysis_id: {datetime_id} to generate CSV data.'
        }
        
        if warnings:
            response['warnings'] = warnings
        if errors:
            response['errors'] = errors
        
        return response
        
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'message': 'Analysis failed'
        }
    finally:
        # Restore original values
        FOREXFACTORY_START_DATE = original_ff_start
        FOREXFACTORY_USE_WEEK = original_ff_week
        TRADINGECONOMICS_START_DATE = original_te_start
        TRADINGECONOMICS_END_DATE = original_te_end
        # Restore API key based on current API type
        if AI_API_TYPE == 'OPENROUTER':
            OPENROUTER_API_KEY = original_api_key
        else:
            ANTHROPIC_API_KEY = original_api_key
        anthropic_client = original_client


def generate_csv_from_analysis(comprehensive_analysis: str) -> str:
    """
    Generate CSV data from comprehensive analysis using Anthropic AI.
    
    Args:
        comprehensive_analysis: Full comprehensive analysis text
        
    Returns:
        CSV data as string
    """
    logger.info("Generating CSV from comprehensive analysis")
    
    # Route to correct AI provider based on AI_API_TYPE
    if AI_API_TYPE == 'OPENROUTER':
        if not anthropic_client or not hasattr(anthropic_client, 'messages'):
            logger.error("OpenRouter client not initialized")
            raise RuntimeError('OpenRouter client not initialized')
        call_client = anthropic_client
    else:
        # Default to Anthropic
        if not anthropic_client:
            logger.warning("Anthropic client not initialized, cannot generate CSV")
            raise RuntimeError('Anthropic client not initialized')
        call_client = anthropic_client
    
    CSV_GENERATION_PROMPT = '''
# Task
You are an extractor: given a comprehensive market analysis text, produce a single CSV containing every event, prediction, price level, and date in the analysis.

# IMPORTANT: MUST RETURN ONLY A SINGLE CODE BLOCK (```txt) CONTAINING THE CSV. DO NOT OUTPUT ANY EXPLANATION, MARKDOWN, OR ADDITIONAL TEXT.

# REQUIRED CSV HEADER (MUST MATCH EXACTLY - case-sensitive, comma-separated):
Token,Date,Event_Type,Forecast,Timeframe,Title,Description,Event_Category,Price_Level,Price_Type,Pattern,Content_Source,Confidence_Level

# FIELD DEFINITIONS (use EXACT values/formats):
- Token: Cryptocurrency name (e.g., Bitcoin, Ethereum) or "General" for market-wide events.
- Date: YYYY-MM-DD or "N/A" if no specific date.
- Event_Type: one of EXACTLY: Listed, Mentioned, Predicted.
- Forecast: Prediction type from Calendar Updates section - one of: NEUTRAL, DUMP, PUMP, VOLATILITY, MAJOR DUMP, MAJOR PUMP, CRITICAL DUMP, CRITICAL PUMP, DUMP IF WEAK, DUMP IF STRONG, PUMP IF CUT, PUMP IF WEAK, MAJOR VOLATILITY, CRITICAL VOLATILITY, or "N/A" if not found or unclear.
- Timeframe: Past, Present, Future or "N/A".
- Title: Event title/name (e.g., "BusinessNZ Services Index (NZ)", "China Economic Data Cluster", "Federal Reserve FOMC") or "N/A" if not available.
- Description: short description without commas (use semicolons instead) and without newlines.
- Event_Category: category like Price Movement, Regulatory, Economic Data, Market Pattern, Support Level, Resistance Level, Astronomical, etc. Use "N/A" if unsure.
- Price_Level: price with $ prefix (e.g., $50000) or "N/A".
- Price_Type: Support, Resistance, Target, Current, Peak, Bottom, Breakout, or "N/A".
- Pattern: chart pattern name or "N/A".
- Content_Source: ForexFactory, TradingEconomics, YouTube Transcript, Multiple, or Analysis.
- Confidence_Level: High, Medium, Low, a percentage (e.g., 75%), or "N/A".

# FORECAST EXTRACTION RULES (CRITICAL):
1) For events in "# Calendar Updates based on both input events and transcripts" section:
   - Extract Forecast directly from the format: "Date: FORECAST (magnitude), Title - Description"
   - Examples: "NEUTRAL", "DUMP IF WEAK", "MAJOR VOLATILITY", "CRITICAL DUMP IF HAWKISH", "PUMP IF CUT"
   - Include the full forecast text including conditions (e.g., "DUMP IF WEAK", not just "DUMP")
   
2) For events from other sections (transcripts, scenarios, etc.):
   - If a clear directional prediction exists (e.g., "expects dump", "anticipates pump", "volatility expected"), extract it
   - If unclear or no prediction, use "N/A"
   - Look for keywords: "dump", "pump", "volatility", "neutral", "bearish", "bullish", "crash", "rally"
   
3) Title extraction:
   - For Calendar Updates section: Extract the event name after the forecast and before the dash (e.g., "BusinessNZ Services Index (NZ)", "China Economic Data Cluster")
   - For other sections: Extract the event name or use a descriptive title based on context
   - If no clear title exists, use "N/A"

# FORMATTING RULES (YOU MUST OBEY ALL OF THESE):
1) The first line must be the exact header shown above and only that header.
2) Every subsequent line is a data row; every row must contain exactly 13 comma-separated values (12 commas).
3) NEVER include commas within field values — replace commas with semicolons if needed.
4) Use "N/A" for missing or inapplicable fields; never leave an empty field.
5) Dates must use YYYY-MM-DD format when available.
6) Price values must include the $ symbol when applicable.
7) Do not include any extra commentary, footers, or metadata — only the code block with CSV.

# CLASSIFICATION RULES:
- Listed: events taken directly from economic calendars (ForexFactory, TradingEconomics).
- Mentioned: events/dates referenced in transcripts or discussion but not calendar listings.
- Predicted: AI-generated forecasts, price targets, or scenarios.

# EXTRA GUIDANCE:
- Extract events from all sections of the analysis. If multiple sources contribute to the same event, set Content_Source to "Multiple".
- If a single event mentions multiple price levels, produce separate rows for each price level (each row must still follow the header format).
- Prioritize extracting Forecast from Calendar Updates section when available.

# FEW-SHOT EXAMPLES (exact CSV rows; follow these styles):
Token,Date,Event_Type,Forecast,Timeframe,Title,Description,Event_Category,Price_Level,Price_Type,Pattern,Content_Source,Confidence_Level
General,2025-12-14,Listed,NEUTRAL,Future,BusinessNZ Services Index (NZ),Minor regional data; limited crypto impact,Economic Data,N/A,N/A,N/A,ForexFactory,N/A
General,2025-12-15,Listed,DUMP IF WEAK,Future,China Economic Data Cluster,Weak China data triggers global slowdown fears and crypto selloffs,Economic Data,N/A,N/A,N/A,Multiple,Medium
Bitcoin,2025-12-19,Predicted,MAJOR VOLATILITY,Future,BOJ Policy Rate Decision,BOJ hawkish surprise = severe yen carry trade unwind = crypto crash,Regulatory,N/A,N/A,N/A,Analysis,High

# FINAL CHECK: Before returning, ensure header matches exactly and every row has 13 values (12 commas). Return only the CSV inside a single ```txt code block.
'''
    
    try:
        with call_client.messages.stream(
            model=DEFAULT_MODEL,
            max_tokens=56000,
            temperature=0.1,
            system=CSV_GENERATION_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Extract all events, dates, prices, and predictions from the following comprehensive analysis and convert to CSV format:\n\n{comprehensive_analysis}"
                }
            ]
        ) as stream:
            csv_content = ""
            for text in stream.text_stream:
                csv_content += text
        
        # Extract CSV content from response (look for ```.txt or ``` markers)
        # Handle various formats: ```.txt, ```txt, ```csv, or just ```
        original_content = csv_content
        
        # Try to find and extract from code blocks
        if "```.txt" in csv_content:
            start = csv_content.find("```.txt") + 7
            end = csv_content.find("```", start)
            if end == -1:
                end = len(csv_content)
            csv_content = csv_content[start:end].strip()
        elif "```txt" in csv_content:
            start = csv_content.find("```txt") + 6
            end = csv_content.find("```", start)
            if end == -1:
                end = len(csv_content)
            csv_content = csv_content[start:end].strip()
        elif "```csv" in csv_content:
            start = csv_content.find("```csv") + 6
            end = csv_content.find("```", start)
            if end == -1:
                end = len(csv_content)
            csv_content = csv_content[start:end].strip()
        elif "```" in csv_content:
            # Fallback: extract between any ``` markers
            parts = csv_content.split("```")
            if len(parts) >= 2:
                csv_content = parts[1].strip()
                # Remove language identifier if present (.txt, txt, csv, etc.)
                if csv_content.startswith(".txt") or csv_content.startswith("txt"):
                    csv_content = csv_content[4:].strip()
                elif csv_content.startswith("csv"):
                    csv_content = csv_content[3:].strip()
        
        # Additional cleanup: remove "txt" if it's the first line
        lines = csv_content.split('\n')
        if len(lines) > 0 and lines[0].strip().lower() == 'txt':
            csv_content = '\n'.join(lines[1:])
        
        # Final validation: ensure we have a header row
        if not csv_content or not csv_content.strip():
            logger.error(f"Failed to extract CSV content. Original response: {original_content[:500]}")
            raise Exception("Failed to extract CSV content from AI response")
        
        # Log first few lines for debugging
        first_lines = '\n'.join(csv_content.split('\n')[:3])
        logger.info(f"Extracted CSV preview (first 3 lines):\n{first_lines}")
        
        logger.info("Successfully generated CSV from comprehensive analysis")
        return csv_content
        
    except Exception as e:
        logger.error(f"Error generating CSV from analysis: {e}")
        raise


def main():
    """
    Main function - runs the full test suite including transcript collection and analysis.
    For other functionality, use:
    - extract_youtube_transcripts() - extract YouTube transcripts only
    - test_tradingeconomics() - test only TradingEconomics scraper
    - test_all() - test all functions (same as main)
    """
    test_all()


# ============================================================================
# FLASK API
# ============================================================================

app = Flask(__name__)
# Enable CORS for all routes - permissive for development
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])


@app.route('/', methods=['GET'])
def root():
    """
    Root endpoint showing current app status.
    """
    return jsonify({
        'status': 'running',
        'app': 'Crypto Analysis Market Oracle API',
        'version': '1.0.0',
        'endpoints': {
            '/': 'GET - App status (this endpoint)',
            '/validate': 'POST - Validate and extract YouTube transcripts (returns analysis_id)',
            '/analyze': 'POST - Run analysis with JSON configuration (requires analysis_id from /validate)',
            '/process': 'POST - Process analysis and generate CSV (requires analysis_id)',
            '/poly/event': 'GET - Get complete event data with all markets (?url=...)',
            '/poly/event/slug/<slug>': 'GET - Get event data by slug',
            '/poly/event/markets/list': 'GET - Get reduced list of markets for an event (?url=... or ?slug=...)',
            '/poly/market/<id>': 'GET - Get detailed market data by market ID',
            '/poly/probabilities': 'GET - Get outcome probabilities (?url=...&market_slug=...)'
        },
        'config_note': 'API keys must be configured in .env file (never in requests)',
        'workflow': {
            'step_1': 'POST /validate - Validate and extract YouTube transcripts (returns analysis_id)',
            'step_2': 'POST /analyze - Run analysis with economic calendar data (requires analysis_id from step 1)',
            'step_3': 'POST /process - Generate CSV data from analysis (requires analysis_id)'
        },
        'api_key_configured': bool(
            (AI_API_TYPE == 'OPENROUTER' and OPENROUTER_API_KEY and anthropic_client) or
            (AI_API_TYPE != 'OPENROUTER' and ANTHROPIC_API_KEY and anthropic_client)
        ),
        'api_type': AI_API_TYPE
    })


@app.route('/validate', methods=['POST'])
def validate():
    """
    Validate and extract YouTube transcripts endpoint.
    
    This is the FIRST endpoint to call. It validates YouTube URLs, extracts transcripts,
    creates an analysis directory, and returns validation results.
    
    Expected JSON body:
    {
        "youtube_urls": ["https://youtube.com/watch?v=..."]  // required - list or comma-separated string
    }
    
    Returns:
    {
        "status": "success",
        "analysis_id": "20251220_152704",
        "transcripts": [
            {
                "url": "https://youtube.com/watch?v=...",
                "success": true,
                "video_id": "bgV5FnP8gpA",
                "error": null
            },
            {
                "url": "https://youtube.com/watch?v=...",
                "success": false,
                "video_id": "INVALID_ID",
                "error": "Could not extract transcript (video may not have subtitles)"
            }
        ]
    }
    """
    try:
        # Get JSON body
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        youtube_urls = data.get('youtube_urls') if data else None
        
        if not youtube_urls:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: youtube_urls'
            }), 400
        
        # Parse YouTube URLs (handle both list and comma-separated string)
        if isinstance(youtube_urls, str):
            urls = parse_youtube_urls(youtube_urls)
        elif isinstance(youtube_urls, list):
            urls = youtube_urls
        else:
            return jsonify({
                'status': 'error',
                'error': 'youtube_urls must be a list or comma-separated string'
            }), 400
        
        if not urls:
            return jsonify({
                'status': 'error',
                'error': 'No valid YouTube URLs provided'
            }), 400
        
        # Create analysis directory
        analysis_dir = init_analysis_directory()
        
        # Validate and extract transcripts
        result = validate_and_extract_youtube_transcripts(urls, analysis_dir)
        
        # Count successful vs failed
        successful = sum(1 for t in result['transcripts'] if t['success'])
        failed = len(result['transcripts']) - successful
        
        response = {
            'status': 'success',
            'analysis_id': result['analysis_id'],
            'transcripts': result['transcripts'],
            'summary': {
                'total': len(result['transcripts']),
                'successful': successful,
                'failed': failed
            },
            'message': f'Validation completed. {successful}/{len(result["transcripts"])} transcripts extracted successfully. Use analysis_id in /analyze endpoint.'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in /validate endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Run analysis endpoint that accepts JSON body with configuration.
    
    Note: ANTHROPIC_API_KEY must be configured in .env file (never in request body for security).
    Note: You must call /validate endpoint first to create the analysis directory and extract transcripts.
    
    Expected JSON body:
    {
        "analysis_id": "20251220_152704",  // required - from /validate endpoint response
        "forexfactory_start_date": "2025-12-14",  // optional
        "forexfactory_use_week": true,  // optional, default: true
        "tradingeconomics_start_date": "2025-12-15",  // optional
        "tradingeconomics_end_date": "2025-12-21"  // optional
    }
    """
    try:
        # Get JSON body
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        config = request.get_json()
        analysis_id = config.get('analysis_id') if config else None
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id. Call /validate endpoint first.'
            }), 400
        
        # Validate that API key exists in .env (security: never accept API keys in requests)
        # Check based on AI_API_TYPE
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        
        # Remove anthropic_api_key from config if provided (security: ignore it)
        if config and 'anthropic_api_key' in config:
            logger.warning("anthropic_api_key provided in request body - ignoring (using .env value for security)")
            config = {k: v for k, v in config.items() if k != 'anthropic_api_key'}
        
        # Remove analysis_id from config dict (it's a separate parameter)
        analysis_id_param = config.pop('analysis_id', None)
        if not analysis_id_param:
            analysis_id_param = analysis_id
        
        # Run analysis with provided config and analysis_id (API key from .env will be used)
        result = run_analysis_with_config(config, analysis_id_param)
        
        if result['status'] == 'error':
            return jsonify(result), 500
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in /analyze endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/process', methods=['POST'])
def process():
    """
    Process analysis endpoint that takes an analysis_id and generates CSV data.
    
    Expected JSON body:
    {
        "analysis_id": "20251220_152704"  // required - datetime ID from /analyze endpoint
    }
    
    Returns:
    {
        "status": "success",
        "analysis_directory": "analysis\\20251220_152704",
        "csv_data": "...",
        "comprehensive_analysis": "...",
        "forexfactory_events_count": 130,
        "tradingeconomics_events_count": 65,
        "youtube_transcripts_count": 7,
        "message": "Processing completed successfully"
    }
    """
    try:
        # Get JSON body
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        analysis_id = data.get('analysis_id') if data else None
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id'
            }), 400
        
        # Validate that API key exists in .env
        # Check based on AI_API_TYPE
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        
        # Construct analysis directory path
        analysis_dir = os.path.join("analysis", analysis_id)
        
        # Check if analysis directory exists
        if not os.path.exists(analysis_dir):
            return jsonify({
                'status': 'error',
                'error': f'Analysis directory not found: {analysis_dir}. Invalid or missing analysis_id.'
            }), 404
        
        # Check if comprehensive_analysis.txt exists
        comprehensive_analysis_path = os.path.join(analysis_dir, "comprehensive_analysis.txt")
        if not os.path.exists(comprehensive_analysis_path):
            return jsonify({
                'status': 'error',
                'error': f'Comprehensive analysis file not found in {analysis_dir}. Analysis may be incomplete or corrupted.'
            }), 404
        
        # Read comprehensive analysis
        logger.info(f"Reading comprehensive analysis from {comprehensive_analysis_path}")
        with open(comprehensive_analysis_path, 'r', encoding='utf-8') as f:
            comprehensive_analysis = f.read()
        
        if not comprehensive_analysis.strip():
            return jsonify({
                'status': 'error',
                'error': 'Comprehensive analysis file is empty. Cannot generate CSV data.'
            }), 400
        
        # Generate CSV data
        logger.info(f"Generating CSV data for analysis_id: {analysis_id}")
        csv_data = generate_csv_from_analysis(comprehensive_analysis)
        
        # Write CSV data to file for debugging
        csv_output_path = os.path.join(analysis_dir, "output.csv")
        try:
            with open(csv_output_path, 'w', encoding='utf-8') as f:
                f.write(csv_data)
            logger.info(f"CSV data written to {csv_output_path}")
            logger.info(f"CSV data length: {len(csv_data)} characters")
            logger.info(f"CSV data preview (first 500 chars): {csv_data[:500]}")
        except Exception as e:
            logger.warning(f"Failed to write CSV to file: {e}")
        
        # Read event counts from JSON files if they exist
        forexfactory_count = 0
        tradingeconomics_count = 0
        youtube_count = 0
        
        ff_events_path = os.path.join(analysis_dir, "forexfactory_events.json")
        if os.path.exists(ff_events_path):
            try:
                with open(ff_events_path, 'r', encoding='utf-8') as f:
                    ff_events = json.load(f)
                    forexfactory_count = len(ff_events) if isinstance(ff_events, list) else 0
            except:
                pass
        
        te_events_path = os.path.join(analysis_dir, "tradingeconomics_events.json")
        if os.path.exists(te_events_path):
            try:
                with open(te_events_path, 'r', encoding='utf-8') as f:
                    te_events = json.load(f)
                    tradingeconomics_count = len(te_events) if isinstance(te_events, list) else 0
            except:
                pass
        
        # Count YouTube transcript files
        transcript_files = glob.glob(os.path.join(analysis_dir, "*_transcript.txt"))
        youtube_count = len(transcript_files)
        
        # Log response details for debugging
        logger.info(f"Process response details:")
        logger.info(f"  - CSV data length: {len(csv_data)} characters")
        logger.info(f"  - CSV line count: {len(csv_data.split(chr(10)))} lines")
        logger.info(f"  - ForexFabric events: {forexfactory_count}")
        logger.info(f"  - TradingEconomics events: {tradingeconomics_count}")
        logger.info(f"  - YouTube transcripts: {youtube_count}")
        
        # Return response
        response = {
            'status': 'success',
            'analysis_directory': analysis_dir,
            'csv_data': csv_data,
            'comprehensive_analysis': comprehensive_analysis,
            'forexfactory_events_count': forexfactory_count,
            'tradingeconomics_events_count': tradingeconomics_count,
            'youtube_transcripts_count': youtube_count,
            'message': 'Processing completed successfully'
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in /process endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/websearch', methods=['POST'])
def websearch():
    """
    Web search endpoint that accepts a prompt and optional domain filters.
    
    Expected JSON body:
    {
        "prompt": "What are the latest Bitcoin price predictions?",  // required
        "allowed_domains": ["coindesk.com", "bloomberg.com"],  // optional - Anthropic only
        "blocked_domains": ["spam-site.com"],  // optional - Anthropic only
        "max_searches": 5,  // optional, default: 5
        "max_tokens": 4000  // optional, default: 4000
    }
    
    Returns:
    {
        "status": "success",
        "response": "...",
        "prompt": "...",
        "api_type": "ANTHROPIC" | "OPENROUTER"
    }
    """
    try:
        # Get JSON body
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        prompt = data.get('prompt') if data else None
        
        if not prompt:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: prompt'
            }), 400
        
        # Validate that API key exists in .env
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        
        # Extract optional parameters
        allowed_domains = data.get('allowed_domains')
        blocked_domains = data.get('blocked_domains')
        max_searches = data.get('max_searches', 5)
        max_tokens = data.get('max_tokens', 4000)
        
        # Warn if domain filters are provided with OpenRouter (not supported)
        if AI_API_TYPE == 'OPENROUTER' and (allowed_domains or blocked_domains):
            logger.warning("Domain filtering is not supported with OpenRouter API. Filters will be ignored.")
        
        # Perform web search
        response_text = perform_web_search(
            prompt=prompt,
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
            max_searches=max_searches,
            max_tokens=max_tokens
        )
        
        # Check if there was an error
        if response_text.startswith("Error") or response_text.startswith("AI API key not configured"):
            return jsonify({
                'status': 'error',
                'error': response_text
            }), 500
        
        return jsonify({
            'status': 'success',
            'response': response_text,
            'prompt': prompt,
            'api_type': AI_API_TYPE,
            'max_searches': max_searches,
            'max_tokens': max_tokens,
            'allowed_domains': allowed_domains if AI_API_TYPE != 'OPENROUTER' else None,
            'blocked_domains': blocked_domains if AI_API_TYPE != 'OPENROUTER' else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /websearch endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/ask-ai', methods=['POST'])
def ask_ai():
    """
    Ask AI endpoint that accepts a question about a specific event and uses web search to provide current information.
    
    Expected JSON body:
    {
        "question": "What is the current status of this event?",  // required
        "event": {  // required - event data from the table row
            "Token": "Bitcoin",
            "Date": "2025-12-25",
            "Event_Type": "Listed",
            "Title": "Fed Interest Rate Decision",
            "Description": "...",
            // ... other event fields
        },
        "analysis_id": "20251220_212438",  // optional - if provided, includes comprehensive analysis
        "max_searches": 5,  // optional, default: 5
        "max_tokens": 4000  // optional, default: 4000
    }
    
    Returns:
    {
        "status": "success",
        "response": "...",
        "question": "...",
        "event": {...}
    }
    """
    try:
        # Get JSON body
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        question = data.get('question') if data else None
        event = data.get('event') if data else None
        analysis_id = data.get('analysis_id') if data else None
        
        if not question:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: question'
            }), 400
        
        if not event:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: event'
            }), 400
        
        # Validate that API key exists in .env
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured in .env file. API keys must be set at the server level, not in requests.'
                }), 500
        
        # Extract optional parameters
        max_searches = data.get('max_searches', 5)
        max_tokens = data.get('max_tokens', 4000)
        
        # Load comprehensive analysis if analysis_id is provided
        comprehensive_analysis = None
        if analysis_id:
            analysis_dir = os.path.join("analysis", analysis_id)
            comprehensive_analysis_path = os.path.join(analysis_dir, "comprehensive_analysis.txt")
            if os.path.exists(comprehensive_analysis_path):
                try:
                    with open(comprehensive_analysis_path, 'r', encoding='utf-8') as f:
                        comprehensive_analysis = f.read()
                    logger.info(f"Loaded comprehensive analysis from {comprehensive_analysis_path} (length: {len(comprehensive_analysis)})")
                except Exception as e:
                    logger.warning(f"Failed to load comprehensive analysis: {e}")
            else:
                logger.warning(f"Comprehensive analysis file not found: {comprehensive_analysis_path}")
        
        # Build event context string
        event_context = f"""Event Details:
- Token: {event.get('Token', 'N/A')}
- Date: {event.get('Date', 'N/A')}
- Event Type: {event.get('Event_Type', 'N/A')}
- Title: {event.get('Title', event.get('Event_Description', 'N/A'))}
- Description: {event.get('Description', event.get('Event_Description', 'N/A'))}
- Category: {event.get('Event_Category', 'N/A')}
- Price Level: {event.get('Price_Level', 'N/A')}
- Price Type: {event.get('Price_Type', 'N/A')}
- Timeframe: {event.get('Timeframe', 'N/A')}
- Forecast: {event.get('Forecast', 'N/A')}
- Source: {event.get('Content_Source', 'N/A')}
- Confidence: {event.get('Confidence_Level', 'N/A')}"""
        
        # Build the prompt with comprehensive analysis, event context, and question
        prompt_parts = [
            "You are a financial market analyst assistant. A user is asking about a specific event from their market analysis.",
            "",
            "=== ORIGINAL ANALYSIS ===",
        ]
        
        if comprehensive_analysis:
            prompt_parts.append("Below is the comprehensive analysis that was generated for this dataset. Use this as your knowledge base to understand the context, patterns, and predictions that were identified:")
            prompt_parts.append("")
            prompt_parts.append(comprehensive_analysis)
            prompt_parts.append("")
        else:
            prompt_parts.append("(No original comprehensive analysis available for this dataset.)")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "=== SPECIFIC EVENT ===",
            "The user is asking about this specific event from the analysis:",
            "",
            event_context,
            "",
            "=== USER'S QUESTION ===",
            question,
            "",
            "=== INSTRUCTIONS ===",
            "Please provide a helpful, accurate answer about this event. You have access to:",
            "1. The original comprehensive analysis (above) - use this as your knowledge base",
            "2. The specific event details - the event the user is asking about",
            "3. Web search capabilities - use web search to find the most current information",
            "",
            "Your response should:",
            "- Reference relevant information from the original analysis when applicable",
            "- Use web search to find current status, updates, and recent developments",
            "- Provide market impact analysis and expectations",
            "- Include relevant context from reliable financial news sources",
            "- Synthesize information from both the original analysis and current web sources",
            "",
            "Focus on providing actionable, up-to-date information that helps the user understand the current state and implications of this event."
        ])
        
        prompt = "\n".join(prompt_parts)
        
        # Perform web search with the combined prompt
        response_text = perform_web_search(
            prompt=prompt,
            allowed_domains=None,  # Allow all domains for general questions
            blocked_domains=None,
            max_searches=max_searches,
            max_tokens=max_tokens
        )
        
        # Check if there was an error
        if response_text.startswith("Error") or response_text.startswith("AI API key not configured"):
            return jsonify({
                'status': 'error',
                'error': response_text
            }), 500
        
        return jsonify({
            'status': 'success',
            'response': response_text,
            'question': question,
            'event': event,
            'api_type': AI_API_TYPE
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /ask-ai endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


# ============================================================================
# POLYMARKET API ENDPOINTS
# ============================================================================

@app.route('/poly/probabilities', methods=['GET'])
def poly_probabilities():
    """
    Get outcome probabilities from a Polymarket URL.
    
    Query Parameters:
        url: Polymarket market/event URL (required)
        
    Returns:
        {
            "status": "success",
            "url": "...",
            "slug": "...",
            "probabilities": {
                "Yes": 0.27,
                "No": 0.73
            }
        }
    """
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: url'
            }), 400
        
        try:
            event_slug = poly.extract_event_slug_from_url(url)
            logger.info(f"Extracted event slug: {event_slug} from URL: {url}")
        except ValueError as e:
            logger.error(f"Failed to extract event slug: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': f'Invalid Polymarket URL: {str(e)}'
            }), 400
        
        # Get probabilities for the first market in the event (or specific market if provided)
        market_slug = request.args.get('market_slug')  # Optional: specific market
        probabilities = poly.get_outcome_probabilities(url, market_slug=market_slug)
        if probabilities is None:
            return jsonify({
                'status': 'error',
                'error': 'Failed to fetch outcome probabilities. Check the URL and try again.'
            }), 500
        
        return jsonify({
            'status': 'success',
            'url': url,
            'event_slug': event_slug,
            'market_slug': market_slug or 'first',
            'probabilities': probabilities
        }), 200
        
    except ValueError as e:
        logger.error(f"ValueError in /poly/probabilities: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in /poly/probabilities endpoint: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/poly/event', methods=['GET'])
def poly_event():
    """
    Get complete event data including all markets from a Polymarket event URL.
    
    Query Parameters:
        url: Polymarket event URL (required)
        
    Returns:
        Complete event data with all markets and their outcome probabilities
    """
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: url'
            }), 400
        
        event_data = poly.get_event_data(url)
        if event_data is None:
            return jsonify({
                'status': 'error',
                'error': 'Failed to fetch event data. Check the URL and try again.'
            }), 500
        
        event_slug = poly.extract_event_slug_from_url(url)
        
        return jsonify({
            'status': 'success',
            'url': url,
            'event_slug': event_slug,
            'event': event_data
        }), 200
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in /poly/event endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500




@app.route('/poly/event/slug/<slug>', methods=['GET'])
def poly_event_by_slug(slug):
    """
    Get event data by slug.
    
    URL Parameters:
        slug: Event slug
        
    Returns:
        Event data
    """
    try:
        event_data = poly.get_event_by_slug(slug)
        
        if event_data is None:
            return jsonify({
                'status': 'error',
                'error': f'Failed to fetch event data for slug: {slug}'
            }), 404
        
        return jsonify({
            'status': 'success',
            'slug': slug,
            'event': event_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /poly/event/slug endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500




@app.route('/poly/event/markets/list', methods=['GET'])
def poly_event_markets_list():
    """
    Get reduced list of markets for an event with only essential data.
    
    Query Parameters:
        url: Polymarket event URL (optional if slug provided)
        slug: Event slug (optional if url provided)
        
    Returns:
        List of markets with id and essential details (outcomes, outcomePrices, volume, active, closed)
    """
    try:
        url = request.args.get('url')
        slug = request.args.get('slug')
        
        if not url and not slug:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: url or slug'
            }), 400
        
        # Get event slug
        if url:
            try:
                event_slug = poly.extract_event_slug_from_url(url)
            except ValueError as e:
                return jsonify({
                    'status': 'error',
                    'error': f'Invalid Polymarket URL: {str(e)}'
                }), 400
        else:
            event_slug = slug
        
        # Get event data
        event_data = poly.get_event_by_slug(event_slug)
        if event_data is None:
            return jsonify({
                'status': 'error',
                'error': f'Failed to fetch event data for slug: {event_slug}'
            }), 404
        
        # Extract and reduce markets data
        markets_raw = event_data.get("markets", [])
        markets_list = []
        
        for market in markets_raw:
            markets_list.append({
                "id": market.get("id"),
                "details": {
                    "outcomes": market.get("outcomes"),
                    "outcomePrices": market.get("outcomePrices"),
                    "volume": market.get("volume"),
                    "active": market.get("active"),
                    "closed": market.get("closed")
                }
            })
        
        return jsonify({
            'status': 'success',
            'event_slug': event_slug,
            'markets_count': len(markets_list),
            'markets': markets_list
        }), 200
        
    except ValueError as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error in /poly/event/markets/list endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/poly/market/<market_id>', methods=['GET'])
def poly_market_by_id(market_id):
    """
    Get detailed market data by market ID.
    
    URL Parameters:
        market_id: Market ID (e.g., "949335")
        
    Returns:
        Complete market data with parsed outcome probabilities
    """
    try:
        market_data = poly.get_market_by_id(market_id)
        
        if market_data is None:
            return jsonify({
                'status': 'error',
                'error': f'Failed to fetch market data for ID: {market_id}'
            }), 404
        
        # Parse outcome probabilities
        import json as json_module
        outcomes = market_data.get("outcomes")
        outcome_prices = market_data.get("outcomePrices")
        
        # Handle JSON strings
        if isinstance(outcomes, str):
            try:
                outcomes = json_module.loads(outcomes)
            except json_module.JSONDecodeError:
                outcomes = []
        
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json_module.loads(outcome_prices)
            except json_module.JSONDecodeError:
                outcome_prices = []
        
        # Create outcome probabilities dictionary
        outcome_probabilities = {}
        if outcomes and outcome_prices and len(outcomes) == len(outcome_prices):
            for outcome, price_str in zip(outcomes, outcome_prices):
                try:
                    price = float(price_str) if isinstance(price_str, str) else float(price_str)
                    outcome_probabilities[outcome] = price
                except (ValueError, TypeError):
                    continue
        
        market_data['outcomeProbabilities'] = outcome_probabilities
        
        return jsonify({
            'status': 'success',
            'market_id': market_id,
            'market': market_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /poly/market/<id> endpoint: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/poly/debug/event', methods=['GET'])
def poly_debug_event():
    """
    Debug endpoint to see raw API response structure.
    
    Query Parameters:
        url: Polymarket market URL (required)
        
    Returns:
        Raw API response for debugging
    """
    try:
        url = request.args.get('url')
        if not url:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: url'
            }), 400
        
        try:
            event_slug = poly.extract_event_slug_from_url(url)
        except ValueError as e:
            return jsonify({
                'status': 'error',
                'error': f'Invalid Polymarket URL: {str(e)}'
            }), 400
        
        # Make direct API call to see raw response
        api_base = os.getenv('POLYMARKET_API_BASE_URL', 'https://gamma-api.polymarket.com')
        api_url = f"{api_base}/events/slug/{event_slug}"
        logger.info(f"Debug: Calling API URL: {api_url}")
        
        headers = {}
        api_key = os.getenv('POLYMARKET_API_KEY', '')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        response_json = None
        if response.status_code == 200:
            try:
                response_json = response.json()
            except:
                pass
        
        return jsonify({
            'status': 'debug',
            'request_url': api_url,
            'response_status': response.status_code,
            'response_headers': dict(response.headers),
            'response_text': response.text[:5000],
            'response_json': response_json,
            'extracted_event_slug': event_slug,
            'note': 'This shows the raw API response. Check response_json to see the actual structure.'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /poly/debug/event endpoint: {e}")
        import traceback
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500




if __name__ == "__main__":
    # Check if running as Flask app or as script
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        # Run as Flask API
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        # Run as script (original behavior)
        main()

