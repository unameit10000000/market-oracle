"""
Utility functions for the application
"""

import os
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Import config module to access ANALYSIS_DIR (which may be updated dynamically)
import config as config_module


def log_output_to_file(data: Any, filename: str, description: str = ""):
    """
    Log output data to a file in the analysis directory.
    
    Args:
        data: Data to log (can be string, dict, list, etc.)
        filename: Output filename
        description: Optional description to add to the log
    """
    # Use config_module.ANALYSIS_DIR to get the current value (may be set by run_analysis_with_config)
    if config_module.ANALYSIS_DIR is None:
        raise ValueError("Analysis directory not initialized. Call init_analysis_directory() first.")
    
    filepath = os.path.join(config_module.ANALYSIS_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        if description:
            f.write(f"# {description}\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            f.write("=" * 80 + "\n\n")
        
        if isinstance(data, (dict, list)):
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            f.write(str(data))
    
    logger.info(f"Logged output to {filepath}")

