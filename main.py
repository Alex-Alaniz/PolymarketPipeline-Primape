#!/usr/bin/env python3
"""
Entry point for the Polymarket pipeline.
This file allows running the pipeline via the web interface workflow.

Steps in the pipeline:
1. Fetch active markets from Polymarket public API with category diversity
2. Filter markets to only include non-expired ones with valid image assets
3. Post new markets to Slack for approval (tracked in database)
4. Check for market approvals/rejections in Slack
5. Deploy approved markets to ApeChain with proper UI mapping
6. Generate comprehensive pipeline statistics and logs
"""
from flask import Flask, jsonify, request, render_template_string, send_from_directory
import os
import sys
import threading
import time
from datetime import datetime

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from pipeline import PolymarketPipeline
from models import db, Market, ApprovalEvent, PipelineRun, PendingMarket, ApprovalLog
from api_routes import api_bp

# Create Flask app
app = Flask(__name__)

# Set secret key for CSRF protection
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "polymarket-pipeline-key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database with app
db.init_app(app)

# Register API Blueprint
app.register_blueprint(api_bp)

# Create tables
with app.app_context():
    db.create_all()

# Global variables to track pipeline status
pipeline_status = {
    "running": False,
    "start_time": None,
    "end_time": None,
    "status": "idle",
    "last_message": None,
    "log_messages": []
}

# HTML template for the main page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Pipeline</title>
    <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
    <!-- Add jQuery for better AJAX handling -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: var(--bs-dark);
            color: var(--bs-light);
        }
        h1, h2, h3 {
            color: var(--bs-light);
            text-align: center;
            margin-bottom: 30px;
        }
        .container {
            background-color: var(--bs-dark-bg-subtle);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .status-box {
            border: 1px solid var(--bs-border-color);
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            background-color: var(--bs-dark);
        }
        .log-container {
            max-height: 300px;
            overflow-y: auto;
            padding: 10px;
            background-color: var(--bs-black);
            color: var(--bs-light);
            font-family: monospace;
            border-radius: 4px;
            margin: 20px 0;
        }
        .log-line {
            margin: 2px 0;
            word-wrap: break-word;
        }
        .button {
            background-color: var(--bs-primary);
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .button:hover {
            background-color: var(--bs-primary-hover);
            opacity: 0.9;
        }
        .button:disabled {
            background-color: var(--bs-secondary);
            cursor: not-allowed;
            opacity: 0.7;
        }
        .info {
            margin: 15px 0;
            padding: 10px;
            background-color: var(--bs-dark-bg-subtle);
            border-left: 6px solid var(--bs-primary);
        }
        .text-success {
            color: var(--bs-success) !important;
        }
        .text-danger {
            color: var(--bs-danger) !important;
        }
        .text-primary {
            color: var(--bs-primary) !important;
        }
        .text-secondary {
            color: var(--bs-secondary) !important;
        }
    </style>
</head>
<body>
    <h1>Polymarket Pipeline Control Panel</h1>
    
    <div class="container">
        <div class="status-box">
            <h2>Pipeline Status: 
                <span id="status" class="{% if status.status == 'completed' %}text-success{% elif status.status == 'failed' %}text-danger{% elif status.status == 'running' %}text-primary{% else %}text-secondary{% endif %}">
                    {{ status.status }}
                </span>
            </h2>
            {% if status.running %}
                <p>Running since: {{ status.start_time }}</p>
                <p>Last message: {{ status.last_message }}</p>
                <div class="alert alert-info">
                    <strong>Pipeline in progress!</strong> The page will automatically refresh to show updates.
                </div>
            {% elif status.end_time %}
                <p>Last run: {{ status.start_time }} to {{ status.end_time }}</p>
                
                {% if status.status == 'failed' %}
                    <div class="alert alert-danger">
                        <strong>Pipeline failed!</strong> 
                        {% if "No active markets" in status.last_message %}
                            No active markets were found from Polymarket. All markets may be closed or expired.
                            <ul class="mt-2">
                                <li>This is expected behavior - the pipeline is designed to only process active markets.</li>
                                <li>Check the Polymarket site to verify if there are any active markets currently available.</li>
                            </ul>
                        {% elif "blockchain" in status.last_message %}
                            Failed to connect to the blockchain endpoint.
                            <ul class="mt-2">
                                <li>This could be due to network connectivity issues or endpoint availability.</li>
                                <li>Please try again later or check your blockchain RPC configuration.</li>
                            </ul>
                        {% else %}
                            {{ status.last_message }}
                        {% endif %}
                    </div>
                {% elif status.status == 'completed' %}
                    <div class="alert alert-success">
                        <strong>Pipeline completed successfully!</strong> Check Slack for any markets that were processed.
                    </div>
                {% endif %}
            {% else %}
                <p>Pipeline is idle</p>
                <div class="alert alert-secondary">
                    <strong>Ready to run!</strong> Click the "Run Pipeline" button to start processing Polymarket data.
                </div>
            {% endif %}
        </div>
        
        <div>
            <button id="run-pipeline" class="button" {% if status.running %}disabled{% endif %}>Run Pipeline</button>
            <button id="check-approvals" class="button" style="background-color: var(--bs-success); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Check Market Approvals</button>
            <button id="post-unposted" class="button" style="background-color: var(--bs-purple); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Post Next Batch</button>
            <button id="post-unposted-pending" class="button" style="background-color: var(--bs-indigo); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Post Pending Batch</button>
            <button id="flush-unposted" class="button" style="background-color: var(--bs-danger); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Flush Unposted Markets</button>
            <button id="run-deployment" class="button" style="background-color: var(--bs-warning); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Check Deployment Approvals</button>
            <button id="sync-slack-db" class="button" style="background-color: var(--bs-info); margin-left: 10px;" {% if status.running %}disabled{% endif %}>Sync Slack & DB</button>
            <a href="/pipeline-flow" class="button" style="background-color: var(--bs-secondary); margin-left: 10px; text-decoration: none;">View Pipeline Flow</a>
        </div>
        
        <div class="info">
            <p>This application runs the Polymarket Pipeline, automating the process of:</p>
            <ol>
                <li>Fetching diverse markets from Polymarket API across multiple categories</li>
                <li>Filtering to active, non-expired markets with valid image assets</li>
                <li>Posting new markets to Slack for initial approval (with ✅ to approve, ❌ to reject)</li>
                <li>Tracking market approvals/rejections in the database (with auto-reject after 7 days)</li>
                <li>Processing approved markets through a separate deployment approval flow</li>
                <li>Deploying fully approved markets to ApeChain with frontend mappings</li>
            </ol>
            
            <p class="alert alert-info mt-3">
                <strong>Note:</strong> The main pipeline handles initial market approvals, while the 
                <strong>Check Deployment Approvals</strong> button runs a separate process for final QA
                and deployment to ApeChain. This two-step approval process ensures quality control.
            </p>
            
            <p class="alert alert-warning">
                <strong>Important:</strong> Markets that remain in pending status for more than 7 days
                will be automatically rejected to prevent accumulation of stale data.
            </p>
        </div>
        
        <h3>Log Messages</h3>
        <div class="log-container" id="log-container">
            {% for message in status.log_messages %}
                <div class="log-line">{{ message }}</div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        // Using jQuery for more reliable AJAX
        $(document).ready(function() {
            // Function to send POST request with jQuery
            function sendPostRequest(url, buttonId) {
                // Disable the button
                $("#" + buttonId).prop("disabled", true);
                
                // Make the AJAX request
                $.ajax({
                    url: url,
                    type: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({}),
                    dataType: "json",
                    success: function(data) {
                        if (data.success) {
                            // Update the status
                            $("#status").text("running");
                            
                            // Disable all action buttons
                            $(".button").prop("disabled", true);
                            
                            // Refresh the page after 2 seconds
                            setTimeout(function() {
                                window.location.reload();
                            }, 2000);
                        } else {
                            // Show error message
                            alert("Failed: " + data.message);
                            
                            // Re-enable the button
                            $("#" + buttonId).prop("disabled", false);
                        }
                    },
                    error: function(xhr, status, error) {
                        // Log the error details
                        console.error("Error:", error);
                        console.error("Status:", status);
                        console.error("Response:", xhr.responseText);
                        
                        // Show error message
                        alert("An error occurred. Please try again.");
                        
                        // Re-enable the button
                        $("#" + buttonId).prop("disabled", false);
                    }
                });
            }
            
            // Run Pipeline button
            $("#run-pipeline").click(function(e) {
                e.preventDefault();
                sendPostRequest("/run-pipeline", "run-pipeline");
            });
            
            // Check Market Approvals button
            $("#check-approvals").click(function(e) {
                e.preventDefault();
                sendPostRequest("/check-market-approvals", "check-approvals");
            });
            
            // Check Deployment Approvals button
            $("#run-deployment").click(function(e) {
                e.preventDefault();
                sendPostRequest("/run-deployment-approvals", "run-deployment");
            });
            
            // Sync Slack & DB button
            $("#sync-slack-db").click(function(e) {
                e.preventDefault();
                sendPostRequest("/sync-slack-db", "sync-slack-db");
            });
            
            // Post Next Batch button
            $("#post-unposted").click(function(e) {
                e.preventDefault();
                sendPostRequest("/post-unposted-markets", "post-unposted");
            });
            
            // Post Pending Batch button
            $("#post-unposted-pending").click(function(e) {
                e.preventDefault();
                sendPostRequest("/post-unposted-pending-markets", "post-unposted-pending");
            });
            
            // Flush Unposted Markets button
            $("#flush-unposted").click(function(e) {
                e.preventDefault();
                if (confirm("WARNING: This will delete all unposted markets from the database. This action cannot be undone. Markets already posted to Slack will be preserved.\n\nDo you want to continue?")) {
                    sendPostRequest("/flush-unposted-markets", "flush-unposted");
                }
            });
            
            // Auto-refresh if the pipeline is running
            {% if status.running %}
            setTimeout(function() {
                window.location.reload();
            }, 5000);
            {% endif %}
        });
        
        // Console logging for debugging
        console.log("Pipeline UI loaded - jQuery button handlers attached");
    </script>
</body>
</html>
"""

class LogCapture:
    """Custom handler to capture log messages"""
    def __init__(self):
        self.messages = []
    
    def write(self, message):
        if message.strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] {message.strip()}"
            pipeline_status["log_messages"].append(formatted_message)
            pipeline_status["last_message"] = message.strip()
            
            # Keep only the last 100 messages
            if len(pipeline_status["log_messages"]) > 100:
                pipeline_status["log_messages"] = pipeline_status["log_messages"][-100:]
    
    def flush(self):
        pass

def run_pipeline():
    """Run the pipeline in a separate thread"""
    # Skip if we're in testing mode
    if os.environ.get("TESTING") == "true":
        return
    # Redirect stdout and stderr to our log capture
    log_capture = LogCapture()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = log_capture
    sys.stderr = log_capture
    
    try:
        # Update UI status
        pipeline_status["running"] = True
        pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pipeline_status["status"] = "running"
        
        # Log pipeline start
        print("Starting Polymarket pipeline...")
        
        # Create database entry for this run
        with app.app_context():
            pipeline_run = PipelineRun(
                start_time=datetime.now(),
                status="running"
            )
            db.session.add(pipeline_run)
            db.session.commit()
            run_id = pipeline_run.id
            print(f"Created pipeline run record with ID: {run_id}")
        
        # Run the pipeline
        pipeline = PolymarketPipeline(db_run_id=run_id)
        exit_code = pipeline.run()
        
        # Update UI status based on exit code
        pipeline_status["running"] = False
        pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pipeline_status["status"] = "completed" if exit_code == 0 else "failed"
        
        # Update database record
        with app.app_context():
            pipeline_run = PipelineRun.query.get(run_id)
            if pipeline_run:
                pipeline_run.end_time = datetime.now()
                pipeline_run.status = "completed" if exit_code == 0 else "failed"
                db.session.commit()
        
        # Log pipeline end
        print(f"Pipeline {pipeline_status['status']} with exit code {exit_code}")
        
    except Exception as e:
        # Log any exceptions
        error_message = str(e)
        print(f"Pipeline failed with exception: {error_message}")
        
        # Update UI status
        pipeline_status["running"] = False
        pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pipeline_status["status"] = "failed"
        
        # Update database record if possible
        try:
            with app.app_context():
                pipeline_run = PipelineRun.query.filter_by(status="running").order_by(PipelineRun.id.desc()).first()
                if pipeline_run:
                    pipeline_run.end_time = datetime.now()
                    pipeline_run.status = "failed"
                    pipeline_run.error = error_message
                    db.session.commit()
        except Exception as db_error:
            print(f"Failed to update pipeline run record: {str(db_error)}")
    
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@app.route('/')
def index():
    """Main page"""
    return render_template_string(HTML_TEMPLATE, status=pipeline_status)

@app.route('/run-pipeline', methods=['POST'])
def start_pipeline():
    """API endpoint to start the pipeline"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Pipeline is already running"
        })
    
    # Start the pipeline in a separate thread
    thread = threading.Thread(target=run_pipeline)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Pipeline started"
    })

@app.route('/run-deployment-approvals', methods=['POST'])
def start_deployment_approvals():
    """API endpoint to start the deployment approval process"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Pipeline is already running"
        })
    
    # Define a function to run the deployment approvals
    def run_deployment_approvals():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting Deployment Approval Process...")
            
            # Import the deployment approval module
            import check_deployment_approvals
            
            # Run the deployment approval process
            with app.app_context():
                # First post markets for deployment approval
                posted = check_deployment_approvals.post_markets_for_deployment_approval()
                print(f"Posted {len(posted)} markets for deployment approval")
                
                # Then check for approvals
                pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
                print(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Deployment approval process completed successfully")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Deployment approval process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the deployment approval process in a separate thread
    thread = threading.Thread(target=run_deployment_approvals)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Deployment approval process started"
    })

@app.route('/clean-environment', methods=['POST'])
def clean_environment():
    """API endpoint to clean the environment (database and Slack)"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to clean the environment
    def run_environment_cleaning():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting Environment Cleaning...")
            
            # Import the environment cleaning module
            import clean_environment
            
            # Run the environment cleaning process
            with app.app_context():
                exit_code = clean_environment.main()
                if exit_code == 0:
                    print("Environment cleaning completed successfully")
                    success = True
                else:
                    print(f"Environment cleaning failed with exit code {exit_code}")
                    success = False
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Environment cleaning process completed")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Environment cleaning process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the environment cleaning process in a separate thread
    thread = threading.Thread(target=run_environment_cleaning)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Environment cleaning process started"
    })

@app.route('/sync-slack-db', methods=['POST'])
def sync_slack_db():
    """API endpoint to synchronize Slack and database"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to sync Slack and DB
    def run_slack_db_sync():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting Slack-Database Synchronization...")
            
            # Import the sync module
            import sync_slack_db
            
            # Run the synchronization process
            with app.app_context():
                try:
                    # Get the result from the main function
                    result = sync_slack_db.main()
                    
                    # Check if result is a tuple with 3 elements (synced, updated, cleaned)
                    if isinstance(result, tuple) and len(result) == 3:
                        synced, updated, cleaned = result
                        print(f"Synchronization complete: {synced} synced, {updated} updated, {cleaned} cleaned")
                    else:
                        # For backward compatibility, handle non-tuple return
                        print("Synchronization completed successfully")
                except Exception as e:
                    print(f"Error during synchronization: {str(e)}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Slack-DB synchronization completed successfully")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Slack-DB synchronization failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the sync process in a separate thread
    thread = threading.Thread(target=run_slack_db_sync)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Slack-DB synchronization started"
    })

@app.route('/check-market-approvals', methods=['POST'])
def check_market_approvals():
    """API endpoint to check initial market approvals"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to check market approvals
    def run_market_approvals():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting Market Approval Check Process...")
            
            # Import the market approval module
            import check_market_approvals
            
            # Run the market approval process
            with app.app_context():
                # Check for market approvals
                pending, approved, rejected = check_market_approvals.check_market_approvals()
                print(f"Market approval results: {pending} pending, {approved} approved, {rejected} rejected")
                
                # Create market entries for approved markets
                if approved > 0:
                    print("Creating market entries for approved markets...")
                    markets_created = 0
                    
                    # Get all approved markets that haven't been processed yet
                    from models import db, ProcessedMarket
                    approved_markets = ProcessedMarket.query.filter_by(
                        approved=True, 
                        posted=True
                    ).all()
                    
                    for processed_market in approved_markets:
                        if processed_market.raw_data:
                            try:
                                # Create market entry if it doesn't exist yet
                                success = check_market_approvals.create_market_entry(processed_market.raw_data)
                                if success:
                                    markets_created += 1
                            except Exception as e:
                                print(f"Error creating market entry: {str(e)}")
                    
                    print(f"Created {markets_created} market entries for approved markets")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Market approval check process completed successfully")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Market approval check process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the market approval check process in a separate thread
    thread = threading.Thread(target=run_market_approvals)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Market approval check process started"
    })

@app.route('/status')
def get_status():
    """API endpoint to get the pipeline status"""
    return jsonify(pipeline_status)

@app.route('/markets')
def get_markets():
    """API endpoint to get all markets from the database"""
    with app.app_context():
        try:
            markets = Market.query.all()
            return jsonify({
                "count": len(markets),
                "markets": [market.to_dict() for market in markets]
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500

@app.route('/post-unposted-markets', methods=['POST'])
def post_unposted_markets():
    """API endpoint to post the next batch of unposted markets"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to run the unposted markets posting process
    def run_post_unposted_markets():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting process to post unposted markets...")
            
            # Run the post unposted markets process
            from post_unposted_markets import main as post_unposted_main
            
            with app.app_context():
                result = post_unposted_main()
                if result == 0:
                    print("Successfully posted unposted markets")
                else:
                    print("Failed to post unposted markets")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print("Post unposted markets process completed")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Post unposted markets process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the process in a separate thread
    thread = threading.Thread(target=run_post_unposted_markets)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Process to post unposted markets started"
    })

@app.route('/post-unposted-pending-markets', methods=['POST'])
def post_unposted_pending_markets():
    """API endpoint to post the next batch of unposted pending markets"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to run the unposted pending markets posting process
    def run_post_unposted_pending_markets():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting process to post unposted pending markets...")
            
            # Run the post unposted pending markets process
            from post_unposted_pending_markets import main as post_unposted_pending_main
            
            with app.app_context():
                result = post_unposted_pending_main()
                if result == 0:
                    print("Successfully posted unposted pending markets")
                else:
                    print("Failed to post unposted pending markets")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print("Post unposted pending markets process completed")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Post unposted pending markets process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the process in a separate thread
    thread = threading.Thread(target=run_post_unposted_pending_markets)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Process to post unposted pending markets started"
    })

@app.route('/flush-unposted-markets', methods=['POST'])
def flush_unposted_markets():
    """API endpoint to flush unposted markets from the database"""
    print("===> Flush unposted markets route called")
    
    if pipeline_status["running"]:
        print("===> Pipeline is already running, returning error")
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to run the flush process
    def run_flush_unposted_markets():
        # Redirect stdout and stderr to our log capture
        log_capture = LogCapture()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = log_capture
        sys.stderr = log_capture
        
        try:
            # Update UI status
            pipeline_status["running"] = True
            pipeline_status["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "running"
            
            # Log process start
            print("Starting process to flush unposted markets...")
            
            # Import the flush module
            from flush_unposted_markets import flush_unposted_markets, flush_pending_markets, show_database_stats
            
            with app.app_context():
                # Show initial stats
                print("Initial database state:")
                show_database_stats()
                
                # Flush unposted markets
                deleted_unposted = flush_unposted_markets()
                print(f"Deleted {deleted_unposted} unposted markets from ProcessedMarket table")
                
                # Flush pending markets
                deleted_pending = flush_pending_markets()
                print(f"Deleted {deleted_pending} markets from PendingMarket table")
                
                # Show final stats
                print("\nFinal database state:")
                show_database_stats()
                
                # Final summary
                print(f"\nSummary: Deleted {deleted_unposted} unposted markets and {deleted_pending} pending markets")
                print("You can now run the pipeline to refetch and recategorize markets")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Flush unposted markets process completed")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Flush unposted markets process failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    print("===> Starting flush unposted markets thread")
    # Start the process in a separate thread
    thread = threading.Thread(target=run_flush_unposted_markets)
    thread.daemon = True
    thread.start()
    
    print("===> Returning success response")
    return jsonify({
        "success": True,
        "message": "Process to flush unposted markets started"
    })

@app.route('/runs')
def get_runs():
    """API endpoint to get all pipeline runs from the database"""
    with app.app_context():
        try:
            runs = PipelineRun.query.order_by(PipelineRun.id.desc()).all()
            return jsonify({
                "count": len(runs),
                "runs": [run.to_dict() for run in runs]
            })
        except Exception as e:
            return jsonify({
                "error": str(e)
            }), 500

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/pipeline-flow')
def pipeline_flow():
    """Show the pipeline flow diagram"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Polymarket Pipeline Flow</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0 auto;
                padding: 20px;
                background-color: var(--bs-dark);
                color: var(--bs-light);
                text-align: center;
            }
            h1, h2 {
                color: var(--bs-light);
                margin-bottom: 30px;
            }
            .container {
                max-width: 1100px;
                margin: 0 auto;
                background-color: var(--bs-dark-bg-subtle);
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .flow-diagram {
                width: 100%;
                max-width: 1000px;
                height: auto;
                margin: 0 auto;
                display: block;
            }
            .btn {
                display: inline-block;
                margin: 20px 0;
                padding: 10px 20px;
                background-color: var(--bs-primary);
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 16px;
            }
            .btn:hover {
                background-color: var(--bs-primary-hover);
                opacity: 0.9;
            }
            .pipeline-description {
                text-align: left;
                max-width: 900px;
                margin: 0 auto 30px auto;
                padding: 15px;
                background-color: var(--bs-dark);
                border-radius: 8px;
                border-left: 4px solid var(--bs-primary);
            }
            .pipeline-steps {
                list-style-type: none;
                counter-reset: step-counter;
                padding-left: 0;
                margin: 0 auto;
                text-align: left;
                max-width: 800px;
            }
            .pipeline-steps li {
                counter-increment: step-counter;
                margin-bottom: 10px;
                padding: 10px;
                position: relative;
                padding-left: 50px;
            }
            .pipeline-steps li::before {
                content: counter(step-counter);
                position: absolute;
                left: 0;
                top: 5px;
                width: 35px;
                height: 35px;
                background-color: var(--bs-primary);
                color: white;
                border-radius: 50%;
                text-align: center;
                line-height: 35px;
                font-weight: bold;
            }
            .text-info { color: var(--bs-info); }
            .text-warning { color: var(--bs-warning); }
            .text-success { color: var(--bs-success); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Polymarket Pipeline Flow Diagram</h1>
            
            <div class="pipeline-description">
                <p>This diagram illustrates the complete workflow of our Polymarket Pipeline system, from market data extraction through approval to integration with ApeChain for deployment.</p>
            </div>
            
            <div>
                <h2>Pipeline Visual Flow</h2>
                <div id="text-flow-diagram">
                    <h3>Pipeline Process Flow:</h3>
                    <ol class="pipeline-steps">
                        <li><span class="text-info">Fetch Diverse Markets</span> from Polymarket API across multiple categories</li>
                        <li><span class="text-info">Filter Active Markets</span> using expiration date and asset validation</li>
                        <li><span class="text-info">Track Markets</span> in PostgreSQL database to prevent duplicates</li>
                        <li><span class="text-warning">Post New Markets to Slack</span> for approval</li>
                        <li><span class="text-warning">Check Market Approvals</span> from Slack reactions (✅/❌)</li>
                        <li><span class="text-info">Update Database</span> with approval status</li>
                        <li><span class="text-success">Create Market Records</span> for approved markets</li>
                        <li><span class="text-warning">Post Markets for Deployment Approval</span> - final QA check</li>
                        <li><span class="text-warning">Check Deployment Approvals</span> from Slack reactions</li>
                        <li><span class="text-success">Deploy to ApeChain</span> smart contract with frontend mapping</li>
                    </ol>
                </div>
                
                <div>
                    <h3>Database Structure</h3>
                    <p>The system uses two primary tables in our PostgreSQL database:</p>
                    
                    <div style="text-align: left; width: fit-content; margin: 20px auto;">
                        <h4 class="text-info">ProcessedMarket Table</h4>
                        <ul style="text-align: left;">
                            <li><b>condition_id</b> - Unique identifier from Polymarket (PK)</li>
                            <li><b>question</b> - Market question text</li>
                            <li><b>first_seen</b> - When the market was first discovered</li>
                            <li><b>posted</b> - Whether posted to Slack (boolean)</li> 
                            <li><b>message_id</b> - Slack message ID for tracking</li>
                            <li><b>approved</b> - Market approval status (boolean or null)</li>
                            <li><b>raw_data</b> - Original data from Polymarket API</li>
                        </ul>
                        
                        <h4 class="text-success">Market Table</h4>
                        <ul style="text-align: left;">
                            <li><b>id</b> - Primary key, matches condition_id</li>
                            <li><b>question</b> - Market question text</li> 
                            <li><b>type</b> - Market type (binary, etc.)</li>
                            <li><b>category</b> - Market category for diversity tracking</li>
                            <li><b>expiry</b> - Market expiration timestamp</li>
                            <li><b>status</b> - Processing status</li>
                            <li><b>icon_url</b> - URL for frontend icon display</li>
                            <li><b>apechain_market_id</b> - ID on ApeChain</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <a href="/" class="btn">Back to Pipeline Control Panel</a>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/pending-markets')
def pending_markets():
    """Show the pending markets with their categories."""
    # Import here to avoid circular imports
    from models import ApprovalLog, PendingMarket
    TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pending Markets</title>
        <link rel="stylesheet" href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background-color: var(--bs-dark);
                color: var(--bs-light);
            }
            h1, h2, h3 {
                color: var(--bs-light);
                text-align: center;
                margin-bottom: 30px;
            }
            .container {
                background-color: var(--bs-dark-bg-subtle);
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px 15px;
                text-align: left;
                border-bottom: 1px solid var(--bs-border-color);
            }
            th {
                background-color: var(--bs-dark);
                font-weight: bold;
            }
            tr:hover {
                background-color: rgba(255, 255, 255, 0.05);
            }
            .badge {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 50px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                margin-right: 5px;
            }
            .badge-politics { background-color: #9C27B0; color: white; }
            .badge-crypto { background-color: #FF9800; color: black; }
            .badge-sports { background-color: #4CAF50; color: white; }
            .badge-business { background-color: #2196F3; color: white; }
            .badge-culture { background-color: #E91E63; color: white; }
            .badge-news { background-color: #795548; color: white; }
            .badge-tech { background-color: #607D8B; color: white; }
            .badge-all { background-color: #9E9E9E; color: white; }
            .button {
                background-color: var(--bs-primary);
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                text-decoration: none;
                display: inline-block;
                margin-top: 20px;
            }
            .status-info {
                background-color: var(--bs-dark);
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Pending Markets</h1>
            
            <div class="status-info">
                <h3>Markets Awaiting Approval</h3>
                <p>These markets have been categorized by GPT-4o-mini and are waiting for human approval in Slack.</p>
                <p>Total pending markets: <strong>{{ markets|length }}</strong></p>
                <a href="/" class="button">Back to Pipeline Dashboard</a>
            </div>
            
            {% if markets %}
                <table>
                    <thead>
                        <tr>
                            <th>Question</th>
                            <th>Category</th>
                            <th>Options</th>
                            <th>Posted to Slack</th>
                            <th>Fetched</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for market in markets %}
                            <tr>
                                <td>{{ market.question }}</td>
                                <td>
                                    <span class="badge badge-{{ market.category }}">
                                        {{ market.category }}
                                    </span>
                                </td>
                                <td>
                                    {% if market.options %}
                                        {% set options = market.options|tojson|safe %}
                                        {{ options }}
                                    {% else %}
                                        Yes/No
                                    {% endif %}
                                </td>
                                <td>{{ "Yes" if market.slack_message_id else "No" }}</td>
                                <td>{{ market.fetched_at.strftime('%Y-%m-%d %H:%M') }}</td>
                            </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <div class="alert alert-info">
                    <p>No pending markets found. Run the pipeline to fetch and categorize new markets.</p>
                </div>
            {% endif %}
        </div>
    </body>
    </html>
    """
    
    with app.app_context():
        # First, get IDs of markets that have been rejected
        rejected_ids = [
            log.poly_id for log in ApprovalLog.query.filter_by(decision='rejected').all()
        ]
        
        # Get all pending markets that haven't been rejected
        if rejected_ids:
            pending_markets = PendingMarket.query.filter(
                ~PendingMarket.poly_id.in_(rejected_ids)
            ).all()
        else:
            pending_markets = PendingMarket.query.all()
        
    return render_template_string(TEMPLATE, markets=pending_markets)

# This allows running the script directly
if __name__ == "__main__":
    # If running directly, start the pipeline
    pipeline = PolymarketPipeline()
    exit_code = pipeline.run()
    sys.exit(exit_code)