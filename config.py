"""
Configuration module for the Polymarket pipeline.
Loads environment variables and sets up configuration parameters.
"""

import os
import sys
import logging
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, continue without it
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"transform_data.log")
    ]
)

# Create a logger
logger = logging.getLogger("config")

# Base paths and directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, "tmp")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Create directories if they don't exist
for directory in [DATA_DIR, TMP_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Polymarket configuration
POLYMARKET_BASE = os.environ.get("POLYMARKET_BASE", "https://polymarket.com")
POLYMARKET_API = os.environ.get("POLYMARKET_API", "https://strapi-matic.poly.market/api")
POLYMARKET_GQL = os.environ.get("POLYMARKET_GQL", "https://gamma-api.poly.market/graphql")

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL_ID")

# Discord configuration (optional, if using Discord instead of Slack)
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
DISCORD_CHANNEL = os.environ.get("DISCORD_CHANNEL")

# Messaging platform (slack or discord)
MESSAGING_PLATFORM = os.environ.get("MESSAGING_PLATFORM", "slack")

# OpenAI API key for banner generation
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Frontend repository configuration
FRONTEND_REPO = os.environ.get("FRONTEND_REPO", "https://github.com/example/frontend-repo")
FRONTEND_IMG_PATH = os.environ.get("FRONTEND_IMG_PATH", "public/images/markets")

# Blockchain configuration for ApeChain
APECHAIN_RPC = os.environ.get("APECHAIN_RPC", "https://rpc.apechain.io")
MARKET_FACTORY_ADDR = os.environ.get("MARKET_FACTORY_ADDR", "0xMarketFactory")
PRIVATE_KEY = os.environ.get("PRIVATE_KEY")

# Pipeline configuration
APPROVAL_WINDOW_MINUTES = int(os.environ.get("APPROVAL_WINDOW_MINUTES", "30"))
MAX_MARKETS_PER_RUN = int(os.environ.get("MAX_MARKETS_PER_RUN", "10"))

# Get the current timestamp
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Display configuration summary (excluding secrets)
logger.info(f"Polymarket base URL: {POLYMARKET_BASE}")
logger.info(f"Messaging platform: {MESSAGING_PLATFORM}")
logger.info(f"Approval window: {APPROVAL_WINDOW_MINUTES} minutes")
logger.info(f"Data directory: {DATA_DIR}")
logger.info(f"Temporary directory: {TMP_DIR}")
logger.info(f"Logs directory: {LOGS_DIR}")

# Check if required environment variables are set
required_vars = {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_CHANNEL_ID": SLACK_CHANNEL,
    "OPENAI_API_KEY": OPENAI_API_KEY
}

missing_vars = [name for name, value in required_vars.items() if not value]

if missing_vars:
    logger.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
    logger.warning("Some functionality may not work correctly.")
else:
    logger.info("All required environment variables are set.")