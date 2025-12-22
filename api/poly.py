"""
Polymarket API Client
Fetches market data and outcome probabilities from Polymarket's Gamma API
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Polymarket API Configuration
POLYMARKET_API_BASE_URL = os.getenv('POLYMARKET_API_BASE_URL', 'https://gamma-api.polymarket.com')
# Support both POLY_API_* (preferred) and POLYMARKET_API_* (legacy) variable names
POLYMARKET_API_KEY = os.getenv('POLY_API_KEY') or os.getenv('POLYMARKET_API_KEY', '')
POLYMARKET_API_SECRET = os.getenv('POLY_API_SECRET') or os.getenv('POLYMARKET_API_SECRET', '')
POLYMARKET_API_PASSPHRASE = os.getenv('POLY_API_PASSPHRASE') or os.getenv('POLYMARKET_API_PASSPHRASE', '')


def extract_event_slug_from_url(polymarket_url: str) -> str:
    """
    Extract the event slug from a Polymarket URL.
    
    Args:
        polymarket_url: Full Polymarket URL (e.g., https://polymarket.com/event/event-slug/market-slug)
        
    Returns:
        The event slug (first part after /event/)
        
    Raises:
        ValueError: If the URL doesn't contain a valid event slug
    """
    try:
        parsed = urlparse(polymarket_url)
        path = parsed.path.strip("/")
        parts = path.split("/")
        
        # Handle /event/{event_slug}/{market_slug} format - we want the event slug
        if parts[0] == 'event' and len(parts) >= 2:
            return parts[1]  # Return the event slug (second part)
        # Handle /event/{event_slug} format
        elif parts[0] == 'event' and len(parts) == 2:
            return parts[1]
        # Handle /market/{market_slug} format - can't extract event slug from this
        elif parts[0] == 'market':
            raise ValueError(f"URL contains a market slug, not an event slug. Use event URL format: /event/event-slug")
        else:
            raise ValueError(f"URL does not contain a valid Polymarket event slug: {polymarket_url}")
    except Exception as e:
        raise ValueError(f"Failed to parse Polymarket URL: {polymarket_url}. Error: {str(e)}")


def extract_slug_from_url(polymarket_url: str) -> str:
    """
    Extract the event slug from a Polymarket URL (backward compatibility).
    """
    return extract_event_slug_from_url(polymarket_url)


def get_market_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """
    Fetch market data by slug from Polymarket's Gamma API.
    
    Args:
        slug: Market slug (extracted from URL or provided directly)
        
    Returns:
        Dictionary containing market data, or None if request fails
    """
    # Try /getMarkets endpoint with slug query parameter first (as per docs)
    url1 = f"{POLYMARKET_API_BASE_URL}/getMarkets"
    params = {"slug": slug}
    
    headers = {}
    if POLYMARKET_API_KEY:
        headers['Authorization'] = f'Bearer {POLYMARKET_API_KEY}'
    
    try:
        logger.info(f"Fetching market data for slug: {slug}")
        logger.info(f"Trying endpoint: {url1} with params: {params}")
        response = requests.get(url1, headers=headers, params=params, timeout=10)
        logger.info(f"Response status: {response.status_code}")
        
        # If first endpoint fails, try alternative
        if response.status_code != 200:
            logger.warning(f"getMarkets endpoint returned {response.status_code}, trying /markets/slug/...")
            url2 = f"{POLYMARKET_API_BASE_URL}/markets/slug/{slug}"
            logger.info(f"Trying alternative endpoint: {url2}")
            response = requests.get(url2, headers=headers, timeout=10)
            logger.info(f"Alternative response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API returned status {response.status_code}: {response.text[:500]}")
            return None
            
        data = response.json()
        logger.info(f"Successfully fetched market data for slug: {slug}")
        logger.debug(f"Response type: {type(data)}")
        logger.debug(f"Market data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Handle response that might be wrapped in a 'markets' array
        if isinstance(data, dict) and 'markets' in data:
            markets = data['markets']
            if markets and len(markets) > 0:
                logger.info(f"Found {len(markets)} market(s) in response, using first one")
                return markets[0]
            else:
                logger.warning("Markets array is empty")
                return None
        elif isinstance(data, list) and len(data) > 0:
            logger.info(f"Response is array with {len(data)} item(s), using first one")
            return data[0]
        
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch market data for slug {slug}: {str(e)}")
        logger.error(f"Request exception type: {type(e).__name__}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching market data for slug {slug}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        return None


def get_event_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """
    Fetch event data by slug from Polymarket's Gamma API.
    
    Args:
        slug: Event slug (extracted from URL or provided directly)
        
    Returns:
        Dictionary containing event data, or None if request fails
    """
    url = f"{POLYMARKET_API_BASE_URL}/events/slug/{slug}"
    
    headers = {}
    if POLYMARKET_API_KEY:
        headers['Authorization'] = f'Bearer {POLYMARKET_API_KEY}'
    
    try:
        logger.info(f"Fetching event data for slug: {slug}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched event data for slug: {slug}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch event data for slug {slug}: {str(e)}")
        return None


def get_market_by_id(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch market data by ID from Polymarket's Gamma API.
    
    Args:
        market_id: Market ID (e.g., "949335")
        
    Returns:
        Dictionary containing market data, or None if request fails
    """
    url = f"{POLYMARKET_API_BASE_URL}/markets/{market_id}"
    
    headers = {}
    if POLYMARKET_API_KEY:
        headers['Authorization'] = f'Bearer {POLYMARKET_API_KEY}'
    
    try:
        logger.info(f"Fetching market data for ID: {market_id}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched market data for ID: {market_id}")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch market data for ID {market_id}: {str(e)}")
        return None


def get_outcome_probabilities(polymarket_url: str, market_slug: Optional[str] = None) -> Optional[Dict[str, float]]:
    """
    Extract outcome probabilities from a Polymarket event URL.
    If market_slug is provided, returns probabilities for that specific market.
    Otherwise, returns probabilities for the first market in the event.
    
    Args:
        polymarket_url: Full Polymarket event URL (e.g., https://polymarket.com/event/event-slug)
        market_slug: Optional market slug to get probabilities for a specific market
        
    Returns:
        Dictionary mapping outcome names to probabilities (0.0-1.0), or None if request fails
    """
    try:
        event_slug = extract_event_slug_from_url(polymarket_url)
        logger.info(f"Extracted event slug: {event_slug} from URL: {polymarket_url}")
        
        # Get event data which contains all markets
        event_data = get_event_by_slug(event_slug)
        
        if not event_data:
            logger.error(f"get_event_by_slug returned None for slug: {event_slug}")
            return None
        
        # Get markets from event
        markets = event_data.get("markets", [])
        if not markets:
            logger.error(f"No markets found in event data for slug: {event_slug}")
            return None
        
        # Find the specific market if market_slug provided, otherwise use first
        market_data = None
        if market_slug:
            for market in markets:
                if market.get("slug") == market_slug:
                    market_data = market
                    break
            if not market_data:
                logger.warning(f"Market with slug '{market_slug}' not found in event. Available markets: {[m.get('slug') for m in markets]}")
                return None
        else:
            market_data = markets[0]
            logger.info(f"Using first market: {market_data.get('slug')}")
        
        if not market_data:
            logger.error(f"No market data found")
            return None
        
        logger.info(f"Market data type: {type(market_data)}")
        logger.info(f"Market data keys: {list(market_data.keys()) if isinstance(market_data, dict) else 'Not a dict'}")
        
        # Check various possible field names for outcomes and prices
        # The API might return outcomes as an array of objects with 'name' and 'probability' fields
        outcomes = market_data.get("outcomes")
        outcome_prices = market_data.get("outcomePrices") or market_data.get("outcome_prices") or market_data.get("prices")
        
        # If outcomes is an array of objects, extract names and probabilities
        if isinstance(outcomes, list) and len(outcomes) > 0 and isinstance(outcomes[0], dict):
            logger.info("Outcomes is an array of objects, extracting names and probabilities")
            outcome_names = []
            outcome_probs = []
            for outcome in outcomes:
                name = outcome.get("name") or outcome.get("outcome") or outcome.get("title")
                prob = outcome.get("probability") or outcome.get("price")
                if name:
                    outcome_names.append(name)
                    if prob is not None:
                        outcome_probs.append(float(prob))
                    else:
                        outcome_probs.append(None)
            if outcome_names:
                outcomes = outcome_names
                if outcome_probs and all(p is not None for p in outcome_probs):
                    outcome_prices = outcome_probs
                logger.info(f"Extracted {len(outcome_names)} outcomes: {outcome_names}")
        
        # Handle outcomes and outcomePrices as JSON strings (they come as strings from API)
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
                logger.info(f"Parsed outcomes from JSON string: {outcomes}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse outcomes JSON string: {outcomes}. Error: {e}")
                return None
        
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
                logger.info(f"Parsed outcomePrices from JSON string: {outcome_prices}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse outcomePrices JSON string: {outcome_prices}. Error: {e}")
                return None
        
        logger.info(f"Outcomes found: {outcomes}")
        logger.info(f"Outcome prices found: {outcome_prices}")
        
        if not outcomes:
            logger.warning(f"No outcomes found in market data. Available keys: {list(market_data.keys()) if isinstance(market_data, dict) else 'N/A'}")
            return None
        
        if not outcome_prices:
            logger.warning(f"No outcome prices found in market data. Available keys: {list(market_data.keys()) if isinstance(market_data, dict) else 'N/A'}")
            return None
        
        if len(outcomes) != len(outcome_prices):
            logger.warning(f"Mismatch between outcomes ({len(outcomes)}) and prices ({len(outcome_prices)})")
            return None
        
        # Convert prices to floats and create dictionary
        result = {}
        for outcome, price_str in zip(outcomes, outcome_prices):
            try:
                price = float(price_str) if isinstance(price_str, str) else float(price_str)
                result[outcome] = price
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to convert price '{price_str}' to float: {str(e)}")
                continue
        
        if not result:
            logger.error(f"Failed to parse any outcome probabilities from data")
            return None
            
        logger.info(f"Successfully parsed {len(result)} outcome probabilities")
        return result
    except ValueError as e:
        logger.error(f"ValueError in get_outcome_probabilities: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to get outcome probabilities from URL {polymarket_url}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def get_event_data(polymarket_url: str) -> Optional[Dict[str, Any]]:
    """
    Get complete event data including all markets with outcome probabilities.
    
    Args:
        polymarket_url: Full Polymarket event URL (e.g., https://polymarket.com/event/event-slug)
        
    Returns:
        Dictionary containing event data with all markets and their outcome probabilities, or None if request fails
    """
    try:
        event_slug = extract_event_slug_from_url(polymarket_url)
        event_data = get_event_by_slug(event_slug)
        
        if not event_data:
            return None
        
        # Parse outcome probabilities for each market
        markets = event_data.get("markets", [])
        for market in markets:
            outcomes = market.get("outcomes")
            outcome_prices = market.get("outcomePrices")
            
            # Parse JSON strings if needed
            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except json.JSONDecodeError:
                    outcomes = []
            
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except json.JSONDecodeError:
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
            
            market['outcomeProbabilities'] = outcome_probabilities
        
        return event_data
    except Exception as e:
        logger.error(f"Failed to get event data from URL {polymarket_url}: {str(e)}")
        return None


def get_market_data(polymarket_url: str) -> Optional[Dict[str, Any]]:
    """
    Get complete event data including all markets (alias for get_event_data for backward compatibility).
    """
    return get_event_data(polymarket_url)


def list_markets(
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    List markets from Polymarket's Gamma API with optional filters.
    
    Args:
        active: Filter by active status (True/False)
        closed: Filter by closed status (True/False)
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of market dictionaries, or None if request fails
    """
    url = f"{POLYMARKET_API_BASE_URL}/markets"
    
    params = {}
    if active is not None:
        params['active'] = str(active).lower()
    if closed is not None:
        params['closed'] = str(closed).lower()
    if limit is not None:
        params['limit'] = limit
    if offset is not None:
        params['offset'] = offset
    
    headers = {}
    if POLYMARKET_API_KEY:
        headers['Authorization'] = f'Bearer {POLYMARKET_API_KEY}'
    
    try:
        logger.info(f"Fetching markets list with params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched {len(data) if isinstance(data, list) else 'unknown'} markets")
        return data if isinstance(data, list) else [data]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch markets list: {str(e)}")
        return None


def list_events(
    active: Optional[bool] = None,
    closed: Optional[bool] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    List events from Polymarket's Gamma API with optional filters.
    
    Args:
        active: Filter by active status (True/False)
        closed: Filter by closed status (True/False)
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of event dictionaries, or None if request fails
    """
    url = f"{POLYMARKET_API_BASE_URL}/events"
    
    params = {}
    if active is not None:
        params['active'] = str(active).lower()
    if closed is not None:
        params['closed'] = str(closed).lower()
    if limit is not None:
        params['limit'] = limit
    if offset is not None:
        params['offset'] = offset
    
    headers = {}
    if POLYMARKET_API_KEY:
        headers['Authorization'] = f'Bearer {POLYMARKET_API_KEY}'
    
    try:
        logger.info(f"Fetching events list with params: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched {len(data) if isinstance(data, list) else 'unknown'} events")
        return data if isinstance(data, list) else [data]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch events list: {str(e)}")
        return None

