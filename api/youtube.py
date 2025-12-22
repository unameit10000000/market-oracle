"""
YouTube transcript extraction module
"""

import os
import re
import glob
import subprocess
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs

from config import YOUTUBE_URLS, ANALYSIS_DIR

logger = logging.getLogger(__name__)


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


def validate_and_extract_youtube_transcripts(urls: List[str], analysis_dir: str) -> Dict[str, Any]:
    """
    Validate and extract transcripts from YouTube URLs, returning success/failure for each.
    
    Args:
        urls: List of YouTube URLs to validate and extract
        analysis_dir: Directory path where transcripts should be saved
        
    Returns:
        Dictionary with:
            - analysis_id: datetime string
            - transcripts: List of dicts with url, success (bool), video_id, error (optional)
    """
    logger.info(f"Validating and extracting transcripts for {len(urls)} URLs")
    
    # Extract datetime ID from directory path
    analysis_id = os.path.basename(analysis_dir)
    
    # Ensure directory exists
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Temporary directory for downloading subtitle files
    temp_dir = analysis_dir
    
    transcript_results = []
    
    for idx, url in enumerate(urls, 1):
        logger.info(f"Processing URL {idx}/{len(urls)}: {url}")
        
        result = {
            'url': url,
            'success': False,
            'video_id': None,
            'error': None
        }
        
        try:
            # Extract video ID
            video_id = extract_video_id(url)
            if not video_id:
                result['error'] = "Could not extract video ID from URL"
                logger.error(f"Could not extract video ID from URL: {url}")
                transcript_results.append(result)
                continue
            
            result['video_id'] = video_id
            
            # Extract transcript
            transcript = extract_youtube_transcript(video_id, temp_dir)
            if not transcript:
                result['error'] = "Could not extract transcript (video may not have subtitles)"
                logger.error(f"Could not extract transcript for video ID: {video_id}")
                transcript_results.append(result)
                continue
            
            # Save transcript to file
            safe_video_id = re.sub(r'[^\w\-_]', '_', video_id)
            filename = f"{safe_video_id}_transcript.txt"
            filepath = os.path.join(analysis_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# YouTube Transcript\n\n")
                f.write(f"Video URL: {url}\n")
                f.write(f"Video ID: {video_id}\n")
                f.write(f"Extracted: {datetime.now().isoformat()}\n\n")
                f.write("=" * 80 + "\n\n")
                f.write(transcript)
            
            logger.info(f"Successfully saved transcript to {filepath}")
            result['success'] = True
            transcript_results.append(result)
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error processing URL {url}: {e}")
            transcript_results.append(result)
    
    successful_count = sum(1 for r in transcript_results if r['success'])
    logger.info(f"Transcript validation completed: {successful_count}/{len(urls)} successful")
    
    return {
        'analysis_id': analysis_id,
        'transcripts': transcript_results
    }


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

