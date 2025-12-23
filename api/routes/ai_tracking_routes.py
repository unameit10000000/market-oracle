"""
AI Tracking API routes
Handles automated thinking and chat functionality for tracking modules
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Tuple
from flask import request, jsonify

from . import app
import poly
from config import (
    anthropic_client, DEFAULT_MODEL, AI_API_TYPE,
    ANTHROPIC_API_KEY, OPENROUTER_API_KEY
)

logger = logging.getLogger(__name__)

# System prompt for AI tracking
SYSTEM_PROMPT_TEMPLATE = """Based on our existing analysis, and our provided realtime data as of now {timestamp}, give your two cents about what is happening. In particular I want you to provide an immediate action plan containing what to look out for, what to track and how to respond."""


def read_analysis_files(analysis_id: str) -> Tuple[str, str]:
    """
    Read analysis files from the analysis directory.
    
    Args:
        analysis_id: Analysis ID (e.g., "20251223_000322")
        
    Returns:
        Tuple of (comprehensive_analysis, csv_data)
        
    Raises:
        FileNotFoundError: If analysis directory or files don't exist
    """
    analysis_dir = os.path.join("analysis", analysis_id)
    
    if not os.path.exists(analysis_dir):
        raise FileNotFoundError(f"Analysis directory not found: {analysis_dir}")
    
    # Read comprehensive_analysis.txt
    comprehensive_analysis_path = os.path.join(analysis_dir, "comprehensive_analysis.txt")
    if not os.path.exists(comprehensive_analysis_path):
        raise FileNotFoundError(f"Comprehensive analysis file not found: {comprehensive_analysis_path}")
    
    with open(comprehensive_analysis_path, 'r', encoding='utf-8') as f:
        comprehensive_analysis = f.read()
    
    # Read output.csv
    csv_path = os.path.join(analysis_dir, "output.csv")
    csv_data = ""
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            csv_data = f.read()
    else:
        logger.warning(f"CSV file not found: {csv_path}. Continuing without CSV data.")
    
    return comprehensive_analysis, csv_data


def construct_ai_prompt(
    comprehensive_analysis: str,
    csv_data: str,
    chat_history: list[dict],
    module_data: dict,
    enabled_modules: list[str]
) -> tuple[str, str]:
    """
    Construct AI prompt with analysis files, chat history, and module data.
    
    Args:
        comprehensive_analysis: Content of comprehensive_analysis.txt
        csv_data: Content of output.csv
        chat_history: List of previous chat messages
        module_data: Dictionary of module data (e.g., {"polymarket": {...}})
        enabled_modules: List of enabled module names
        
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # System prompt with timestamp
    timestamp = datetime.now().isoformat()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(timestamp=timestamp)
    
    # Build user prompt
    user_prompt_parts = []
    
    # 1. Analysis files (always included)
    user_prompt_parts.append("=== EXISTING ANALYSIS ===")
    user_prompt_parts.append("\nComprehensive Analysis:")
    user_prompt_parts.append(comprehensive_analysis)
    
    if csv_data:
        user_prompt_parts.append("\n\nCSV Data:")
        user_prompt_parts.append(csv_data)
    
    # 2. Chat history (if available)
    if chat_history and len(chat_history) > 0:
        user_prompt_parts.append("\n\n=== CHAT HISTORY ===")
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            user_prompt_parts.append(f"\n{role.upper()}: {content}")
    
    # 3. Module data (conditional, based on enabled modules)
    if "polymarket" in enabled_modules and "polymarket" in module_data:
        polymarket_data = module_data["polymarket"]
        user_prompt_parts.append("\n\n=== REALTIME POLYMARKET DATA ===")
        user_prompt_parts.append("Realtime information provided from Polymarket:")
        user_prompt_parts.append(json.dumps(polymarket_data, indent=2))
        user_prompt_parts.append("\n\nNote: The frontend displays calculated values for each market:")
        user_prompt_parts.append("- ID: Market identifier")
        user_prompt_parts.append("- Active/Open: Market status")
        user_prompt_parts.append("- Price: Price range label (e.g., '<78,000', '86,000-88,000')")
        user_prompt_parts.append("- Volume: Trading volume")
        user_prompt_parts.append("- Chance: Probability percentage (Yes outcome)")
        user_prompt_parts.append("- Buy Yes/No: Prices in cents")
    
    # Join all parts
    user_prompt = "\n".join(user_prompt_parts)
    
    return system_prompt, user_prompt


def call_ai_api(system_prompt: str, user_prompt: str) -> str:
    """
    Call AI API (OpenRouter or Anthropic) with the constructed prompts.
    
    Args:
        system_prompt: System prompt
        user_prompt: User prompt
        
    Returns:
        AI response text
        
    Raises:
        Exception: If API call fails
    """
    if not anthropic_client:
        error_msg = f"{AI_API_TYPE} API key not configured"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    try:
        logger.info(f"Calling AI API ({AI_API_TYPE}) with model {DEFAULT_MODEL}")
        
        # Use streaming for better performance
        with anthropic_client.messages.stream(
            model=DEFAULT_MODEL,
            max_tokens=8000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        ) as stream:
            response_text = ""
            for text in stream.text_stream:
                response_text += text
        
        logger.info(f"AI API response received (length: {len(response_text)})")
        return response_text
        
    except Exception as e:
        logger.error(f"Error calling AI API: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


@app.route('/ai-tracking/start-thinking', methods=['POST'])
def start_thinking():
    """
    Start auto thinking mode.
    
    Request body:
    {
        "interval": "15m",
        "enabled_modules": ["polymarket"],
        "analysis_id": "20251223_000322",
        "chat_history": [...]
    }
    
    Returns:
    {
        "status": "success",
        "message": "Auto thinking started",
        "next_fetch_at": "2025-12-23T10:45:00Z"
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        interval = data.get('interval')
        enabled_modules = data.get('enabled_modules', [])
        analysis_id = data.get('analysis_id')
        chat_history = data.get('chat_history', [])
        
        # Validate required fields
        if not interval:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: interval'
            }), 400
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id'
            }), 400
        
        # Validate interval format
        valid_intervals = ['5m', '15m', '30m', '1h', '4h']
        if interval not in valid_intervals:
            return jsonify({
                'status': 'error',
                'error': f'Invalid interval. Must be one of: {", ".join(valid_intervals)}'
            }), 400
        
        # Calculate next fetch time (for display purposes)
        # Frontend controls timing, but we can provide a suggested time
        from datetime import timedelta
        interval_map = {
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '30m': timedelta(minutes=30),
            '1h': timedelta(hours=1),
            '4h': timedelta(hours=4)
        }
        next_fetch_at = (datetime.now() + interval_map[interval]).isoformat()
        
        logger.info(f"Auto thinking started for analysis_id: {analysis_id}, interval: {interval}")
        
        return jsonify({
            'status': 'success',
            'message': 'Auto thinking started',
            'next_fetch_at': next_fetch_at
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /ai-tracking/start-thinking: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/ai-tracking/stop-thinking', methods=['POST'])
def stop_thinking():
    """
    Stop auto thinking mode.
    
    Request body:
    {
        "analysis_id": "20251223_000322"
    }
    
    Returns:
    {
        "status": "success",
        "message": "Auto thinking stopped"
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        analysis_id = data.get('analysis_id')
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id'
            }), 400
        
        logger.info(f"Auto thinking stopped for analysis_id: {analysis_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Auto thinking stopped'
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /ai-tracking/stop-thinking: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/ai-tracking/fetch-analysis', methods=['POST'])
def fetch_analysis():
    """
    Fetch analysis with module data (auto mode).
    
    Request body:
    {
        "analysis_id": "20251223_000322",
        "enabled_modules": ["polymarket"],
        "chat_history": [...],
        "polymarket_config": {
            "url": "https://polymarket.com/event/...",
            "slug": "bitcoin-above-on-december-23"
        }
    }
    
    Returns:
    {
        "ai_response": {
            "content": "...",
            "timestamp": "2025-12-23T10:30:00Z"
        },
        "polymarket_response": {
            "status": "success",
            "event_slug": "...",
            "endDate": "...",
            "markets_count": 11,
            "markets": [...]
        }
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        analysis_id = data.get('analysis_id')
        enabled_modules = data.get('enabled_modules', [])
        chat_history = data.get('chat_history', [])
        polymarket_config = data.get('polymarket_config', {})
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id'
            }), 400
        
        # Validate API key
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured'
                }), 500
        
        # Read analysis files
        try:
            comprehensive_analysis, csv_data = read_analysis_files(analysis_id)
        except FileNotFoundError as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 404
        
        # Fetch module data
        module_data = {}
        polymarket_response = None
        
        if "polymarket" in enabled_modules:
            try:
                # Get Polymarket data
                slug = polymarket_config.get('slug')
                url = polymarket_config.get('url')
                
                if slug:
                    event_slug = slug
                elif url:
                    event_slug = poly.extract_event_slug_from_url(url)
                else:
                    logger.warning("No Polymarket slug or URL provided, skipping Polymarket data")
                    event_slug = None
                
                if event_slug:
                    # Get event data
                    event_data = poly.get_event_by_slug(event_slug)
                    if event_data:
                        # Format markets data similar to /poly/event/markets/list endpoint
                        markets_raw = event_data.get("markets", [])
                        markets_list = []
                        
                        for market in markets_raw:
                            markets_list.append({
                                "id": market.get("id"),
                                "question": market.get("question", ""),
                                "groupItemTitle": market.get("groupItemTitle", ""),
                                "details": {
                                    "outcomes": market.get("outcomes"),
                                    "outcomePrices": market.get("outcomePrices"),
                                    "volume": market.get("volume"),
                                    "active": market.get("active"),
                                    "closed": market.get("closed")
                                }
                            })
                        
                        polymarket_response = {
                            "status": "success",
                            "event_slug": event_slug,
                            "endDate": event_data.get("endDate", ""),
                            "markets_count": len(markets_list),
                            "markets": markets_list
                        }
                        
                        module_data["polymarket"] = event_data
                    else:
                        logger.warning(f"Failed to fetch Polymarket event data for slug: {event_slug}")
                        polymarket_response = {
                            "status": "error",
                            "error": f"Failed to fetch Polymarket event data"
                        }
            except Exception as e:
                logger.error(f"Error fetching Polymarket data: {e}")
                polymarket_response = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Construct AI prompt
        try:
            system_prompt, user_prompt = construct_ai_prompt(
                comprehensive_analysis,
                csv_data,
                chat_history,
                module_data,
                enabled_modules
            )
        except Exception as e:
            logger.error(f"Error constructing AI prompt: {e}")
            return jsonify({
                'status': 'error',
                'error': f'Failed to construct AI prompt: {str(e)}'
            }), 500
        
        # Call AI API
        try:
            ai_content = call_ai_api(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Error calling AI API: {e}")
            return jsonify({
                'status': 'error',
                'error': f'AI API call failed: {str(e)}'
            }), 500
        
        # Build response
        response = {
            'ai_response': {
                'content': ai_content,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        # Include module responses if available
        if polymarket_response:
            response['polymarket_response'] = polymarket_response
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in /ai-tracking/fetch-analysis: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/ai-tracking/chat', methods=['POST'])
def chat():
    """
    Manual chat endpoint (disabled mode).
    
    Request body:
    {
        "analysis_id": "20251223_000322",
        "message": "User's question",
        "chat_history": [...],
        "enabled_modules": ["polymarket"],
        "polymarket_data": {...}
    }
    
    Returns:
    {
        "ai_response": {
            "content": "...",
            "timestamp": "2025-12-23T10:30:00Z"
        }
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error': 'Request must be JSON'
            }), 400
        
        data = request.get_json()
        analysis_id = data.get('analysis_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])
        enabled_modules = data.get('enabled_modules', [])
        polymarket_data = data.get('polymarket_data')
        
        if not analysis_id:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: analysis_id'
            }), 400
        
        if not message:
            return jsonify({
                'status': 'error',
                'error': 'Missing required parameter: message'
            }), 400
        
        # Validate API key
        if AI_API_TYPE == 'OPENROUTER':
            if not OPENROUTER_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'OPENROUTER_API_KEY not configured'
                }), 500
        else:
            if not ANTHROPIC_API_KEY or not anthropic_client:
                return jsonify({
                    'status': 'error',
                    'error': 'ANTHROPIC_API_KEY not configured'
                }), 500
        
        # Read analysis files
        try:
            comprehensive_analysis, csv_data = read_analysis_files(analysis_id)
        except FileNotFoundError as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 404
        
        # Build module data
        module_data = {}
        if "polymarket" in enabled_modules and polymarket_data:
            module_data["polymarket"] = polymarket_data
        
        # Add user message to chat history
        updated_chat_history = chat_history + [{"role": "user", "content": message}]
        
        # Construct AI prompt
        try:
            system_prompt, user_prompt = construct_ai_prompt(
                comprehensive_analysis,
                csv_data,
                updated_chat_history,
                module_data,
                enabled_modules
            )
        except Exception as e:
            logger.error(f"Error constructing AI prompt: {e}")
            return jsonify({
                'status': 'error',
                'error': f'Failed to construct AI prompt: {str(e)}'
            }), 500
        
        # Call AI API
        try:
            ai_content = call_ai_api(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Error calling AI API: {e}")
            return jsonify({
                'status': 'error',
                'error': f'AI API call failed: {str(e)}'
            }), 500
        
        return jsonify({
            'ai_response': {
                'content': ai_content,
                'timestamp': datetime.now().isoformat()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in /ai-tracking/chat: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

