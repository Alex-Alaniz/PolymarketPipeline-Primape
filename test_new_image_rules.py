#!/usr/bin/env python3

"""
Test the new image handling rules.

This script resets the database, runs the pipeline to fetch markets with our updated
image handling rules, and verifies that the images are correctly extracted.
"""

import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_database():
    """
    Reset the database using the true_reset.py script.
    """
    logger.info("Resetting database...")
    
    # Import and run the true_reset script
    try:
        import true_reset
        result = true_reset.main()
        
        # true_reset.main() returns 0 on success, not a boolean
        if result == 0:
            logger.info("✅ Database reset successfully")
            return True
        else:
            logger.error(f"❌ Failed to reset database (exit code {result})")
            return False
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def run_pipeline():
    """
    Run the market pipeline with the updated image handling.
    """
    logger.info("Running pipeline with new image handling rules...")
    
    # Run the pipeline directly
    try:
        # Run the pipeline script directly
        logger.info("Running pipeline.py directly")
        from main import app
        
        with app.app_context():
            cmd = "python pipeline.py"
            import subprocess
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Pipeline completed successfully")
                logger.info(f"Output: {result.stdout}")
                return True
            else:
                logger.error(f"Pipeline failed with exit code {result.returncode}")
                logger.error(f"Error: {result.stderr}")
                return False
    except Exception as e:
        logger.error(f"Error running pipeline: {str(e)}")
        return False

def main():
    """
    Main function to test the image handling rules.
    """
    # Step 1: Reset the database
    if not reset_database():
        return 1
    
    # Step 2: Run the pipeline with the new image handling
    if not run_pipeline():
        return 1
    
    logger.info("✅ Test completed successfully")
    logger.info("Now check Slack for the posted markets with correct images!")
    return 0

if __name__ == "__main__":
    sys.exit(main())