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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from urllib.parse import urlparse, parse_qs

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

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
anthropic_client = None
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
        # For now, read from example file
        # In production, use: response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        example_file = "htmlsources/forexfactory-calendar.html"
        
        if os.path.exists(example_file):
            with open(example_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
        else:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
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
        # For now, read from example file
        # In production, use: response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        # Try inspect file first (has loaded data), then regular file
        example_file = "htmlsources/tradingeconomics-calendar-inspect.html"
        if not os.path.exists(example_file):
            example_file = "htmlsources/tradingeconomics-calendar.html"
        
        logger.info(f"Using HTML file: {example_file}")
        if os.path.exists(example_file):
            with open(example_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            logger.info(f"Loaded HTML file, size: {len(html_content)} characters")
        else:
            logger.warning(f"HTML file not found: {example_file}, fetching from URL...")
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
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
            model="claude-sonnet-4-5-20250929",
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
            model="claude-sonnet-4-5-20250929",
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
        f.write("MODEL: claude-sonnet-4-5-20250929\n")
        f.write("MAX_TOKENS: 32000\n\n")
        f.write("=" * 80 + "\n\n")
        f.write("USER PROMPT:\n\n")
        f.write(prompt)
    logger.info(f"Saved full AI prompt to {prompt_filepath}")
    
    try:
        with anthropic_client.messages.stream(
            model="claude-sonnet-4-5-20250929",
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


def main():
    """
    Main function - runs the full test suite including transcript collection and analysis.
    For other functionality, use:
    - extract_youtube_transcripts() - extract YouTube transcripts only
    - test_tradingeconomics() - test only TradingEconomics scraper
    - test_all() - test all functions (same as main)
    """
    test_all()


if __name__ == "__main__":
    main()

