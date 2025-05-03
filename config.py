"""
Configuration module for the Polymarket pipeline.
Loads environment variables and sets up configuration parameters.
"""
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, using environment variables directly")

# Base configuration
POLYMARKET_BASE_URL = os.getenv("POLYMARKET_BASE", "https://strapi-matic.poly.market/api")
APPROVAL_WINDOW_MINUTES = int(os.getenv("WINDOWS", "30"))

# Messaging configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID")  # Use SLACK_CHANNEL_ID directly
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL = os.getenv("DISCORD_CHANNEL")

# Image generation configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Git repository configuration
FRONTEND_REPO = os.getenv("FRONTEND_REPO")
FRONTEND_IMG_PATH = os.getenv("IMG_PATH", "https://raw.githubusercontent.com/apechain/market-frontend/main/public/images/markets")

# Blockchain configuration
APECHAIN_RPC = os.getenv("APECHAIN_RPC")
MARKET_FACTORY_ADDR = os.getenv("MARKET_FACTORY_ADDR")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, "tmp")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# State file
STATE_FILE = os.path.join(DATA_DIR, "state.json")

# Log file
LOG_DATE = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = os.path.join(LOGS_DIR, f"pipeline_{LOG_DATE}.log")

# Ensure directories exist
for directory in [DATA_DIR, TMP_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Determine messaging platform
if SLACK_BOT_TOKEN and SLACK_CHANNEL:
    MESSAGING_PLATFORM = "slack"
elif DISCORD_TOKEN and DISCORD_CHANNEL:
    MESSAGING_PLATFORM = "discord"
else:
    # Default to slack for development without raising an error
    MESSAGING_PLATFORM = "slack"
    print("Warning: Slack or Discord configuration not complete, defaulting to Slack for development")

# Validate required configuration - using softer validation for development
if not POLYMARKET_BASE_URL:
    print("Warning: POLYMARKET_BASE environment variable not set, using default")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY environment variable not set, image generation will fail")

if not FRONTEND_REPO or not FRONTEND_IMG_PATH:
    print("Warning: FRONTEND_REPO and/or IMG_PATH environment variables not set, banner deployment will fail")

if not APECHAIN_RPC or not MARKET_FACTORY_ADDR or not PRIVATE_KEY:
    print("Warning: Blockchain configuration incomplete, market deployment will fail")