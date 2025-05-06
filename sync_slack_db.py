#!/usr/bin/env python3
"""
Slack and Database Synchronization Tool

This script synchronizes the state between Slack messages and the database.
It ensures that:
1. Every message in Slack has a corresponding entry in the database
2. Messages for deployed markets are updated to reflect their status
3. Reaction buttons are removed from processed markets
4. Visual formatting clearly indicates the current state of each market
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_db_sync")

# Import flask app context for database access
from main import app
from models import db, ProcessedMarket, Market, ApprovalEvent
from utils.messaging import MessagingClient

# Initialize Slack client
slack_client = MessagingClient()

def get_all_slack_messages() -> List[Dict[str, Any]]:
    """
    Get all relevant messages from the Slack channel.
    
    Returns:
        List of message objects with key metadata
    """
    logger.info("Fetching messages from Slack channel")
    
    # Get messages from the Slack channel (up to 1000 to ensure we get most messages)
    messages = []
    cursor = None
    
    # Paginate through messages up to a reasonable limit
    for _ in range(10):  # Up to 10 pages of 100 messages each
        batch, cursor = slack_client.get_channel_history(limit=100, cursor=cursor)
        if batch:
            messages.extend(batch)
            logger.info(f"Fetched {len(batch)} messages, total: {len(messages)}")
        
        if not cursor:
            break
    
    logger.info(f"Fetched a total of {len(messages)} messages from Slack")
    return messages

def process_slack_messages(messages: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """
    Process Slack messages and synchronize with database.
    
    Args:
        messages: List of Slack message objects
        
    Returns:
        Tuple of (synced, updated, cleaned) message counts
    """
    synced_count = 0
    updated_count = 0
    cleaned_count = 0
    
    with app.app_context():
        # Get all ProcessedMarket records that have been posted to Slack
        posted_markets = ProcessedMarket.query.filter_by(posted=True).all()
        posted_map = {market.message_id: market for market in posted_markets if market.message_id}
        
        # Get all Markets that have been deployed
        deployed_markets = Market.query.filter_by(status="deployed").all()
        deployed_ids = {market.id for market in deployed_markets}
        
        # Get all Markets that are in deployment approval stage
        deployment_pending = Market.query.filter_by(status="pending_deployment").all()
        deployment_pending_ids = {market.id for market in deployment_pending}
        
        # Process each message
        for message in messages:
            message_id = message.get('ts')
            
            # Skip messages without text or attachments (might be system messages)
            if not message.get('text') and not message.get('attachments'):
                continue
            
            # Check if this message is in our database
            if message_id in posted_map:
                processed_market = posted_map[message_id]
                
                # Check if this market has moved to the Market table and been deployed
                if processed_market.approved and processed_market.condition_id in deployed_ids:
                    # This market has been deployed - update the message to show deployed status
                    logger.info(f"Market {processed_market.condition_id} has been deployed - updating Slack message")
                    update_deployed_message(message_id, processed_market)
                    cleaned_count += 1
                elif processed_market.approved and processed_market.condition_id in deployment_pending_ids:
                    # This market is pending deployment - update message to show pending deployment
                    logger.info(f"Market {processed_market.condition_id} is pending deployment - updating Slack message")
                    update_pending_deployment_message(message_id, processed_market)
                    updated_count += 1
                # Otherwise, it's in a normal state - no action needed
                synced_count += 1
            else:
                # This message isn't in our database - try to parse and add it
                logger.info(f"Message {message_id} not found in database - attempting to sync")
                if sync_message_to_db(message):
                    synced_count += 1
    
    return synced_count, updated_count, cleaned_count

def sync_message_to_db(message: Dict[str, Any]) -> bool:
    """
    Sync a Slack message to the database if it represents a market.
    
    Args:
        message: Slack message object
        
    Returns:
        Boolean indicating success
    """
    message_id = message.get('ts')
    
    # Try to extract market data from the message
    market_data = extract_market_data_from_message(message)
    
    if not market_data or not market_data.get('condition_id'):
        # Not a market message or couldn't extract data
        logger.debug(f"Could not extract valid market data from message {message_id}")
        return False
    
    with app.app_context():
        # Check if we already have this market by condition_id
        existing = ProcessedMarket.query.filter_by(condition_id=market_data['condition_id']).first()
        
        if existing:
            # We have this market but with a different message ID - update it
            logger.info(f"Found existing market {market_data['condition_id']} - updating with message ID {message_id}")
            existing.message_id = message_id
            existing.posted = True
            
            # If we have raw_data in the market_data but not in existing, update it
            if not existing.raw_data and 'raw_data' in market_data:
                logger.info(f"Updating raw_data for market {market_data['condition_id']}")
                existing.raw_data = market_data['raw_data']
            
            # Check for reactions
            reactions = message.get('reactions', [])
            update_approval_status_from_reactions(existing, reactions)
            
            db.session.commit()
            logger.info(f"Updated existing market record for {market_data['condition_id']} with message ID {message_id}")
            
            # If market is approved, check if we need to create a Market entry
            if existing.approved and not Market.query.get(existing.condition_id):
                logger.info(f"Market {existing.condition_id} is approved but no Market entry exists - attempting to create one")
                try:
                    from check_market_approvals import create_market_entry
                    if existing.raw_data:
                        success = create_market_entry(existing.raw_data)
                        if success:
                            logger.info(f"Created Market entry for approved market {existing.condition_id}")
                except Exception as e:
                    logger.error(f"Error creating Market entry: {str(e)}")
            
            return True
        else:
            # Create a new record
            try:
                # Try to extract or create a more complete raw_data
                enhanced_data = enhance_market_data(message, market_data)
                
                new_market = ProcessedMarket(
                    condition_id=market_data['condition_id'],
                    question=market_data.get('question', 'Unknown question'),
                    first_seen=datetime.utcnow(),
                    posted=True,
                    message_id=message_id,
                    raw_data=enhanced_data
                )
                
                # Check for reactions
                reactions = message.get('reactions', [])
                update_approval_status_from_reactions(new_market, reactions)
                
                db.session.add(new_market)
                db.session.commit()
                logger.info(f"Created new market record for {market_data['condition_id']} from message {message_id}")
                
                # If market is approved, try to create Market entry
                if new_market.approved:
                    logger.info(f"Newly created market {new_market.condition_id} is approved - attempting to create Market entry")
                    try:
                        from check_market_approvals import create_market_entry
                        if new_market.raw_data:
                            success = create_market_entry(new_market.raw_data)
                            if success:
                                logger.info(f"Created Market entry for newly approved market {new_market.condition_id}")
                    except Exception as e:
                        logger.error(f"Error creating Market entry: {str(e)}")
                
                return True
            except Exception as e:
                logger.error(f"Error creating market record: {str(e)}")
                db.session.rollback()
                return False

def enhance_market_data(message: Dict[str, Any], basic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance market data with additional information from the message.
    
    Args:
        message: Slack message object
        basic_data: Basic market data extracted from the message
        
    Returns:
        Enhanced market data dictionary
    """
    enhanced_data = basic_data.copy()
    
    # Try to extract JSON data from the message text
    try:
        text = message.get('text', '')
        if '{' in text and '}' in text:
            import re
            # More aggressive JSON pattern that can span multiple lines
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, text)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    # Check if this JSON contains relevant market data
                    if 'condition_id' in data or 'conditionId' in data or 'id' in data:
                        # Match the ID to make sure we're using the right JSON object
                        potential_id = data.get('condition_id') or data.get('conditionId') or data.get('id')
                        if potential_id == basic_data['condition_id']:
                            logger.info(f"Found complete raw data for market {basic_data['condition_id']}")
                            # This is our market data, use it as raw_data
                            enhanced_data = data
                            if 'condition_id' not in enhanced_data and 'conditionId' in enhanced_data:
                                enhanced_data['condition_id'] = enhanced_data['conditionId']
                            enhanced_data['extracted_from_json'] = True
                            return enhanced_data
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning(f"Error extracting JSON from message text: {str(e)}")
    
    # If we couldn't extract complete data, set minimal fields
    if 'question' not in enhanced_data:
        enhanced_data['question'] = extract_question_from_message(message) or "Unknown Market"
    
    if 'end_date' not in enhanced_data and 'endDate' not in enhanced_data:
        # Try to extract date from message
        date_str = extract_date_from_message(message)
        if date_str:
            enhanced_data['endDate'] = date_str
    
    enhanced_data['manual_entry'] = True
    return enhanced_data

def extract_question_from_message(message: Dict[str, Any]) -> Optional[str]:
    """Extract market question from Slack message"""
    # Check attachments first
    if message.get('attachments'):
        for attachment in message['attachments']:
            if attachment.get('title'):
                return attachment['title']
    
    # Check message text
    text = message.get('text', '')
    
    # Pattern: "*Question:* Some question text"
    if '*Question:*' in text:
        lines = text.split('\n')
        for line in lines:
            if '*Question:*' in line:
                return line.replace('*Question:*', '').strip()
    
    # Pattern: "Will X happen?"
    if 'Will ' in text:
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith('Will ') and '?' in line:
                return line.strip()
    
    return None

def extract_date_from_message(message: Dict[str, Any]) -> Optional[str]:
    """Extract end date from Slack message"""
    # Look for date patterns in text
    text = message.get('text', '')
    
    # Pattern: "*End Date:* YYYY-MM-DD"
    if '*End Date:*' in text:
        lines = text.split('\n')
        for line in lines:
            if '*End Date:*' in line:
                date_str = line.replace('*End Date:*', '').strip()
                # Try to parse and format the date
                try:
                    from dateutil import parser
                    date_obj = parser.parse(date_str)
                    return date_obj.isoformat() + 'Z'
                except:
                    return date_str
    
    return None

def extract_market_data_from_message(message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract market data from a Slack message.
    
    Args:
        message: Slack message object
        
    Returns:
        Market data dictionary or None
    """
    logger.debug(f"Extracting market data from message: {message.get('ts')}")
    
    # Try to extract from attachments first - most reliable method
    if message.get('attachments'):
        for attachment in message['attachments']:
            # Look for fields with condition_id
            if attachment.get('fields'):
                for field in attachment['fields']:
                    if field.get('title') == 'Condition ID':
                        condition_id = field.get('value')
                        logger.debug(f"Found condition_id in attachment fields: {condition_id}")
                        # Build minimal market data
                        market_data = {
                            'condition_id': condition_id,
                            'question': attachment.get('title', 'Unknown Market')
                        }
                        return market_data
    
    # Try to extract from text - less reliable but good fallback
    text = message.get('text', '')
    
    # Pattern 1: "Condition ID: XXX"
    if 'Condition ID:' in text:
        logger.debug("Found 'Condition ID:' pattern in text")
        # Try to parse structured text
        lines = text.split('\n')
        condition_id = None
        question = None
        
        for line in lines:
            if line.startswith('*Question:*'):
                question = line.replace('*Question:*', '').strip()
            elif 'Condition ID:' in line:
                condition_id = line.split('Condition ID:')[1].strip()
                # Remove any trailing whitespace, quotes, or special chars
                condition_id = condition_id.strip("'\"` \t\n\r")
        
        if condition_id:
            logger.debug(f"Extracted condition_id from text: {condition_id}")
            return {
                'condition_id': condition_id,
                'question': question or 'Unknown Market'
            }
    
    # Pattern 2: Look for markdown formatted links with question/ID pattern
    # Example: <https://polymarket.com/event/question-text|Condition ID: xxx>
    if '<https://polymarket.com/event/' in text:
        logger.debug("Found polymarket URL pattern in text")
        import re
        # Match polymarket URL pattern
        pattern = r'<https://polymarket\.com/event/[^|>]+\|([^>]+)>'
        matches = re.findall(pattern, text)
        
        for match in matches:
            # Check if this contains a condition ID
            if 'Condition ID:' in match:
                parts = match.split('Condition ID:')
                if len(parts) > 1:
                    condition_id = parts[1].strip()
                    logger.debug(f"Extracted condition_id from URL: {condition_id}")
                    return {
                        'condition_id': condition_id,
                        'question': parts[0].strip() or 'Unknown Market'
                    }
    
    # Pattern 3: Look for JSON data that might be stored in the message
    try:
        if 'raw_data' in text and '{' in text and '}' in text:
            logger.debug("Found potential JSON data in text")
            # Extract JSON part 
            import re
            json_pattern = r'\{[^\}]+\}'
            json_matches = re.findall(json_pattern, text)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if data.get('condition_id') or data.get('id'):
                        logger.debug(f"Extracted condition_id from JSON: {data.get('condition_id') or data.get('id')}")
                        return {
                            'condition_id': data.get('condition_id') or data.get('id'),
                            'question': data.get('question') or 'Unknown Market'
                        }
                except:
                    pass
    except:
        logger.debug("Error parsing potential JSON in message")
    
    # Could not extract market data
    logger.debug("Could not extract market data from message")
    return None

def update_approval_status_from_reactions(market: ProcessedMarket, reactions: List[Dict[str, Any]]) -> None:
    """
    Update market approval status based on Slack reactions.
    
    Args:
        market: ProcessedMarket instance
        reactions: List of reaction objects from Slack message
    """
    check_reaction = None
    x_reaction = None
    
    for reaction in reactions:
        if reaction['name'] == 'white_check_mark':
            check_reaction = reaction
        elif reaction['name'] == 'x':
            x_reaction = reaction
    
    # If we have approval reaction
    if check_reaction and not x_reaction:
        if market.approved is not True:
            market.approved = True
            market.approval_date = datetime.utcnow()
            # Use first user as approver
            if check_reaction.get('users'):
                market.approver = check_reaction['users'][0]
    
    # If we have rejection reaction
    elif x_reaction and not check_reaction:
        if market.approved is not False:
            market.approved = False
            market.approval_date = datetime.utcnow()
            # Use first user as rejecter
            if x_reaction.get('users'):
                market.approver = x_reaction['users'][0]

def update_deployed_message(message_id: str, market: ProcessedMarket) -> None:
    """
    Update a Slack message to indicate the market has been deployed.
    
    Args:
        message_id: Slack message ID
        market: ProcessedMarket instance
    """
    # Get original message
    message = slack_client.client.conversations_history(
        channel=slack_client.channel_id,
        latest=message_id,
        limit=1,
        inclusive=True
    )
    
    if not message or not message.get('messages'):
        logger.error(f"Could not retrieve message {message_id}")
        return
    
    original = message['messages'][0]
    
    # Create updated message with deployed status
    if original.get('attachments'):
        # Update the first attachment color to green
        attachments = original['attachments']
        attachments[0]['color'] = '#36a64f'  # Green
        
        # Add footer showing deployed status
        deployed_market = Market.query.get(market.condition_id)
        if deployed_market:
            # Format timestamp
            deployed_time = deployed_market.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            attachments[0]['footer'] = f"✅ DEPLOYED to ApeChain on {deployed_time} | ID: {deployed_market.apechain_market_id or 'Unknown'}"
            
            # Add blockchain transaction if available
            if deployed_market.blockchain_tx:
                attachments[0]['footer_icon'] = "https://www.apechain.io/favicon.ico"
            
            # Try to update the message
            try:
                slack_client.client.chat_update(
                    channel=slack_client.channel_id,
                    ts=message_id,
                    attachments=attachments,
                    text=original.get('text')
                )
                
                # Remove reactions since they're no longer needed
                for reaction in ['white_check_mark', 'x']:
                    try:
                        slack_client.client.reactions_remove(
                            channel=slack_client.channel_id,
                            timestamp=message_id,
                            name=reaction
                        )
                    except:
                        # Ignore errors removing reactions
                        pass
                
                logger.info(f"Updated message {message_id} to show deployed status")
            except Exception as e:
                logger.error(f"Error updating message {message_id}: {str(e)}")

def update_pending_deployment_message(message_id: str, market: ProcessedMarket) -> None:
    """
    Update a Slack message to indicate the market is pending deployment.
    
    Args:
        message_id: Slack message ID
        market: ProcessedMarket instance
    """
    # Get original message
    message = slack_client.client.conversations_history(
        channel=slack_client.channel_id,
        latest=message_id,
        limit=1,
        inclusive=True
    )
    
    if not message or not message.get('messages'):
        logger.error(f"Could not retrieve message {message_id}")
        return
    
    original = message['messages'][0]
    
    # Create updated message with pending deployment status
    if original.get('attachments'):
        # Update the first attachment color to yellow
        attachments = original['attachments']
        attachments[0]['color'] = '#daa520'  # Gold/yellow
        
        # Add footer showing pending status
        deployed_market = Market.query.get(market.condition_id)
        if deployed_market:
            # Format timestamp
            approval_time = market.approval_date.strftime("%Y-%m-%d %H:%M:%S UTC") if market.approval_date else "Unknown"
            attachments[0]['footer'] = f"⏳ PENDING DEPLOYMENT | Approved on {approval_time}"
            
            # Try to update the message
            try:
                slack_client.client.chat_update(
                    channel=slack_client.channel_id,
                    ts=message_id,
                    attachments=attachments,
                    text=original.get('text')
                )
                logger.info(f"Updated message {message_id} to show pending deployment status")
            except Exception as e:
                logger.error(f"Error updating message {message_id}: {str(e)}")

def main():
    """
    Main function to synchronize Slack and database.
    
    Returns:
        Tuple[int, int, int]: Counts of (synced, updated, cleaned) messages
    """
    synced, updated, cleaned = 0, 0, 0
    
    try:
        logger.info("Starting Slack-Database synchronization")
        
        # Get all messages from Slack
        messages = get_all_slack_messages()
        
        # Process messages and sync with database
        synced, updated, cleaned = process_slack_messages(messages)
        
        logger.info(f"Synchronization complete:")
        logger.info(f"  - {synced} messages synced with database")
        logger.info(f"  - {updated} messages updated for pending deployment")
        logger.info(f"  - {cleaned} messages cleaned up for deployed markets")
        
    except Exception as e:
        logger.error(f"Error during synchronization: {str(e)}")
        # Still return counts, but they will be zeros in case of error
    
    return synced, updated, cleaned

if __name__ == "__main__":
    result = main()
    # Return 0 for success when called directly from the command line
    sys.exit(0 if result and isinstance(result, tuple) else 1)