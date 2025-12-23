"""
TradingEconomics scraper - Scrapes economic calendar events from TradingEconomics
"""

import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

from config import TRADINGECONOMICS_START_DATE, TRADINGECONOMICS_END_DATE

logger = logging.getLogger(__name__)


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
        script_dir = os.path.dirname(script_dir)  # Go up one level from scrapers/
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
                
                # Calculate resolve_time: combine date + time
                resolve_time = 'N/A'
                if date_str and time_str:
                    resolve_time = f"{date_str} {time_str}"
                elif date_str:
                    resolve_time = date_str
                
                event_data = {
                    'date': date_str,
                    'time': time_str,
                    'resolve_time': resolve_time,
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

