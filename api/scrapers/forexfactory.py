"""
ForexFactory scraper - Scrapes economic calendar events from ForexFactory
"""

import os
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from config import FOREXFACTORY_START_DATE, FOREXFACTORY_USE_WEEK

logger = logging.getLogger(__name__)


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
        script_dir = os.path.dirname(script_dir)  # Go up one level from scrapers/
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

