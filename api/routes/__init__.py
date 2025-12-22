"""
Routes package - Contains all Flask route handlers
"""

from flask import Flask
from flask_cors import CORS

# Create Flask app instance
app = Flask(__name__)
# Enable CORS for all routes - permissive for development
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# Import all route modules to register routes
from . import main_routes, poly_routes, websearch_routes

__all__ = ['app']

