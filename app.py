import os
import json
import logging
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Enable CORS for all routes
CORS(app, origins=["*"])

# Cache for models with expiration
models_cache = {
    'data': [],
    'timestamp': None,
    'ttl': 300  # 5 minutes cache
}

# Default model list fallback with Janitor.AI compatible format
DEFAULT_MODELS = [
    {"id": "deepseek/deepseek-chat", "object": "model", "created": 1640995200, "owned_by": "deepseek"},
    {"id": "deepseek/deepseek-coder", "object": "model", "created": 1640995200, "owned_by": "deepseek"}
]

DEEPSEEK_API_BASE = "https://api.deepseek.com"

def is_cache_valid():
    """Check if the models cache is still valid"""
    if models_cache['timestamp'] is None:
        return False
    return datetime.now() - models_cache['timestamp'] < timedelta(seconds=models_cache['ttl'])

def fetch_models_from_deepseek(api_key):
    """Fetch available models from DeepSeek API"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{DEEPSEEK_API_BASE}/v1/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            original_models = data.get('data', [])
            
            # Convert model IDs to Janitor.AI format (deepseek/model-name)
            models = []
            for model in original_models:
                converted_model = model.copy()
                converted_model['id'] = f"deepseek/{model['id']}"
                models.append(converted_model)
            
            # Update cache with converted models
            models_cache['data'] = models
            models_cache['timestamp'] = datetime.now()
            
            logger.info(f"Successfully fetched {len(models)} models from DeepSeek")
            return models
        else:
            logger.error(f"Failed to fetch models from DeepSeek: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error fetching models from DeepSeek: {str(e)}")
        return None

def validate_api_key(api_key):
    """Validate API key by making a test request to DeepSeek"""
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f"{DEEPSEEK_API_BASE}/v1/models", headers=headers, timeout=5)
        return response.status_code == 200
        
    except requests.RequestException:
        return False

def convert_openai_to_deepseek(openai_request):
    """Convert OpenAI format request to DeepSeek format"""
    # DeepSeek API is compatible with OpenAI format, so minimal conversion needed
    deepseek_request = openai_request.copy()
    
    # Convert model format from 'deepseek/model-name' to 'model-name' for DeepSeek API
    if 'model' in deepseek_request and deepseek_request['model'].startswith('deepseek/'):
        deepseek_request['model'] = deepseek_request['model'].replace('deepseek/', '')
    elif 'model' not in deepseek_request:
        deepseek_request['model'] = 'deepseek-chat'
    
    # Log the conversion for debugging
    logger.debug(f"Converted request: {json.dumps(deepseek_request, indent=2)}")
    
    return deepseek_request

def convert_deepseek_to_openai(deepseek_response):
    """Convert DeepSeek response to OpenAI format"""
    # DeepSeek responses are already in OpenAI format
    return deepseek_response

@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html')

@app.route('/api/validate-key', methods=['POST'])
def validate_key():
    """Validate DeepSeek API key"""
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({'valid': False, 'error': 'API key is required'}), 400
        
        is_valid = validate_api_key(api_key)
        
        if is_valid:
            session['api_key'] = api_key
            return jsonify({'valid': True, 'message': 'API key is valid'})
        else:
            return jsonify({'valid': False, 'error': 'Invalid API key'})
            
    except Exception as e:
        logger.error(f"Error validating API key: {str(e)}")
        return jsonify({'valid': False, 'error': 'Validation failed'}), 500

@app.route('/api/models', methods=['GET'])
def get_models():
    """Get available models (either from cache, DeepSeek API, or defaults)"""
    try:
        fetch_from_api = request.args.get('fetch', 'false').lower() == 'true'
        api_key = session.get('api_key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        
        # If fetch_from_api is True and we have an API key, fetch from DeepSeek
        if fetch_from_api and api_key:
            models = fetch_models_from_deepseek(api_key)
            if models:
                return jsonify({'data': models, 'source': 'deepseek_api'})
        
        # Check cache if we have an API key
        if api_key and is_cache_valid():
            return jsonify({'data': models_cache['data'], 'source': 'cache'})
        
        # Try to fetch fresh data if we have an API key
        if api_key:
            models = fetch_models_from_deepseek(api_key)
            if models:
                return jsonify({'data': models, 'source': 'deepseek_api'})
        
        # Fallback to default models
        return jsonify({'data': DEFAULT_MODELS, 'source': 'default'})
        
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return jsonify({'data': DEFAULT_MODELS, 'source': 'default', 'error': str(e)})

@app.route('/v1/models', methods=['GET'])
def openai_models():
    """OpenAI-compatible models endpoint"""
    try:
        api_key = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if api_key:
            models = fetch_models_from_deepseek(api_key)
            if models:
                return jsonify({'data': models, 'object': 'list'})
        
        # Check cache
        if is_cache_valid():
            return jsonify({'data': models_cache['data'], 'object': 'list'})
        
        # Fallback to defaults
        return jsonify({'data': DEFAULT_MODELS, 'object': 'list'})
        
    except Exception as e:
        logger.error(f"Error in OpenAI models endpoint: {str(e)}")
        return jsonify({'data': DEFAULT_MODELS, 'object': 'list'})

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI-compatible chat completions endpoint (proxy to DeepSeek)"""
    try:
        # Get API key from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': {'message': 'Missing or invalid Authorization header'}}), 401
        
        api_key = auth_header.replace('Bearer ', '')
        
        # Get request data
        openai_request = request.get_json()
        if not openai_request:
            return jsonify({'error': {'message': 'Request body is required'}}), 400
        
        # Convert to DeepSeek format
        deepseek_request = convert_openai_to_deepseek(openai_request)
        
        # Make request to DeepSeek API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Proxying request to DeepSeek: {deepseek_request.get('model', 'unknown')}")
        
        response = requests.post(
            f"{DEEPSEEK_API_BASE}/v1/chat/completions",
            headers=headers,
            json=deepseek_request,
            timeout=60,
            stream=deepseek_request.get('stream', False)
        )
        
        # Handle streaming response
        if deepseek_request.get('stream', False):
            def generate():
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        yield chunk
            
            return app.response_class(
                generate(),
                mimetype='text/plain',
                headers={'Content-Type': 'text/plain; charset=utf-8'}
            )
        
        # Handle regular response
        if response.status_code == 200:
            deepseek_response = response.json()
            openai_response = convert_deepseek_to_openai(deepseek_response)
            return jsonify(openai_response)
        else:
            logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return jsonify({
                'error': {
                    'message': f'DeepSeek API error: {response.status_code}',
                    'type': 'api_error',
                    'code': response.status_code
                }
            }), response.status_code
            
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({
            'error': {
                'message': f'Request failed: {str(e)}',
                'type': 'request_error'
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in chat completions: {str(e)}")
        return jsonify({
            'error': {
                'message': f'Internal server error: {str(e)}',
                'type': 'internal_error'
            }
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Get proxy status"""
    try:
        api_key = session.get('api_key')
        
        status_info = {
            'proxy_url': f"{request.host_url.rstrip('/')}/v1/chat/completions",
            'models_endpoint': f"{request.host_url.rstrip('/')}/v1/models",
            'api_key_configured': bool(api_key),
            'cache_valid': is_cache_valid(),
            'cache_size': len(models_cache['data']),
            'timestamp': datetime.now().isoformat()
        }
        
        if api_key:
            status_info['api_connection'] = validate_api_key(api_key)
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
