"""
Analysis module - AI-powered analysis functions for market events
"""

import os
import json
import glob
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests

from config import (
    anthropic_client, DEFAULT_MODEL, AI_API_TYPE, 
    ANTHROPIC_API_KEY, OPENROUTER_API_KEY,
    ANALYSIS_DIR, parse_date, parse_bool,
    FOREXFACTORY_START_DATE, FOREXFACTORY_USE_WEEK,
    TRADINGECONOMICS_START_DATE, TRADINGECONOMICS_END_DATE
)
from scrapers import scrape_forexfactory, scrape_tradingeconomics
from utils import log_output_to_file

logger = logging.getLogger(__name__)

# Import config variables that need to be modified in run_analysis_with_config
import config as config_module


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
    
    # Add real events to prompt if provided (include resolve_time for LISTED events)
    for event in recent_events_data:
        date = event.get('date', 'N/A')
        resolve_time = event.get('resolve_time', event.get('time', ''))
        title = event.get('title', 'N/A')
        description = event.get('description', event.get('title', 'N/A'))
        if resolve_time and resolve_time != 'N/A':
            prompt += f"\n- {date} {resolve_time}: {title} - {description}\n"
        else:
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
    
    # Format new events from actual scraped data (include resolve_time for LISTED events)
    if new_events and len(new_events) > 0:
        new_events_str = "\n".join([
            f"- {e.get('date', 'N/A')} {e.get('resolve_time', e.get('time', 'N/A'))}: {e.get('title', 'N/A')} - {e.get('description', 'N/A')} (Source: {e.get('source_url', 'N/A')})"
            if e.get('resolve_time') != 'N/A' and e.get('resolve_time') else
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
- <date> <resolve_time>: <PREDICTION TYPE> (<magnitude>), <title> - <reasoning based on historical patterns>;

IMPORTANT: Include the resolve_time (timestamp) ONLY for LISTED events from economic calendars (ForexFactory, TradingEconomics). For other events (Mentioned, Predicted), use "N/A" for resolve_time or omit it.

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
- 2025-12-18 2:00pm: PUMP IF CUT (4-6%), BOE Rate Decision - Historical: Rate cuts pump crypto 4-6% (2024 pattern);
- 2025-12-18 8:30am: DUMP IF STRONG (4-8%), US Retail Sales - Historical: Strong retail sales = Fed hawkish = crypto dumps (Dec 2024: -6%);
- 2025-12-15 3:00am: DUMP IF WEAK (3-5%), China Economic Data - Historical: Weak China data = global slowdown fears = dump (Aug 2015: -15%, Jan 2016: -22%);

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

5. Format each event as: <date> <resolve_time>: <PREDICTION TYPE> (<magnitude>), <title> - <reasoning with historical reference>;
   - Include resolve_time ONLY for LISTED events (from economic calendars)
   - For Mentioned/Predicted events, omit resolve_time or use "N/A"

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
    # Use config_module.ANALYSIS_DIR to get the current value (may be set by run_analysis_with_config)
    if config_module.ANALYSIS_DIR is None:
        raise ValueError("Analysis directory not initialized. Call init_analysis_directory() first.")
    prompt_filepath = os.path.join(config_module.ANALYSIS_DIR, "ai_prompt.txt")
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
Token,Date,Resolve_Time,Event_Type,Forecast,Timeframe,Title,Description,Event_Category,Price_Level,Price_Type,Pattern,Content_Source,Confidence_Level

# FIELD DEFINITIONS (use EXACT values/formats):
- Token: Cryptocurrency name (e.g., Bitcoin, Ethereum) or "General" for market-wide events.
- Date: YYYY-MM-DD or "N/A" if no specific date.
- Resolve_Time: Exact timestamp when event resolves (e.g., "2025-12-15 10:30pm", "2025-12-19 12:30 AM"). Use "N/A" for non-Listed events (Mentioned, Predicted) or when timestamp is not available. ONLY include timestamps for LISTED events from economic calendars.
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
2) Every subsequent line is a data row; every row must contain exactly 14 comma-separated values (13 commas).
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
Token,Date,Resolve_Time,Event_Type,Forecast,Timeframe,Title,Description,Event_Category,Price_Level,Price_Type,Pattern,Content_Source,Confidence_Level
General,2025-12-14,2025-12-14 10:30pm,Listed,NEUTRAL,Future,BusinessNZ Services Index (NZ),Minor regional data; limited crypto impact,Economic Data,N/A,N/A,N/A,ForexFactory,N/A
General,2025-12-15,2025-12-15 3:00am,Listed,DUMP IF WEAK,Future,China Economic Data Cluster,Weak China data triggers global slowdown fears and crypto selloffs,Economic Data,N/A,N/A,N/A,Multiple,Medium
Bitcoin,2025-12-19,N/A,Predicted,MAJOR VOLATILITY,Future,BOJ Policy Rate Decision,BOJ hawkish surprise = severe yen carry trade unwind = crypto crash,Regulatory,N/A,N/A,N/A,Analysis,High

# FINAL CHECK: Before returning, ensure header matches exactly and every row has 14 values (13 commas). Return only the CSV inside a single ```txt code block.
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
    # Store original values
    original_ff_start = FOREXFACTORY_START_DATE
    original_ff_week = FOREXFACTORY_USE_WEEK
    original_te_start = TRADINGECONOMICS_START_DATE
    original_te_end = TRADINGECONOMICS_END_DATE
    
    try:
        # Override global config with provided values
        if 'forexfactory_start_date' in config:
            config_module.FOREXFACTORY_START_DATE = parse_date(config.get('forexfactory_start_date'))
        if 'forexfactory_use_week' in config:
            config_module.FOREXFACTORY_USE_WEEK = parse_bool(str(config.get('forexfactory_use_week', True)))
        if 'tradingeconomics_start_date' in config:
            config_module.TRADINGECONOMICS_START_DATE = parse_date(config.get('tradingeconomics_start_date'))
        if 'tradingeconomics_end_date' in config:
            config_module.TRADINGECONOMICS_END_DATE = parse_date(config.get('tradingeconomics_end_date'))
        
        # Use existing analysis directory (created by /validate endpoint)
        analysis_dir = os.path.join("analysis", analysis_id)
        
        # Check if analysis directory exists
        if not os.path.exists(analysis_dir):
            raise ValueError(f"Analysis directory not found: {analysis_dir}. Run /validate endpoint first.")
        
        # Set global ANALYSIS_DIR so other functions can use it
        config_module.ANALYSIS_DIR = analysis_dir
        
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
        config_module.FOREXFACTORY_START_DATE = original_ff_start
        config_module.FOREXFACTORY_USE_WEEK = original_ff_week
        config_module.TRADINGECONOMICS_START_DATE = original_te_start
        config_module.TRADINGECONOMICS_END_DATE = original_te_end

