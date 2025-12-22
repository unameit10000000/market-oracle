"""
Main API routes - Root, validate, analyze, and process endpoints
"""

import os
import json
import glob
import logging
from flask import request, jsonify

from . import app
from config import (
    AI_API_TYPE, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, anthropic_client,
    parse_youtube_urls, init_analysis_directory
)
from youtube import validate_and_extract_youtube_transcripts
from analysis import run_analysis_with_config, generate_csv_from_analysis

logger = logging.getLogger(__name__)


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

