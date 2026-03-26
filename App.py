import ee
import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

# 1. SETUP & PATHS
load_dotenv()
current_dir = os.path.dirname(os.path.abspath(__file__))
# Explicitly telling Flask to look in backend/templates
template_dir = os.path.join(current_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)
CORS(app)

# 2. GOOGLE EARTH ENGINE AUTH
SERVICE_ACCOUNT = os.getenv('GEE_SERVICE_ACCOUNT')
KEY_FILE = os.path.join(current_dir, 'private-key.json')
GEE_JSON_KEY = os.getenv('GEE_JSON_KEY')

try:
    if os.path.exists(KEY_FILE):
        credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, KEY_FILE)
        ee.Initialize(credentials)
        print("✅ SUCCESS: KAIROS Backend Linked to Earth Engine (via local key)")
    elif GEE_JSON_KEY:
        import json
        import tempfile
        # Create a temporary file for the credentials JSON
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
            tf.write(GEE_JSON_KEY)
            temp_key_path = tf.name
        
        credentials = ee.ServiceAccountCredentials(SERVICE_ACCOUNT, temp_key_path)
        ee.Initialize(credentials)
        os.unlink(temp_key_path) # Clean up
        print("✅ SUCCESS: KAIROS Backend Linked to Earth Engine (via environment variable)")
    else:
        print("❌ ERROR: private-key.json not found and GEE_JSON_KEY env var not set")
except Exception as e:
    print(f"❌ AUTHENTICATION FAILED: {e}")

# 3. NAVIGATION ROUTES

@app.route('/')
@app.route('/index')
def home():
    """Step 1: The main landing page"""
    return render_template('index.html')

@app.route('/finallogin')
def login_page():
    """Maps the /login URL to your login HTML file"""
    return render_template('finallogin.html')

@app.route('/dashboard')
def dashboard():
    """Step 2: The coordinate entry page"""
    return render_template('dashboard.html')

@app.route('/map')
def map_view():
    """Step 3: The 2D satellite view"""
    return render_template('earthcore2d.html')

@app.route('/earth3d')
def earth3d():
    """3D Earth view"""
    return render_template('earth3d.html')

@app.route('/datasetview')
def datasetview():
    """Dataset viewing page"""
    return render_template('datasetview.html')

@app.route('/imageanalysis')
def imageanalysis():
    """Image analysis page"""
    return render_template('imageanalysis.html')

@app.route('/dataview')
def dataview():
    """Data view page"""
    return render_template('dataview.html')

# 4. GEE TILE API
@app.route('/api/gee-tiles')
def get_gee_tiles():
    try:
        lat = float(request.args.get('lat', 28.6139))
        lon = float(request.args.get('lon', 77.2090))
        mode = request.args.get('mode', 'NDVI')

        point = ee.Geometry.Point([lon, lat])
        image = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
            .filterBounds(point) \
            .sort('CLOUD_COVER') \
            .first()

        # Landsat 8 Scaling
        optical_bands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
        
        if mode == 'NDVI':
            processed = optical_bands.normalizedDifference(['SR_B5', 'SR_B4'])
            vis = {'min': 0, 'max': 0.8, 'palette': ['#34495e', '#f1c40f', '#2ecc71']}
        elif mode == 'WATER':
            processed = optical_bands.normalizedDifference(['SR_B3', 'SR_B5'])
            vis = {'min': 0, 'max': 0.5, 'palette': ['#ffffff', '#3498db', '#1e3799']}
        else:
            processed = optical_bands.normalizedDifference(['SR_B5', 'SR_B4'])
            vis = {'min': 0, 'max': 0.8}

        map_id = processed.getMapId(vis)
        return jsonify({'url': map_id['tile_fetcher'].url_format, 'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)