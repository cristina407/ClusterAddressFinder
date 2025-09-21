"""
STANDALONE CLUSTER ADDRESS FINDER WEB APP
==========================================
A complete web application for finding street addresses from coordinates

INSTALLATION INSTRUCTIONS:
--------------------------
1. Install Python (if not already installed): https://www.python.org/downloads/
2. Open Command Prompt (Windows) or Terminal (Mac/Linux)
3. Install required packages:
   pip install flask pandas openpyxl geopy werkzeug

4. Save this file as: cluster_app.py
5. Run the app:
   python cluster_app.py

6. Open your browser and go to:
   http://localhost:5000

The app will run locally on your computer and can be used repeatedly!
"""

from flask import Flask, render_template, request, send_file, jsonify, session
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import os
import time
from datetime import datetime
from werkzeug.utils import secure_filename
import tempfile
import json
import threading
import queue

# Create Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Global variables for processing status
processing_status = {}
results_storage = {}

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cluster Address Finder</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        
        .upload-section {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            transition: all 0.3s ease;
            margin-bottom: 30px;
        }
        
        .upload-section:hover {
            border-color: #667eea;
            background: #f0f3ff;
        }
        
        .upload-section.dragging {
            border-color: #764ba2;
            background: #e8ebff;
        }
        
        input[type="file"] {
            display: none;
        }
        
        .upload-button {
            display: inline-block;
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: transform 0.2s;
        }
        
        .upload-button:hover {
            transform: translateY(-2px);
        }
        
        .file-info {
            margin-top: 20px;
            padding: 15px;
            background: #e7f3ff;
            border-radius: 8px;
            display: none;
        }
        
        .file-info.show {
            display: block;
        }
        
        .button {
            padding: 12px 30px;
            margin: 10px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .button-primary {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
        }
        
        .button-success {
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
        }
        
        .button-secondary {
            background: linear-gradient(135deg, #6c757d, #495057);
            color: white;
        }
        
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        
        .button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .progress-section {
            display: none;
            margin: 30px 0;
        }
        
        .progress-section.show {
            display: block;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 15px;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        
        .status-message {
            text-align: center;
            margin-top: 15px;
            padding: 15px;
            border-radius: 8px;
            display: none;
        }
        
        .status-message.show {
            display: block;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .results-section {
            display: none;
            margin-top: 30px;
        }
        
        .results-section.show {
            display: block;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        
        .sample-results {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .sample-results h3 {
            margin-bottom: 15px;
            color: #333;
        }
        
        .address-item {
            padding: 10px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }
        
        .controls {
            text-align: center;
            margin-top: 30px;
            padding-top: 30px;
            border-top: 1px solid #dee2e6;
        }
        
        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        th {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 10px;
            text-align: left;
        }
        
        td {
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
        }
        
        .mode-selector {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
        }
        
        .mode-option {
            padding: 15px 25px;
            border: 2px solid #dee2e6;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .mode-option:hover {
            border-color: #667eea;
            background: #f0f3ff;
        }
        
        .mode-option.selected {
            border-color: #667eea;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1));
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🗺️ Cluster Address Finder</h1>
        <p class="subtitle">Convert coordinates to street addresses - Works offline, no API key needed!</p>
        
        <div class="upload-section" id="uploadSection">
            <div style="font-size: 3em; margin-bottom: 20px;">📁</div>
            <p style="margin-bottom: 20px;">Drop your Excel file here or click to browse</p>
            <label for="fileInput" class="upload-button">Choose File</label>
            <input type="file" id="fileInput" accept=".xlsx,.xls" />
            <div class="file-info" id="fileInfo"></div>
        </div>
        
        <div class="mode-selector" id="modeSelector" style="display: none;">
            <div class="mode-option selected" data-mode="test">
                <strong>Test Mode</strong><br>
                <small>Process first 5 rows</small>
            </div>
            <div class="mode-option" data-mode="full">
                <strong>Full Processing</strong><br>
                <small>Process all rows</small>
            </div>
        </div>
        
        <div class="progress-section" id="progressSection">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="status-message" id="statusMessage"></div>
        </div>
        
        <div class="results-section" id="resultsSection">
            <h2>📊 Results Summary</h2>
            <div class="stats-grid" id="statsGrid"></div>
            <div class="sample-results" id="sampleResults"></div>
        </div>
        
        <div class="controls">
            <button class="button button-primary" id="processBtn" onclick="processFile()" style="display: none;">
                🔍 Find Addresses
            </button>
            <button class="button button-success" id="downloadBtn" onclick="downloadResults()" style="display: none;">
                📥 Download Results
            </button>
            <button class="button button-secondary" onclick="resetApp()">
                🔄 Start Over
            </button>
        </div>
    </div>
    
    <script>
        let uploadedFile = null;
        let processingMode = 'test';
        let sessionId = null;
        
        // File upload handling
        const uploadSection = document.getElementById('uploadSection');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        
        uploadSection.addEventListener('click', () => fileInput.click());
        
        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('dragging');
        });
        
        uploadSection.addEventListener('dragleave', () => {
            uploadSection.classList.remove('dragging');
        });
        
        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragging');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });
        
        // Mode selection
        document.querySelectorAll('.mode-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.mode-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
                processingMode = option.dataset.mode;
            });
        });
        
        function handleFile(file) {
            if (!file.name.match(/\.(xlsx|xls)$/)) {
                alert('Please upload an Excel file (.xlsx or .xls)');
                return;
            }
            
            uploadedFile = file;
            fileInfo.innerHTML = `
                <strong>File:</strong> ${file.name}<br>
                <strong>Size:</strong> ${(file.size / 1024).toFixed(2)} KB<br>
                <strong>Ready to process!</strong>
            `;
            fileInfo.classList.add('show');
            document.getElementById('modeSelector').style.display = 'flex';
            document.getElementById('processBtn').style.display = 'inline-block';
        }
        
        async function processFile() {
            if (!uploadedFile) {
                alert('Please select a file first');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', uploadedFile);
            formData.append('mode', processingMode);
            
            const processBtn = document.getElementById('processBtn');
            processBtn.disabled = true;
            processBtn.innerHTML = '🔍 Processing... <span class="loading-spinner"></span>';
            
            document.getElementById('progressSection').classList.add('show');
            document.getElementById('resultsSection').classList.remove('show');
            
            try {
                // Upload and start processing
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showStatus('error', data.error);
                    processBtn.disabled = false;
                    processBtn.innerHTML = '🔍 Find Addresses';
                    return;
                }
                
                sessionId = data.session_id;
                showStatus('info', `Processing ${data.total_rows} locations...`);
                
                // Start monitoring progress
                monitorProgress();
                
            } catch (error) {
                showStatus('error', 'Error uploading file: ' + error.message);
                processBtn.disabled = false;
                processBtn.innerHTML = '🔍 Find Addresses';
            }
        }
        
        async function monitorProgress() {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/progress/${sessionId}`);
                    const data = await response.json();
                    
                    // Update progress bar
                    const progress = (data.processed / data.total) * 100;
                    document.getElementById('progressFill').style.width = progress + '%';
                    document.getElementById('progressFill').textContent = Math.round(progress) + '%';
                    
                    if (data.status === 'completed') {
                        clearInterval(interval);
                        showResults(data.results);
                        document.getElementById('processBtn').disabled = false;
                        document.getElementById('processBtn').innerHTML = '🔍 Find Addresses';
                        showStatus('success', 'Processing complete!');
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        showStatus('error', 'Processing error: ' + data.message);
                        document.getElementById('processBtn').disabled = false;
                        document.getElementById('processBtn').innerHTML = '🔍 Find Addresses';
                    }
                } catch (error) {
                    console.error('Progress monitoring error:', error);
                }
            }, 1000);
        }
        
        function showResults(results) {
            document.getElementById('resultsSection').classList.add('show');
            
            // Show statistics
            const statsGrid = document.getElementById('statsGrid');
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${results.stats.complete_address}</div>
                    <div class="stat-label">Complete Addresses</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${results.stats.street_only}</div>
                    <div class="stat-label">Street Only</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${results.stats.area_only}</div>
                    <div class="stat-label">Area Only</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${results.stats.total}</div>
                    <div class="stat-label">Total Processed</div>
                </div>
            `;
            
            // Show sample addresses
            if (results.sample_addresses && results.sample_addresses.length > 0) {
                const sampleResults = document.getElementById('sampleResults');
                sampleResults.innerHTML = '<h3>Sample Addresses Found:</h3>';
                results.sample_addresses.forEach(addr => {
                    sampleResults.innerHTML += `
                        <div class="address-item">
                            <strong>📍</strong> ${addr}
                        </div>
                    `;
                });
            }
            
            document.getElementById('downloadBtn').style.display = 'inline-block';
        }
        
        async function downloadResults() {
            if (!sessionId) {
                alert('No results to download');
                return;
            }
            
            window.location.href = `/download/${sessionId}`;
        }
        
        function showStatus(type, message) {
            const statusMessage = document.getElementById('statusMessage');
            statusMessage.className = 'status-message show status-' + type;
            statusMessage.textContent = message;
        }
        
        function resetApp() {
            location.reload();
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main page"""
    return HTML_TEMPLATE

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and start processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        mode = request.form.get('mode', 'test')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Read the file
        df = pd.read_excel(filepath)
        
        # Validate required columns
        required_cols = ['Center_Latitude', 'Center_Longitude']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            os.remove(filepath)
            return jsonify({'error': f'Missing required columns: {missing_cols}'}), 400
        
        # Generate session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        # Determine number of rows to process
        if mode == 'test':
            rows_to_process = min(5, len(df))
        else:
            rows_to_process = len(df)
        
        # Initialize processing status
        processing_status[session_id] = {
            'status': 'processing',
            'total': rows_to_process,
            'processed': 0,
            'results': None
        }
        
        # Start processing in background thread
        thread = threading.Thread(
            target=process_addresses,
            args=(df, session_id, rows_to_process)
        )
        thread.start()
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'session_id': session_id,
            'total_rows': rows_to_process,
            'mode': mode
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_addresses(df, session_id, rows_to_process):
    """Process addresses in background"""
    try:
        # Limit dataframe to rows to process
        working_df = df.head(rows_to_process).copy()
        
        # Initialize geocoder
        geolocator = Nominatim(user_agent=f"cluster_finder_{session_id}", timeout=10)
        geocode = RateLimiter(
            geolocator.reverse,
            min_delay_seconds=1.0,
            return_value_on_exception=None
        )
        
        # Add result columns
        working_df['Physical_Address'] = ''
        working_df['Street_Name'] = ''
        working_df['Address_Quality'] = ''
        
        # Statistics
        stats = {
            'complete_address': 0,
            'street_only': 0,
            'area_only': 0,
            'coordinates_only': 0,
            'total': rows_to_process
        }
        
        sample_addresses = []
        
        # Process each row
        for idx, row in working_df.iterrows():
            lat = row['Center_Latitude']
            lon = row['Center_Longitude']
            
            try:
                if pd.notna(lat) and pd.notna(lon):
                    # Get address from coordinates
                    location = geocode(
                        (lat, lon),
                        exactly_one=True,
                        zoom=18,
                        language='en'
                    )
                    
                    if location and location.raw:
                        addr = location.raw.get('address', {})
                        
                        # Extract components
                        house_num = addr.get('house_number', '')
                        street = addr.get('road') or addr.get('street') or addr.get('highway', '')
                        city = addr.get('city') or addr.get('town') or addr.get('village', '')
                        state = addr.get('state', '')
                        postcode = addr.get('postcode', '')
                        
                        # Build address
                        if house_num and street:
                            address_parts = [f"{house_num} {street}"]
                            if city: address_parts.append(city)
                            if state: address_parts.append(state)
                            if postcode: address_parts.append(postcode)
                            
                            address = ', '.join(address_parts)
                            working_df.at[idx, 'Physical_Address'] = address
                            working_df.at[idx, 'Street_Name'] = f"{house_num} {street}"
                            working_df.at[idx, 'Address_Quality'] = 'Complete Street Address'
                            stats['complete_address'] += 1
                            
                            if len(sample_addresses) < 5:
                                sample_addresses.append(address)
                                
                        elif street:
                            address_parts = [street]
                            if city: address_parts.append(city)
                            if state: address_parts.append(state)
                            if postcode: address_parts.append(postcode)
                            
                            address = ', '.join(address_parts)
                            working_df.at[idx, 'Physical_Address'] = address
                            working_df.at[idx, 'Street_Name'] = street
                            working_df.at[idx, 'Address_Quality'] = 'Street Only'
                            stats['street_only'] += 1
                            
                        else:
                            working_df.at[idx, 'Physical_Address'] = location.address
                            working_df.at[idx, 'Address_Quality'] = 'Area Only'
                            stats['area_only'] += 1
                    else:
                        # Use coordinates
                        fallback = f"{lat:.6f}, {lon:.6f}"
                        if 'City' in row and pd.notna(row['City']):
                            fallback += f", {row['City']}"
                        working_df.at[idx, 'Physical_Address'] = fallback
                        working_df.at[idx, 'Address_Quality'] = 'Coordinates Only'
                        stats['coordinates_only'] += 1
                else:
                    working_df.at[idx, 'Physical_Address'] = 'Invalid coordinates'
                    working_df.at[idx, 'Address_Quality'] = 'Error'
                    
            except Exception as e:
                working_df.at[idx, 'Physical_Address'] = f"{lat}, {lon}"
                working_df.at[idx, 'Address_Quality'] = 'Error'
            
            # Update progress
            processing_status[session_id]['processed'] = idx + 1
        
        # Store results
        results_storage[session_id] = working_df
        
        # Update status
        processing_status[session_id]['status'] = 'completed'
        processing_status[session_id]['results'] = {
            'stats': stats,
            'sample_addresses': sample_addresses
        }
        
    except Exception as e:
        processing_status[session_id]['status'] = 'error'
        processing_status[session_id]['message'] = str(e)

@app.route('/progress/<session_id>')
def get_progress(session_id):
    """Get processing progress"""
    if session_id not in processing_status:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify(processing_status[session_id])

@app.route('/download/<session_id>')
def download_results(session_id):
    """Download processed results"""
    if session_id not in results_storage:
        return jsonify({'error': 'Results not found'}), 404
    
    df = results_storage[session_id]
    
    # Create temporary file for download
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f"cluster_addresses_{timestamp}.xlsx"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    
    # Save to Excel with formatting
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Addresses', index=False)
    
    # Send file and clean up
    response = send_file(output_path, as_attachment=True, download_name=output_filename)
    
    # Clean up after sending
    @response.call_on_close
    def cleanup():
        if os.path.exists(output_path):
            os.remove(output_path)
        # Clean up session data
        if session_id in results_storage:
            del results_storage[session_id]
        if session_id in processing_status:
            del processing_status[session_id]
    
    return response

if __name__ == '__main__':
    print("\n" + "="*60)
    print("CLUSTER ADDRESS FINDER WEB APP")
    print("="*60)
    print("\nStarting server...")
    print("\nOnce started, open your browser and go to:")
    print("\n    http://localhost:5000")
    print("\nTo stop the server, press Ctrl+C")
    print("="*60 + "\n")
    
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
