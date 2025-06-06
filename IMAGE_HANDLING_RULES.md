# Polymarket Image Handling Rules

This document outlines the rules for handling images in the Polymarket pipeline. These rules ensure consistent and correct image display in both the Slack approval process and the frontend.

## Image Source Rules

### Banner Images

1. **Binary Markets (Yes/No outcomes):**
   - Use the market-level `image` field for the banner
   - Binary markets only need a single image

2. **Multi-option Markets (e.g., "Who will win?"):**
   - **ALWAYS** use `market["events"][0]["image"]` for the event banner image
   - **NEVER** use option-level images for the banner (we don't want a team logo as the event banner)
   - The event banner should represent the overall event (e.g., La Liga logo for "La Liga Winner 2024-2025")

### Option Icons

1. **Binary Markets (Yes/No outcomes):**
   - Do not display separate icons for Yes/No options
   - Only use the banner image

2. **Multi-option Markets:**
   - For each option, collect icons from **both** of these sources:
     - `option_markets[N].icon` - Icon for each associated market
     - `events[0].outcomes[N].icon` - Icon from each event outcome
   - Always validate URLs before using them
   - Ensure icon images match the option they represent (e.g., team logo for team name)
   - Deduplicate options that represent the same entity (e.g., "Real Madrid" and "Will Real Madrid win?")

## Slack Message Formatting

1. **Binary Markets:**
   - Display the banner image as a single image block
   - Show Yes/No options as text only
   - Format: `*Options:* Yes, No`

2. **Multi-option Markets:**
   - Display the event banner at the top
   - Show each deduplicated option with its own separate image block (not embedded in text fields)
   - Organize options in a clear, consistent layout
   - Ensure each entity (team, candidate) appears only once after deduplication

## URL Validation

1. **All URLs must be:**
   - Well-formed (starting with http:// or https://)
   - Accessible by Slack (some domains are blocked by Slack)
   - Actually image URLs (ending with common image extensions)
   - Not containing placeholder text like "undefined", "null", etc.

2. **Slack Accessibility:**
   - Only use image URLs from domains that Slack can access
   - For testing, we prioritize Imgur (`i.imgur.com`) which is confirmed to be reliable and Slack-accessible
   - Wikimedia (`upload.wikimedia.org`) may sometimes work but is less reliable than Imgur
   - For production, prioritize using `polymarket-upload.s3.us-east-2.amazonaws.com` URLs

## Slack-Compatible Image Domains

The following domains have been confirmed to work reliably with Slack:

1. **Highest Priority (Most Reliable):**
   - `i.imgur.com` - Imgur direct image links (confirmed working in all tests)
   - `polymarket-upload.s3.us-east-2.amazonaws.com` - Polymarket's official S3 bucket
   - `files.slack.com` - Slack's own CDN

2. **Reliable Media Platforms:**
   - `pbs.twimg.com` - Twitter image CDN
   - `cdn.discordapp.com` - Discord CDN
   - `media.discordapp.net` - Discord media network
   - `media.giphy.com` - Giphy media CDN

3. **Image Services:**
   - `images.unsplash.com` - Unsplash CDN
   - `cdn.pixabay.com` - Pixabay CDN

4. **Variable Reliability:**
   - `upload.wikimedia.org` - Sometimes works but can be inconsistent

## Common Issues and Solutions

1. **Wrong Banner Issue:**
   - **Problem:** Using a team/option image as the event banner
   - **Solution:** ALWAYS use `market["events"][0]["image"]` for multi-option markets

2. **Missing Options Issue:**
   - **Problem:** Options not showing in Slack messages
   - **Solution:** Extract options from BOTH `option_markets` and `events[0].outcomes`

3. **Image Rendering Issue:**
   - **Problem:** Images not showing in Slack
   - **Solution:** Validate URLs and only use Slack-accessible domains

4. **Duplicate Options Issue:**
   - **Problem:** Same entity appearing multiple times (e.g., "Real Madrid" and "Will Real Madrid win?")
   - **Solution:** Use deduplication logic to identify and merge duplicate entities (see OPTION_DEDUPLICATION.md)

## Implementation Guidelines

1. Use the `process_event_images()` function to extract and validate images
2. Use the `format_market_with_images()` function to create Slack message blocks
3. Always check URLs with both `is_valid_url()` and `is_slack_accessible_url()`
4. Log image selection decisions for debugging