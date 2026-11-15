import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'development-only-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///shop.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CATALOG_PATH = ROOT / 'data' / 'catalog.json'
    TRACKING_SCENARIOS_PATH = ROOT / 'data' / 'tracking_scenarios.json'
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL', 'http://localhost:5000')
    MAX_CONTENT_LENGTH = 16 * 1024
    PRODUCTION = os.environ.get('DOPADROP_ENV') == 'production'
