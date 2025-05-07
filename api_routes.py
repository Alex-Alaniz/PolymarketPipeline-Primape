#!/usr/bin/env python3
"""
API Routes for Frontend Integration

This module provides API endpoints for the frontend to:
1. Fetch market categorization data
2. Get market banner and option images
3. Query deployed markets by category
4. Fetch event relationships and related markets

These endpoints enable the frontend to display proper categorization, 
event relationships, and images for markets deployed to the Apechain blockchain.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy.exc import SQLAlchemyError

from models import Market, PipelineRun, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/status')
def pipeline_status():
    """
    Get the status of the pipeline.
    
    Returns:
        JSON response with pipeline status information
    """
    try:
        # Get the latest pipeline run
        latest_run = PipelineRun.query.order_by(PipelineRun.start_time.desc()).first()
        
        if not latest_run:
            return jsonify({
                "status": "none",
                "message": "No pipeline runs found"
            })
        
        return jsonify({
            "status": latest_run.status,
            "started_at": latest_run.start_time.isoformat() if latest_run.start_time else None,
            "completed_at": latest_run.end_time.isoformat() if latest_run.end_time else None,
            "markets_processed": latest_run.markets_processed,
            "markets_approved": latest_run.markets_approved,
            "markets_deployed": latest_run.markets_deployed,
            "error": latest_run.error
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting pipeline status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting pipeline status"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting pipeline status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting pipeline status"
        }), 500

@api_bp.route('/market/<market_id>')
def get_market_data(market_id):
    """
    Get market data for a given market ID (Apechain market ID).
    
    This endpoint provides the category, banner, and option images for a market
    for display in the frontend.
    
    Args:
        market_id: Apechain market ID
        
    Returns:
        JSON response with market data including category and images
    """
    try:
        # Find the market by Apechain market ID
        market = Market.query.filter_by(apechain_market_id=market_id).first()
        
        if not market:
            return jsonify({
                "status": "not_found",
                "message": f"Market with Apechain ID {market_id} not found"
            }), 404
        
        # Format the market data for response
        market_data = {
            "id": market.id,
            "apechain_market_id": market.apechain_market_id,
            "question": market.question,
            "category": market.category,
            "status": market.status,
            "banner_uri": market.banner_uri,
            "option_images": market.option_images,
            "created_at": market.created_at.isoformat() if market.created_at else None,
            "updated_at": market.updated_at.isoformat() if market.updated_at else None
        }
        
        return jsonify({
            "status": "success",
            "market": market_data
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting market data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting market data"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting market data: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting market data"
        }), 500

@api_bp.route('/markets')
def get_markets():
    """
    Get all deployed markets.
    
    This endpoint provides a list of all deployed markets with their 
    categories and image data for display in the frontend.
    
    Query Parameters:
        category: Filter markets by category
        status: Filter markets by status (default: 'deployed')
        limit: Maximum number of markets to return (default: 100)
        
    Returns:
        JSON response with list of markets
    """
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        status = request.args.get('status', 'deployed')
        limit = int(request.args.get('limit', 100))
        
        # Build query
        query = Market.query.filter_by(status=status)
        
        if category:
            query = query.filter_by(category=category.lower())
        
        # Get markets, ordered by creation date
        markets = query.order_by(Market.created_at.desc()).limit(limit).all()
        
        # Format the markets for response
        market_list = []
        for market in markets:
            market_data = {
                "id": market.id,
                "apechain_market_id": market.apechain_market_id,
                "question": market.question,
                "category": market.category,
                "status": market.status,
                "banner_uri": market.banner_uri,
                "created_at": market.created_at.isoformat() if market.created_at else None,
                "updated_at": market.updated_at.isoformat() if market.updated_at else None
            }
            market_list.append(market_data)
        
        return jsonify({
            "status": "success",
            "markets": market_list,
            "count": len(market_list)
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting markets: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting markets"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting markets: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting markets"
        }), 500

@api_bp.route('/categories')
def get_categories():
    """
    Get all available market categories and their counts.
    
    This endpoint provides a list of all market categories and the number
    of markets in each category for frontend filtering.
    
    Returns:
        JSON response with list of categories and counts
    """
    try:
        # Get all deployed markets
        markets = Market.query.filter_by(status='deployed').all()
        
        # Count markets by category
        categories = {}
        for market in markets:
            category = market.category or 'uncategorized'
            if category in categories:
                categories[category] += 1
            else:
                categories[category] = 1
        
        # Format the categories for response
        category_list = [
            {"name": category, "count": count} 
            for category, count in categories.items()
        ]
        
        return jsonify({
            "status": "success",
            "categories": category_list
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting categories: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting categories"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting categories"
        }), 500

@api_bp.route('/images/<apechain_market_id>')
def get_market_images(apechain_market_id):
    """
    Get all images for a market.
    
    This endpoint provides both the banner image and option images
    for a specific market.
    
    Args:
        apechain_market_id: Apechain market ID
        
    Returns:
        JSON response with banner and option images
    """
    try:
        # Find the market by Apechain market ID
        market = Market.query.filter_by(apechain_market_id=apechain_market_id).first()
        
        if not market:
            return jsonify({
                "status": "not_found",
                "message": f"Market with Apechain ID {apechain_market_id} not found"
            }), 404
        
        # Format the image data for response
        image_data = {
            "banner_uri": market.banner_uri,
            "option_images": market.option_images or {}
        }
        
        return jsonify({
            "status": "success",
            "images": image_data
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting market images: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting market images"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting market images: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting market images"
        }), 500

@api_bp.route('/events')
def get_events():
    """
    Get all events and their related markets.
    
    This endpoint provides a list of all events with their associated markets,
    useful for displaying related markets in the frontend.
    
    Query Parameters:
        category: Filter events by category
        limit: Maximum number of events to return (default: 50)
        
    Returns:
        JSON response with list of events and their markets
    """
    try:
        # Get query parameters for filtering
        category = request.args.get('category')
        limit = int(request.args.get('limit', 50))
        
        # Get all events with deployed markets
        markets = Market.query.filter(
            Market.status == 'deployed',
            Market.event_id.isnot(None)
        )
        
        if category:
            markets = markets.filter_by(category=category.lower())
        
        # Get unique events
        events = {}
        for market in markets:
            if not market.event_id:
                continue
                
            if market.event_id not in events:
                events[market.event_id] = {
                    "event_id": market.event_id,
                    "event_name": market.event_name,
                    "category": market.category,
                    "markets": []
                }
            
            events[market.event_id]["markets"].append({
                "id": market.id,
                "apechain_market_id": market.apechain_market_id,
                "question": market.question
            })
        
        # Convert to list and limit results
        event_list = list(events.values())[:limit]
        
        return jsonify({
            "status": "success",
            "events": event_list,
            "count": len(event_list)
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting events: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting events"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting events: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting events"
        }), 500

@api_bp.route('/event/<event_id>')
def get_event(event_id):
    """
    Get a specific event and all its related markets.
    
    This endpoint provides detailed information about an event and all markets
    associated with it, useful for displaying event pages in the frontend.
    
    Args:
        event_id: Event ID
        
    Returns:
        JSON response with event details and markets
    """
    try:
        # Find markets for this event
        markets = Market.query.filter_by(
            event_id=event_id,
            status='deployed'
        ).all()
        
        if not markets:
            return jsonify({
                "status": "not_found",
                "message": f"Event with ID {event_id} not found or has no deployed markets"
            }), 404
        
        # Get event info from the first market (they all have the same event info)
        event_name = markets[0].event_name
        category = markets[0].category
        
        # Format market data
        market_list = []
        for market in markets:
            market_data = {
                "id": market.id,
                "apechain_market_id": market.apechain_market_id,
                "question": market.question,
                "banner_uri": market.banner_uri,
                "status": market.status,
                "created_at": market.created_at.isoformat() if market.created_at else None
            }
            market_list.append(market_data)
        
        # Format event data
        event_data = {
            "event_id": event_id,
            "event_name": event_name,
            "category": category,
            "market_count": len(market_list),
            "markets": market_list
        }
        
        return jsonify({
            "status": "success",
            "event": event_data
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting event: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting event"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting event: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting event"
        }), 500

@api_bp.route('/category/<apechain_market_id>')
def get_market_category(apechain_market_id):
    """
    Get the category for a specific market.
    
    This lightweight endpoint only returns the category
    for a specific market, useful for quick categorization lookups.
    
    Args:
        apechain_market_id: Apechain market ID
        
    Returns:
        JSON response with market category
    """
    try:
        # Find the market by Apechain market ID
        market = Market.query.filter_by(apechain_market_id=apechain_market_id).first()
        
        if not market:
            return jsonify({
                "status": "not_found",
                "message": f"Market with Apechain ID {apechain_market_id} not found"
            }), 404
        
        return jsonify({
            "status": "success",
            "market_id": apechain_market_id,
            "category": market.category or "uncategorized"
        })
    
    except SQLAlchemyError as e:
        logger.error(f"Database error getting market category: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Database error getting market category"
        }), 500
    
    except Exception as e:
        logger.error(f"Error getting market category: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error getting market category"
        }), 500