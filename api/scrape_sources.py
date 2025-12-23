"""
Test file to inspect source websites and verify timestamp availability.
NO BeautifulSoup, NO endpoints - just raw HTML inspection.
"""

import requests
import json
from datetime import datetime

def fetch_forexfactory_html():
    """Fetch raw HTML from ForexFactory calendar to inspect timestamp structure."""
    url = "https://www.forexfactory.com/calendar?week=dec14.2025"
    
    # Check for cached HTML file first (same as scraper does)
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cached_file = os.path.join(script_dir, "temp", "htmlsources", "forexfactory-calendar.html")
    
    print("=" * 80)
    print("FOREXFACTORY HTML INSPECTION")
    print("=" * 80)
    print(f"URL: {url}\n")
    
    html = None
    
    # Try cached file first
    if os.path.exists(cached_file):
        print(f"[OK] Using cached HTML file: {cached_file}\n")
        try:
            with open(cached_file, 'r', encoding='utf-8') as f:
                html = f.read()
        except Exception as e:
            print(f"[WARNING] Failed to read cached file: {e}")
    
    # If no cached file, try to fetch
    if html is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        try:
            print("[INFO] Fetching from URL...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"[ERROR] Failed to fetch from URL: {e}")
            return
    
    try:
        
        # Look for script tags with calendar data
        if 'days:' in html:
            print("[OK] Found 'days:' in HTML - calendar data is present")
            
            # Extract a sample of the days data
            import re
            match = re.search(r'days:\s*(\[.*?\])\s*,', html, re.DOTALL)
            if match:
                days_json = match.group(1)
                # Clean up for JSON parsing
                days_json = days_json.replace('\\/', '/')
                days_json = days_json.replace('\\"', '"')
                days_json = re.sub(r',(\s*[}\]])', r'\1', days_json)
                
                try:
                    days_data = json.loads(days_json)
                    if days_data and len(days_data) > 0:
                        first_day = days_data[0]
                        print(f"\nFirst day structure:")
                        print(f"  - date: {first_day.get('date', 'N/A')}")
                        print(f"  - dateline: {first_day.get('dateline', 'N/A')}")
                        
                        if first_day.get('dateline'):
                            dt = datetime.fromtimestamp(first_day.get('dateline'))
                            print(f"  - dateline (parsed): {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if first_day.get('events') and len(first_day.get('events', [])) > 0:
                            first_event = first_day.get('events')[0]
                            print(f"\nFirst event structure:")
                            print(f"  - name: {first_event.get('name', 'N/A')}")
                            print(f"  - timeLabel: {first_event.get('timeLabel', 'N/A')}")
                            print(f"  - dateline: {first_event.get('dateline', 'N/A')}")
                            
                            # Check for other time-related fields
                            print(f"\nAll event keys: {list(first_event.keys())}")
                            
                            # Look for timestamp fields
                            for key in first_event.keys():
                                if 'time' in key.lower() or 'date' in key.lower() or 'stamp' in key.lower():
                                    print(f"  - {key}: {first_event.get(key)}")
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Failed to parse JSON: {e}")
                    print(f"Sample: {days_json[:500]}")
        else:
            print("[ERROR] 'days:' not found in HTML")
        
        # Save HTML to file for manual inspection
        with open('forexfactory_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n[OK] Saved raw HTML to 'forexfactory_raw.html' for manual inspection")
        
    except Exception as e:
        print(f"[ERROR] Error fetching ForexFactory: {e}")


def fetch_tradingeconomics_html():
    """Fetch raw HTML from TradingEconomics calendar to inspect timestamp structure."""
    url = "https://tradingeconomics.com/calendar"
    
    # Check for cached HTML file first (same as scraper does)
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cached_file = os.path.join(script_dir, "temp", "htmlsources", "tradingeconomics-calendar.html")
    cached_file_inspect = os.path.join(script_dir, "temp", "htmlsources", "tradingeconomics-calendar-inspect.html")
    
    print("\n" + "=" * 80)
    print("TRADINGECONOMICS HTML INSPECTION")
    print("=" * 80)
    print(f"URL: {url}\n")
    
    html = None
    
    # Try cached files first
    for cached in [cached_file_inspect, cached_file]:
        if os.path.exists(cached):
            print(f"[OK] Using cached HTML file: {cached}\n")
            try:
                with open(cached, 'r', encoding='utf-8') as f:
                    html = f.read()
                    break
            except Exception as e:
                print(f"[WARNING] Failed to read cached file: {e}")
    
    # If no cached file, try to fetch
    if html is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        try:
            print("[INFO] Fetching from URL...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"[ERROR] Failed to fetch from URL: {e}")
            return
    
    try:
        
        # Look for calendar table
        if 'calendar-table' in html or 'calendar' in html.lower():
            print("[OK] Found calendar-related content in HTML")
            
            # Look for time-related patterns
            import re
            
            # Look for time patterns like "12:30 AM", "01:01 AM"
            time_patterns = re.findall(r'\d{1,2}:\d{2}\s*(?:AM|PM)', html, re.IGNORECASE)
            if time_patterns:
                print(f"\n[OK] Found {len(time_patterns)} time patterns in HTML:")
                print(f"  Sample times: {time_patterns[:10]}")
            
            # Look for data-event attributes
            data_events = re.findall(r'data-event="[^"]*"', html)
            if data_events:
                print(f"\n[OK] Found {len(data_events)} data-event attributes")
            
            # Look for date/time in class names
            date_classes = re.findall(r'class="[^"]*\d{4}-\d{2}-\d{2}[^"]*"', html)
            if date_classes:
                print(f"\n[OK] Found {len(date_classes)} date classes in HTML")
                print(f"  Sample: {date_classes[0][:100]}")
        
        # Save HTML to file for manual inspection
        with open('tradingeconomics_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n[OK] Saved raw HTML to 'tradingeconomics_raw.html' for manual inspection")
        
    except Exception as e:
        print(f"[ERROR] Error fetching TradingEconomics: {e}")


if __name__ == "__main__":
    print("Testing source websites for timestamp availability...\n")
    fetch_forexfactory_html()
    fetch_tradingeconomics_html()
    print("\n" + "=" * 80)
    print("INSPECTION COMPLETE")
    print("=" * 80)
    print("\nCheck the saved HTML files for detailed structure inspection.")

