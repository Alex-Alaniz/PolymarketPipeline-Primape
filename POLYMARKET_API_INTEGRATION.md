# Polymarket API Integration Guide

This document explains how our pipeline integrates with Polymarket's API to fetch and process different types of market data.

## API Endpoints

Polymarket Gamma API provides two distinct endpoints that we use:

1. **Markets API**: `https://gamma-api.polymarket.com/markets`
   - Returns individual binary markets (Yes/No prediction markets)
   - These are standalone markets not part of events

2. **Events API**: `https://gamma-api.polymarket.com/events`
   - Returns event collections that contain multiple related markets
   - Used for multi-option markets (like sports competitions with multiple teams)

## Data Processing Flow

Our pipeline handles these two data types differently:

### Binary Markets Processing

1. Fetch binary markets from the Markets API
2. Filter to only include markets without an associated event
3. Process each binary market individually
4. Each binary market becomes its own "event" (1:1 relationship)
5. Store as standalone markets in the database

### Event Markets Processing

1. Fetch events from the Events API
2. Each event contains multiple related markets
3. Transform the entire event into a single market with multiple options
   - Event title becomes the market question
   - Event banner becomes the market banner
   - Child markets become options in the transformed market
4. Store as event-based markets with proper relationships

## Option Image Handling

- For binary markets: Use the market outcome images as option images
- For event markets: Use the child market icons as option images, with option names as keys

## Market Categorization

- Binary markets are categorized individually
- Event markets inherit the event category with fallback to GPT-4o-mini categorization

## Deployment Process

- Both binary and event markets follow the same approval workflow
- Event markets deploy all child markets together as a group
- Binary markets deploy individually

This separation ensures we correctly handle the different data structures while maintaining a consistent user experience for both market types.