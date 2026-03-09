# backend/tests/conftest.py
"""
Pytest configuration.
Adds backend/ to the Python path so imports work correctly.
"""
import sys
from pathlib import Path

# add backend/ to path 
sys.path.insert(0, str(Path(__file__).parent.parent))