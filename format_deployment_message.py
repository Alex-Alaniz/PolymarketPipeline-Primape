
def format_deployment_message(
    market_id: str,
    question: str,
    category: str,
    options: List[str],
    expiry: str,
    banner_uri: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for deployment approval.
    
    Args:
        market_id: Market ID
        question: Market question
        category: Market category
        options: List of option values
        expiry: Human-readable expiry date
        banner_uri: Optional banner image URI
        
    Returns:
        Tuple of (message text, blocks)
    """
    # Format options as comma-separated string
    options_str = ', '.join(options) if options else 'Yes, No'
    
    # Format message text
    message_text = f"*Market for Deployment Approval*  *Question:* {question}"
    
    # Create blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Market for Deployment Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {question}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Category:* {category}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Options:* {options_str}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Expiry:* {expiry}"
            }
        }
    ]
    
    # Add banner if available
    if banner_uri:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Banner:* {banner_uri}"
            }
        })
    
    # Add approval context
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "React with :white_check_mark: to approve deployment or :x: to reject"
        }
    })
    
    return message_text, blocks
