"""
Main Flask application for the Polymarket Pipeline.

This version is updated to support the event-based model,
with proper tracking of events, market IDs, and image URLs.
"""

import os
import sys
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from flask import Flask, request, jsonify, redirect, url_for, render_template_string
from models_updated import db, Event, Market, PendingMarket, ProcessedMarket, PipelineRun, ApprovalEvent

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Global status dictionary to track pipeline state
pipeline_status = {
    "running": False,
    "status": "idle",
    "start_time": None,
    "end_time": None,
    "last_message": None,
    "log_messages": []
}

# HTML template for the main page
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Polymarket Pipeline</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bs-primary: #0d6efd;
            --bs-secondary: #6c757d;
            --bs-success: #198754;
            --bs-info: #0dcaf0;
            --bs-warning: #ffc107;
            --bs-danger: #dc3545;
            --bs-purple: #6f42c1;
            --bs-indigo: #6610f2;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        
        .status-container {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        
        .status-badge {
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin-left: 10px;
        }
        
        .status-idle {
            background-color: #e9ecef;
            color: #495057;
        }
        
        .status-running {
            background-color: #cfe2ff;
            color: #0a58ca;
        }
        
        .status-completed {
            background-color: #d1e7dd;
            color: #0f5132;
        }
        
        .status-failed {
            background-color: #f8d7da;
            color: #842029;
        }
        
        .button {
            display: inline-block;
            padding: 10px 15px;
            background-color: #0d6efd;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.3s;
        }
        
        .button:hover {
            background-color: #0b5ed7;
        }
        
        .button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        
        .log-container {
            background-color: #212529;
            color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            margin-top: 20px;
        }
        
        .log-line {
            margin: 0;
            padding: 2px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .info {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .info p {
            margin-bottom: 10px;
        }
        
        .info ol li, .info ul li {
            margin-bottom: 8px;
        }
        
        .alert {
            margin-top: 15px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            grid-gap: 15px;
            margin-top: 20px;
        }
        
        .stat-card {
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .stat-label {
            color: #6c757d;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }
        
        h3 {
            margin-top: 30px;
            margin-bottom: 15px;
            color: #495057;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Polymarket Pipeline Dashboard</h1>
        
        <div class="status-container">
            <h2>Pipeline Status: 
                <span id="status" class="status-badge status-{{ status.status }}">{{ status.status }}</span>
            </h2>
            {% if status.start_time %}
            <p><strong>Started:</strong> {{ status.start_time }}</p>
            {% endif %}
            {% if status.end_time %}
            <p><strong>Completed:</strong> {{ status.end_time }}</p>
            {% endif %}
            {% if status.last_message %}
            <p><strong>Last Message:</strong> {{ status.last_message }}</p>
            {% endif %}
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Events</div>
                <div class="stat-value">{{ stats.event_count }}</div>
                <div>Unique event categories</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Markets</div>
                <div class="stat-value">{{ stats.market_count }}</div>
                <div>Total markets in system</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pending Markets</div>
                <div class="stat-value">{{ stats.pending_count }}</div>
                <div>Awaiting approval</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Deployed Markets</div>
                <div class="stat-value">{{ stats.deployed_count }}</div>
                <div>Successfully deployed</div>
            </div>
        </div>
        
        <div>
            <button id="run-pipeline" class="button" {% if status.running %}disabled{% endif %} onclick="runPipeline()">Run Pipeline</button>
            <button id="check-approvals" class="button" style="background-color: var(--bs-success); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="checkMarketApprovals()">Check Market Approvals</button>
            <button id="post-unposted" class="button" style="background-color: var(--bs-purple); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="postUnpostedMarkets()">Post Next Batch</button>
            <button id="post-unposted-pending" class="button" style="background-color: var(--bs-indigo); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="postUnpostedPendingMarkets()">Post Pending Batch</button>
            <button id="flush-unposted" class="button" style="background-color: var(--bs-danger); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="flushUnpostedMarkets()">Flush Unposted Markets</button>
            <button id="run-deployment" class="button" style="background-color: var(--bs-warning); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="runDeploymentApprovals()">Check Deployment Approvals</button>
            <button id="sync-slack-db" class="button" style="background-color: var(--bs-info); margin-left: 10px;" {% if status.running %}disabled{% endif %} onclick="syncSlackDb()">Sync Slack & DB</button>
            <a href="/pipeline-flow" class="button" style="background-color: var(--bs-secondary); margin-left: 10px; text-decoration: none;">View Pipeline Flow</a>
        </div>
        
        <div class="info">
            <p>This application runs the Polymarket Pipeline, automating the process of:</p>
            <ol>
                <li>Fetching diverse markets from Polymarket API across multiple categories</li>
                <li>Extracting events and categorizing markets with AI assistance</li>
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
                    document.getElementById('sync-slack-db').disabled = true;
                    document.getElementById('post-unposted').disabled = true;
                    document.getElementById('post-unposted-pending').disabled = true;
                    document.getElementById('flush-unposted').disabled = true;
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
                    document.getElementById('post-unposted').disabled = true;
                    document.getElementById('post-unposted-pending').disabled = true;
                    document.getElementById('flush-unposted').disabled = true;
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
                    document.getElementById('post-unposted').disabled = true;
                    document.getElementById('post-unposted-pending').disabled = true;
                    document.getElementById('flush-unposted').disabled = true;
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
        
        function postUnpostedMarkets() {
            fetch('/post-unposted-markets', {
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
                    document.getElementById('post-unposted').disabled = true;
                    document.getElementById('post-unposted-pending').disabled = true;
                    document.getElementById('flush-unposted').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to post unposted markets: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while posting unposted markets');
            });
        }
        
        function postUnpostedPendingMarkets() {
            fetch('/post-unposted-pending-markets', {
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
                    document.getElementById('post-unposted').disabled = true;
                    document.getElementById('post-unposted-pending').disabled = true;
                    document.getElementById('flush-unposted').disabled = true;
                    // Refresh page after 2 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    alert('Failed to post unposted pending markets: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while posting unposted pending markets');
            });
        }
        
        function flushUnpostedMarkets() {
            if (confirm("WARNING: This will delete all unposted markets from the database. This action cannot be undone. Markets already posted to Slack will be preserved.\n\nDo you want to continue?")) {
                fetch('/flush-unposted-markets', {
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
                        document.getElementById('post-unposted').disabled = true;
                        document.getElementById('post-unposted-pending').disabled = true;
                        document.getElementById('flush-unposted').disabled = true;
                        // Refresh page after 2 seconds
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    } else {
                        alert('Failed to flush unposted markets: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while flushing unposted markets');
                });
            }
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
        
        # Import the run_pipeline_with_events module
        from run_pipeline_with_events import run_pipeline as run_event_pipeline
        
        # Run the pipeline
        exit_code = run_event_pipeline(max_markets=20)
        
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

def get_database_stats():
    """Get statistics from the database for display in the UI"""
    with app.app_context():
        event_count = db.session.query(Event).count()
        market_count = db.session.query(Market).count()
        pending_count = db.session.query(PendingMarket).count()
        deployed_count = db.session.query(Market).filter(Market.apechain_market_id != None).count()
        
        return {
            "event_count": event_count,
            "market_count": market_count,
            "pending_count": pending_count,
            "deployed_count": deployed_count
        }

@app.route('/')
def index():
    """Main page"""
    return render_template_string(
        HTML_TEMPLATE, 
        status=pipeline_status,
        stats=get_database_stats()
    )

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

@app.route('/check-market-approvals', methods=['POST'])
def start_market_approvals():
    """API endpoint to check for market approvals"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Pipeline is already running"
        })
    
    # Define a function to run the market approvals check
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
            print("Starting Market Approval Check...")
            
            # Import the market approval modules
            import check_market_approvals
            
            # Run the market approval process
            with app.app_context():
                pending, approved, rejected = check_market_approvals.check_market_approvals()
                print(f"Market approval results: {pending} pending, {approved} approved, {rejected} rejected")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed"
            
            # Log process end
            print("Market approval check completed successfully")
            
        except Exception as e:
            # Log any exceptions
            error_message = str(e)
            print(f"Market approval check failed with exception: {error_message}")
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "failed"
        
        finally:
            # Restore stdout and stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    # Start the market approval check in a separate thread
    thread = threading.Thread(target=run_market_approvals)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Market approval check started"
    })

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
            print("Starting to post unposted markets...")
            
            # Import the post_unposted_markets module
            import post_unposted_markets
            
            # Run the posting process
            with app.app_context():
                result = post_unposted_markets.main()
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print(f"Post unposted markets process {pipeline_status['status']}")
            
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
    
    # Start the posting process in a separate thread
    thread = threading.Thread(target=run_post_unposted_markets)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Post unposted markets process started"
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
            print("Starting to post unposted pending markets...")
            
            # Import the post_unposted_pending_markets module
            import post_unposted_pending_markets
            
            # Run the posting process
            with app.app_context():
                result = post_unposted_pending_markets.main()
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print(f"Post unposted pending markets process {pipeline_status['status']}")
            
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
    
    # Start the posting process in a separate thread
    thread = threading.Thread(target=run_post_unposted_pending_markets)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Post unposted pending markets process started"
    })

@app.route('/flush-unposted-markets', methods=['POST'])
def flush_unposted_markets():
    """API endpoint to flush all unposted markets from the database"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to run the flush unposted markets process
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
            print("Starting to flush unposted markets...")
            
            # Import the flush_unposted_markets module
            import flush_unposted_markets
            
            # Run the flush process
            with app.app_context():
                result = flush_unposted_markets.main()
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print(f"Flush unposted markets process {pipeline_status['status']}")
            
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
    
    # Start the flush process in a separate thread
    thread = threading.Thread(target=run_flush_unposted_markets)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Flush unposted markets process started"
    })

@app.route('/sync-slack-db', methods=['POST'])
def sync_slack_db():
    """API endpoint to synchronize Slack reactions with the database"""
    if pipeline_status["running"]:
        return jsonify({
            "success": False,
            "message": "Another process is already running"
        })
    
    # Define a function to run the Slack-DB synchronization
    def run_sync_slack_db():
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
            print("Starting Slack-DB synchronization...")
            
            # Import the sync_slack_db module
            import sync_slack_db
            
            # Run the synchronization
            with app.app_context():
                result = sync_slack_db.main()
            
            # Update UI status
            pipeline_status["running"] = False
            pipeline_status["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pipeline_status["status"] = "completed" if result == 0 else "failed"
            
            # Log process end
            print(f"Slack-DB synchronization {pipeline_status['status']}")
            
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
    
    # Start the synchronization in a separate thread
    thread = threading.Thread(target=run_sync_slack_db)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Slack-DB synchronization started"
    })

@app.route('/pipeline-flow')
def pipeline_flow():
    """Show the pipeline flow diagram"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Polymarket Pipeline Flow</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
            }
            
            h1 {
                margin-bottom: 20px;
            }
            
            .flow-container {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            
            .flow-diagram {
                max-width: 100%;
                margin: 20px 0;
            }
            
            .back-button {
                display: inline-block;
                padding: 10px 15px;
                background-color: #0d6efd;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back-button">← Back to Dashboard</a>
        
        <h1>Polymarket Pipeline Flow</h1>
        
        <div class="flow-container">
            <img src="/static/pipeline_flow.png" alt="Pipeline Flow Diagram" class="flow-diagram">
            
            <h2>Pipeline Process Details</h2>
            <ol>
                <li><strong>Fetch Markets:</strong> Retrieve market data from Polymarket API</li>
                <li><strong>Extract Events:</strong> Identify events from market questions</li>
                <li><strong>Categorize:</strong> Use AI to categorize markets into predefined categories</li>
                <li><strong>Store in Database:</strong> Save market and event data with proper relationships</li>
                <li><strong>Post to Slack:</strong> Send markets for human approval with category badges</li>
                <li><strong>Process Approvals:</strong> Handle approval/rejection decisions</li>
                <li><strong>Generate Images:</strong> Create banner images for approved markets</li>
                <li><strong>Deploy to Blockchain:</strong> Deploy approved markets to ApeChain</li>
                <li><strong>Update Frontend:</strong> Add mapping entries for frontend rendering</li>
            </ol>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Start the Flask app
    app.run(debug=True, host="0.0.0.0")