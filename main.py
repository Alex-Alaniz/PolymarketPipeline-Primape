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
from models import db, Market, ApprovalEvent, PipelineRun

# Create Flask app
app = Flask(__name__)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database with app
db.init_app(app)

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
            <button id="run-pipeline" class="button" {% if status.running %}disabled{% endif %} onclick="runPipeline()">Run Pipeline</button>
            <button id="check-approvals" class="button" style="background-color: var(--bs-success); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="checkMarketApprovals()">Check Market Approvals</button>
            <button id="run-deployment" class="button" style="background-color: var(--bs-warning); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="runDeploymentApprovals()">Check Deployment Approvals</button>
            <button id="sync-slack-db" class="button" style="background-color: var(--bs-info); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="syncSlackDb()">Sync Slack & DB</button>
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
        function runPipeline() {
            fetch('/run-pipeline', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = 'running';
                    document.getElementById('run-pipeline').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to start pipeline: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while starting the pipeline');
            });
        }
        
        function checkMarketApprovals() {
            fetch('/check-market-approvals', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = 'running';
                    document.getElementById('run-pipeline').disabled = true;
                    document.getElementById('check-approvals').disabled = true;
                    document.getElementById('run-deployment').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to start market approval check: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while checking market approvals');
            });
        }
        
        function runDeploymentApprovals() {
            fetch('/run-deployment-approvals', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = 'running';
                    document.getElementById('run-pipeline').disabled = true;
                    document.getElementById('check-approvals').disabled = true;
                    document.getElementById('run-deployment').disabled = true;
                    document.getElementById('sync-slack-db').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to start deployment approval process: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while starting the deployment approval process');
            });
        }
        
        function syncSlackDb() {
            fetch('/sync-slack-db', {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = 'running';
                    document.getElementById('run-pipeline').disabled = true;
                    document.getElementById('check-approvals').disabled = true;
                    document.getElementById('run-deployment').disabled = true;
                    document.getElementById('sync-slack-db').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to start Slack-DB synchronization: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while synchronizing Slack and database');
            });
        }
        
        // Refresh the page every 5 seconds if the pipeline is running
        {% if status.running %}
        setTimeout(() => {
            window.location.reload();
        }, 5000);
        {% endif %}
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
                synced, updated, cleaned = sync_slack_db.main()
                print(f"Synchronization complete: {synced} synced, {updated} updated, {cleaned} cleaned")
            
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

# This allows running the script directly
if __name__ == "__main__":
    # If running directly, start the pipeline
    pipeline = PolymarketPipeline()
    exit_code = pipeline.run()
    sys.exit(exit_code)