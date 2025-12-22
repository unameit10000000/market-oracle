"""
Polymarket API routes
"""

import os
import json
import logging
import traceback
import requests
from flask import request, jsonify

from . import app
import poly

logger = logging.getLogger(__name__)


@app.route('/poly/check-keys', methods=['GET'])
def poly_check_keys():
    """
    Check if Polymarket API keys are configured.
    
    Returns:
        {
            "status": "success",
            "keys_configured": true/false,
            "keys_present": {
                "api_key": true/false,
                "api_secret": true/false,
                "api_passphrase": true/false
            }
        }
    """
    try:
        # Support both POLY_API_* (preferred) and POLYMARKET_API_* (legacy) variable names
        api_key = os.getenv('POLY_API_KEY') or os.getenv('POLYMARKET_API_KEY', '')
        api_secret = os.getenv('POLY_API_SECRET') or os.getenv('POLYMARKET_API_SECRET', '')
        api_passphrase = os.getenv('POLY_API_PASSPHRASE') or os.getenv('POLYMARKET_API_PASSPHRASE', '')
        
        keys_present = {
            "api_key": bool(api_key and api_key.strip()),
            "api_secret": bool(api_secret and api_secret.strip()),
            "api_passphrase": bool(api_passphrase and api_passphrase.strip())
        }
        
        # Consider keys configured if at least API key is present
        # (some endpoints might only need the key, not secret/passphrase)
        keys_configured = keys_present["api_key"]
        
        return jsonify({
            'status': 'success',
            'keys_configured': keys_configured,
            'keys_present': keys_present
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking Polymarket API keys: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


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
                "question": market.get("question", ""),  # Market question/title
                "groupItemTitle": market.get("groupItemTitle", ""),  # Price range label (e.g., "<78,000", "86,000-88,000")
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
        # Support both POLY_API_* (preferred) and POLYMARKET_API_* (legacy) variable names
        api_key = os.getenv('POLY_API_KEY') or os.getenv('POLYMARKET_API_KEY', '')
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
        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

