"""
Web search and AI query routes
"""

import os
import logging
from flask import request, jsonify

from . import app
from config import AI_API_TYPE, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, anthropic_client
from analysis import perform_web_search

logger = logging.getLogger(__name__)


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
- Resolve Time: {event.get('Resolve_Time', 'N/A')}
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

