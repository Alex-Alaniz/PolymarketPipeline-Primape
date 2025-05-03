#!/usr/bin/env python3
"""
Entry point for the Polymarket pipeline.
This file allows running the pipeline via the web interface workflow.

Steps in the pipeline:
1. Fetch Polymarket data using transform_polymarket_data_capitalized.py
2. Post markets to Slack/Discord for initial approval
3. Generate banner images for approved markets using OpenAI
4. Post markets with banners to Slack/Discord for final approval
5. Deploy approved markets (push banner to frontend repo & create market on ApeChain)
6. Generate summary reports and logs
"""
from flask import Flask, jsonify, request, render_template_string
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
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .status-box {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .log-container {
            max-height: 300px;
            overflow-y: auto;
            padding: 10px;
            background-color: #222;
            color: #f0f0f0;
            font-family: monospace;
            border-radius: 4px;
            margin: 20px 0;
        }
        .log-line {
            margin: 2px 0;
            word-wrap: break-word;
        }
        .button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .button:hover {
            background-color: #45a049;
        }
        .button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .info {
            margin: 15px 0;
            padding: 10px;
            background-color: #e7f3fe;
            border-left: 6px solid #2196F3;
        }
    </style>
</head>
<body>
    <h1>Polymarket Pipeline Control Panel</h1>
    
    <div class="container">
        <div class="status-box">
            <h2>Pipeline Status: <span id="status">{{ status.status }}</span></h2>
            {% if status.running %}
                <p>Running since: {{ status.start_time }}</p>
                <p>Last message: {{ status.last_message }}</p>
            {% elif status.end_time %}
                <p>Last run: {{ status.start_time }} to {{ status.end_time }}</p>
                <p>Status: {{ status.status }}</p>
            {% else %}
                <p>Pipeline is idle</p>
            {% endif %}
        </div>
        
        <div>
            <button id="run-pipeline" class="button" {% if status.running %}disabled{% endif %} onclick="runPipeline()">Run Pipeline</button>
        </div>
        
        <div class="info">
            <p>This application runs the Polymarket Pipeline, automating the process of:</p>
            <ol>
                <li>Extracting Polymarket data</li>
                <li>AI-powered market trend prediction preview</li>
                <li>Facilitating two-stage approvals via Slack</li>
                <li>Generating banner images with OpenAI</li>
                <li>Deploying approved markets to ApeChain</li>
            </ol>
        </div>
        
        <!-- Market Trend Prediction Section -->
        <div style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
            <h3>AI-Powered Market Trend Prediction</h3>
            <p>Generate AI-powered trend predictions and insights for a market.</p>
            
            <div style="margin-bottom: 15px;">
                <input type="text" id="market-id" placeholder="Market ID" style="padding: 8px; width: 200px;">
                <input type="text" id="market-question" placeholder="Market Question" style="padding: 8px; width: 400px; margin-left: 10px;">
            </div>
            
            <div style="margin-bottom: 15px;">
                <select id="market-category" style="padding: 8px; width: 200px;">
                    <option value="Politics">Politics</option>
                    <option value="Crypto">Crypto</option>
                    <option value="Sports">Sports</option>
                    <option value="Entertainment">Entertainment</option>
                    <option value="Finance">Finance</option>
                    <option value="Science">Science</option>
                    <option value="Other">Other</option>
                </select>
                
                <button id="generate-prediction" class="button" style="margin-left: 10px;" onclick="generatePrediction()">Generate Prediction</button>
            </div>
            
            <div id="prediction-result" style="margin-top: 20px; display: none; padding: 15px; border: 1px solid #ddd; border-radius: 4px; background-color: #f9f9f9;">
                <h4>Market Trend Prediction Results</h4>
                <div id="prediction-content"></div>
            </div>
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
        
        // Refresh the page every 5 seconds if the pipeline is running
        {% if status.running %}
        setTimeout(() => {
            window.location.reload();
        }, 5000);
        {% endif %}
        
        function generatePrediction() {
            // Get form values
            const marketId = document.getElementById('market-id').value;
            const marketQuestion = document.getElementById('market-question').value;
            const marketCategory = document.getElementById('market-category').value;
            
            // Validate input
            if (!marketId || !marketQuestion) {
                alert('Please enter both Market ID and Market Question');
                return;
            }
            
            // Prepare market data
            const marketData = {
                id: marketId,
                question: marketQuestion,
                category: marketCategory
            };
            
            // Show loading indicator
            const resultDiv = document.getElementById('prediction-result');
            const contentDiv = document.getElementById('prediction-content');
            resultDiv.style.display = 'block';
            contentDiv.innerHTML = '<p>Generating AI prediction, please wait... (this may take 15-30 seconds)</p>';
            
            // Call API
            fetch('/market-trend-prediction', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(marketData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Format prediction result
                    const prediction = data.prediction;
                    let html = '<div style="color: #333;">';
                    
                    html += `<div style="margin-bottom: 15px;">
                        <strong>Market:</strong> ${prediction.market_question}<br>
                        <strong>Generated at:</strong> ${prediction.generated_at}<br>
                        <strong>Based on:</strong> ${prediction.based_on_markets} historical markets
                    </div>`;
                    
                    html += `<div style="display: flex; flex-wrap: wrap; gap: 20px;">
                        <div style="flex: 1; min-width: 200px; padding: 15px; background-color: #f0f8ff; border-radius: 4px; border-left: 4px solid #4682b4;">
                            <h4 style="margin-top: 0;">Market Interest</h4>
                            <p><strong>Level:</strong> <span style="color: ${prediction.interest_level === 'high' ? '#2e8b57' : (prediction.interest_level === 'medium' ? '#daa520' : '#cd5c5c')};">${prediction.interest_level.toUpperCase()}</span></p>
                            <p><strong>Reasoning:</strong> ${prediction.interest_reasoning}</p>
                        </div>
                        
                        <div style="flex: 1; min-width: 200px; padding: 15px; background-color: #fff8e1; border-radius: 4px; border-left: 4px solid #ffa000;">
                            <h4 style="margin-top: 0;">Volume Prediction</h4>
                            <p><strong>Level:</strong> <span style="color: ${prediction.volume_prediction === 'high' ? '#2e8b57' : (prediction.volume_prediction === 'medium' ? '#daa520' : '#cd5c5c')};">${prediction.volume_prediction.toUpperCase()}</span></p>
                            <p><strong>Strategic Timing:</strong> ${prediction.strategic_timing}</p>
                        </div>
                    </div>`;
                    
                    // Historical context and volatility
                    html += `<div style="margin-top: 20px;">
                        <h4>Historical Context</h4>
                        <ul>
                            ${prediction.historical_context.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                        
                        <h4>Volatility Factors</h4>
                        <ul>
                            ${prediction.volatility_factors.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>`;
                    
                    html += '</div>';
                    contentDiv.innerHTML = html;
                } else {
                    // Show error
                    contentDiv.innerHTML = `<p style="color: #cc0000;">Error: ${data.error}</p>`;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                contentDiv.innerHTML = `<p style="color: #cc0000;">Error: Failed to generate prediction. Please try again.</p>`;
            });
        }
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

@app.route('/market-trend-prediction', methods=['POST'])
def predict_market_trend():
    """API endpoint to generate AI-powered market trend prediction"""
    try:
        # Get market details from request
        data = request.get_json()
        if not data:
            return jsonify({
                "error": "No market data provided"
            }), 400
            
        # Extract market data
        market_id = data.get('id')
        market_question = data.get('question')
        
        if not market_id or not market_question:
            return jsonify({
                "error": "Market ID and question are required"
            }), 400
        
        # Initialize trend predictor
        from utils.trend_prediction import MarketTrendPredictor
        trend_predictor = MarketTrendPredictor()
        
        # Generate prediction
        prediction = trend_predictor.generate_trend_preview(data)
        
        if prediction and 'error' not in prediction:
            return jsonify({
                "success": True,
                "market_id": market_id,
                "prediction": prediction
            })
        else:
            error_msg = prediction.get('error', 'Unknown error')
            return jsonify({
                "success": False,
                "market_id": market_id,
                "error": error_msg
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# This allows running the script directly
if __name__ == "__main__":
    # If running directly, start the pipeline
    pipeline = PolymarketPipeline()
    exit_code = pipeline.run()
    sys.exit(exit_code)