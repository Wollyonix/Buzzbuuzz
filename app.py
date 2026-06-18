import os
import json
import logging
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session, make_response
import json as _json
import threading
from flask_cors import CORS
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise ValueError("SESSION_SECRET environment variable is required for secure session management")

# Enable CORS for all routes with specific headers for API compatibility
CORS(app, 
     origins=["*"],
     allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
     expose_headers=["Content-Type", "Content-Length"],
     methods=["GET", "POST", "OPTIONS"],
     supports_credentials=False)

# Cache for models with expiration
models_cache = {
    'data': [],
    'timestamp': None,
    'ttl': 300  # 5 minutes cache
}

# Rate limiting for API calls
api_call_timestamps = {
    'models': [],
    'validate': []
}
RATE_LIMIT_WINDOW = 60  # 1 minute
MAX_CALLS_PER_MINUTE = 10

# Default model list fallback with Janitor.AI compatible format
DEFAULT_MODELS = [
    {"id": "deepseek/deepseek-v3.1-terminus", "object": "model", "created": 1640995200, "owned_by": "deepseek"},
    {"id": "deepseek/deepseek-chat", "object": "model", "created": 1640995200, "owned_by": "deepseek"},
    {"id": "deepseek/deepseek-coder", "object": "model", "created": 1640995200, "owned_by": "deepseek"}
]

# Add V4 models to defaults so clients see new models without API calls
DEFAULT_MODELS.extend([
    {"id": "deepseek/deepseek-v4-flash", "object": "model", "created": 1710000000, "owned_by": "deepseek"},
    {"id": "deepseek/deepseek-v4-pro", "object": "model", "created": 1710000000, "owned_by": "deepseek"}
])
DEEPSEEK_API_BASE = "https://api.deepseek.com"
CHAT_LOG_PATH = os.environ.get("CHAT_LOG_PATH", "chat_logs.jsonl")
ENABLE_CHAT_LOGS = os.environ.get("ENABLE_CHAT_LOGS", "0") == "1"
# Toggle for DeepSeek "thinking" mode (default: enabled)
ENABLE_THINKING_MODE = os.environ.get("ENABLE_THINKING_MODE", "1") == "1"
LOGS_PASSWORD = os.environ.get("LOGS_PASSWORD")
LOGS_PER_PAGE = int(os.environ.get("LOGS_PER_PAGE", "20"))
LOGS_POLL_INTERVAL = float(os.environ.get("LOGS_POLL_INTERVAL", "1.5"))
LOGS_LOCK = threading.Lock()

# Optional cross-process file lock (recommended in multi-worker environments)
try:
    import portalocker
except Exception:
    portalocker = None
LOGS_PER_PAGE = 20


def save_chat_log(request_obj, response_obj, meta=None):
    if not ENABLE_CHAT_LOGS:
        return

    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request": {
            "model": request_obj.get("model"),
            "messages": request_obj.get("messages", []),
            "temperature": request_obj.get("temperature"),
            "top_p": request_obj.get("top_p"),
            "frequency_penalty": request_obj.get("frequency_penalty"),
            "presence_penalty": request_obj.get("presence_penalty")
        },
        "response": response_obj,
        "meta": meta or {}
    }

    try:
        if portalocker:
            with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                portalocker.unlock(f)
        else:
            with LOGS_LOCK:
                with open(CHAT_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Could not save chat log: {e}")


def _read_all_logs():
    items = []
    if not os.path.exists(CHAT_LOG_PATH):
        return items
    try:
        if portalocker:
            with open(CHAT_LOG_PATH, 'r', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_SH)
                for line in f:
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        continue
                portalocker.unlock(f)
        else:
            with LOGS_LOCK:
                with open(CHAT_LOG_PATH, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            items.append(json.loads(line))
                        except Exception:
                            continue
    except Exception as e:
        logger.error(f"Unable to read chat logs: {e}")
    return items


def _write_all_logs(items):
    try:
        if portalocker:
            with open(CHAT_LOG_PATH, 'w', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                for entry in items:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                portalocker.unlock(f)
        else:
            with LOGS_LOCK:
                with open(CHAT_LOG_PATH, 'w', encoding='utf-8') as f:
                    for entry in items:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Unable to write chat logs: {e}")


def is_cache_valid():
    """Check if the models cache is still valid"""
    if models_cache['timestamp'] is None:
        return False
    return datetime.now() - models_cache['timestamp'] < timedelta(seconds=models_cache['ttl'])

def fetch_models_from_deepseek(api_key):
    """Fetch available models from DeepSeek API"""
    try:
        # Check rate limiting
        if is_rate_limited('models'):
            logger.warning("Models API rate limited, returning cached data")
            return models_cache['data'] if models_cache['data'] else DEFAULT_MODELS
            
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

def is_rate_limited(endpoint):
    """Check if API endpoint is rate limited"""
    now = time.time()
    timestamps = api_call_timestamps.get(endpoint, [])
    
    # Remove timestamps older than the window
    timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    api_call_timestamps[endpoint] = timestamps
    
    # Check if we're over the limit
    if len(timestamps) >= MAX_CALLS_PER_MINUTE:
        logger.warning(f"Rate limit exceeded for {endpoint}")
        return True
    
    # Add current timestamp
    timestamps.append(now)
    return False

def validate_api_key(api_key):
    """Validate API key by making a test request to DeepSeek"""
    try:
        # Check rate limiting
        if is_rate_limited('validate'):
            logger.warning("Validation rate limited")
            return False
            
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
    if 'model' in deepseek_request and isinstance(deepseek_request['model'], str):
        m = deepseek_request['model']
        # Normalize prefix
        if m.startswith('deepseek/'):
            m = m.replace('deepseek/', '')

        # Backwards-compatibility: map deprecated names to V4 where appropriate
        # According to DeepSeek docs, 'deepseek-chat' and 'deepseek-reasoner' map
        # to non-thinking and thinking modes of deepseek-v4-flash respectively.
        if m == 'deepseek-chat' or m == 'chat' or m == 'deepseek-chat':
            m = 'deepseek-v4-flash'
        elif m == 'deepseek-reasoner' or m == 'reasoner':
            m = 'deepseek-v4-flash'

        deepseek_request['model'] = m
    elif 'model' not in deepseek_request:
        deepseek_request['model'] = 'deepseek-v4-flash'
    # Determine thinking mode: per-request override takes precedence
    # DeepSeek supports a 'thinking' flag; map from incoming request if present,
    # otherwise use global ENABLE_THINKING_MODE.
    if 'thinking' in openai_request:
        # DeepSeek expects a ThinkingOptions struct, not a raw boolean.
        # Map boolean to an explicit mode value.
        req_thinking = openai_request.get('thinking')
        if isinstance(req_thinking, bool):
            deepseek_request['thinking'] = {'type': 'thinking' if req_thinking else 'non-thinking'}
        elif isinstance(req_thinking, dict):
            # ensure provided dict has required 'type' field if possible
            if 'type' not in req_thinking and 'mode' in req_thinking:
                req_thinking = dict(req_thinking)
                req_thinking['type'] = req_thinking.pop('mode')
            deepseek_request['thinking'] = req_thinking
        else:
            # fallback: use global toggle
            deepseek_request['thinking'] = {'type': 'thinking' if ENABLE_THINKING_MODE else 'non-thinking'}
    else:
        # apply global toggle as structured object
        deepseek_request.setdefault('thinking', {'type': 'thinking' if ENABLE_THINKING_MODE else 'non-thinking'})
    
    # Log the conversion for debugging without exposing full content
    logger.debug(f"Converted request for model: {deepseek_request.get('model', 'unknown')}")
    
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
        
        # ONLY fetch from API if explicitly requested AND we have an API key
        if fetch_from_api and api_key:
            logger.info("Explicit API fetch requested by user")
            models = fetch_models_from_deepseek(api_key)
            if models:
                return jsonify({'data': models, 'source': 'deepseek_api'})
        
        # Check cache if we have an API key and fetch was requested
        if fetch_from_api and api_key and is_cache_valid():
            return jsonify({'data': models_cache['data'], 'source': 'cache'})
        
        # Default behavior: return static models (NO API CALL)
        return jsonify({'data': DEFAULT_MODELS, 'source': 'default'})
        
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return jsonify({'data': DEFAULT_MODELS, 'source': 'default', 'error': str(e)})

@app.route('/v1/models', methods=['GET', 'OPTIONS'])
def openai_models():
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = app.response_class()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
    """OpenAI-compatible models endpoint - returns default models to prevent token usage"""
    try:
        # For Janitor.AI compatibility, ALWAYS return default models without API calls
        # This prevents unnecessary token consumption from model listing
        logger.info("Models endpoint called - returning default models (no API call)")
        response_obj = jsonify({'data': DEFAULT_MODELS, 'object': 'list'})
        response_obj.headers['Access-Control-Allow-Origin'] = '*'
        return response_obj
        
    except Exception as e:
        logger.error(f"Error in OpenAI models endpoint: {str(e)}")
        response_obj = jsonify({'data': DEFAULT_MODELS, 'object': 'list'})
        response_obj.headers['Access-Control-Allow-Origin'] = '*'
        return response_obj

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    # Handle CORS preflight requests
    if request.method == 'OPTIONS':
        response = app.response_class()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '86400'
        return response
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

        # Always save the incoming request immediately (useful for non-streaming misses)
        try:
            save_chat_log(deepseek_request, {"status": "pending"}, meta={"model": deepseek_request.get("model"), "note": "request-saved-before-response"})
        except Exception as e:
            logger.warning(f"Could not pre-save incoming request: {e}")
        
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
            timeout=(10, 60),  # connection timeout, read timeout
            stream=deepseek_request.get('stream', False)
        )
        
        # Handle streaming response
        if deepseek_request.get('stream', False):
            def generate():
                try:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            yield chunk
                except (requests.RequestException, GeneratorExit) as e:
                    logger.warning(f"Stream interrupted: {str(e)}")
                except Exception as e:
                    logger.error(f"Streaming error: {str(e)}")
                finally:
                    # Ensure connection is closed
                    response.close()
            
            return app.response_class(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                }
            )
        
        # Handle regular response
        if response.status_code == 200:
            deepseek_response = response.json()
            openai_response = convert_deepseek_to_openai(deepseek_response)
            try:
                save_chat_log(deepseek_request, openai_response, meta={"model": deepseek_request.get("model")})
            except Exception as e:
                logger.warning(f"Failed to save chat log: {e}")
            response_obj = jsonify(openai_response)
            response_obj.headers['Access-Control-Allow-Origin'] = '*'
            return response_obj
        else:
            logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
            return jsonify({
                'error': {
                    'message': f'DeepSeek API error: {response.status_code}',
                    'type': 'api_error',
                    'code': response.status_code
                }
            }), response.status_code
            
    except requests.Timeout as e:
        logger.error(f"Request timeout: {str(e)}")
        return jsonify({
            'error': {
                'message': 'Request timeout - DeepSeek API took too long to respond',
                'type': 'timeout_error'
            }
        }), 504
    except requests.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return jsonify({
            'error': {
                'message': 'Connection error - Could not reach DeepSeek API',
                'type': 'connection_error'
            }
        }), 503
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
            # Don't validate API key automatically to prevent token usage
            # Only indicate that a key is configured
            status_info['api_connection'] = 'configured'
        
        return jsonify(status_info)
        
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/tokens', methods=['GET'])
def tokens_get():
    # Summarize existing chat logs (word-count token estimate)
    rows = []
    items = _read_all_logs()
    for i, entry in enumerate(items):
        ts = entry.get('timestamp')
        req = entry.get('request', {})
        resp = entry.get('response', {})

        # Aggregate request text
        req_text = ''
        if isinstance(req, dict):
            msgs = req.get('messages', [])
            if isinstance(msgs, list):
                parts = []
                for m in msgs:
                    if isinstance(m, dict):
                        parts.append(m.get('content', '') or m.get('text', ''))
                    elif isinstance(m, str):
                        parts.append(m)
                req_text = ' '.join([p for p in parts if p])
        elif isinstance(req, str):
            req_text = req

        # Aggregate response text
        resp_text = ''
        if isinstance(resp, dict):
            # try common fields
            resp_text = _json.dumps(resp)
        elif isinstance(resp, str):
            resp_text = resp

        req_tokens = len(req_text.split()) if req_text else 0
        resp_tokens = len(resp_text.split()) if resp_text else 0
        rows.append({
            'index': i,
            'timestamp': ts,
            'req_tokens': req_tokens,
            'resp_tokens': resp_tokens,
            'total': req_tokens + resp_tokens
        })

    # sort recent first
    rows = list(reversed(rows))
    return render_template('tokens.html', log_rows=rows)


@app.route('/tokens', methods=['POST'])
def tokens_post():
    payload = request.form.get('payload', '').strip()
    results = {'total': 0, 'details': []}

    messages = None
    try:
        parsed = _json.loads(payload)
        if isinstance(parsed, dict) and 'messages' in parsed and isinstance(parsed['messages'], list):
            messages = parsed['messages']
        elif isinstance(parsed, list):
            messages = parsed
    except Exception:
        messages = None

    if messages is None:
        lines = [l.strip() for l in payload.splitlines() if l.strip()]
        messages = []
        for i, ln in enumerate(lines):
            try:
                obj = _json.loads(ln)
                messages.append(obj)
            except Exception:
                messages.append({'content': ln, 'label': f'line {i+1}'})

    total = 0
    details = []
    for i, m in enumerate(messages):
        content = ''
        label = f'message {i+1}'
        if isinstance(m, dict):
            content = m.get('content', '') or m.get('text', '') or ''
            if 'role' in m:
                label = f"{m.get('role')}"
            elif 'label' in m:
                label = m.get('label')
        elif isinstance(m, str):
            content = m
        count = len(content.split())
        total += count
        details.append({'label': label, 'count': count})

    results['total'] = total
    results['details'] = details

    return render_template('tokens.html', results=results, payload=payload)


@app.route('/api/logs', methods=['GET'])
def api_get_logs():
    """Return paginated logs as JSON"""
    if not ENABLE_CHAT_LOGS:
        return jsonify({'enabled': False, 'items': [], 'page': 1, 'per_page': LOGS_PER_PAGE, 'total': 0})

    try:
        page = int(request.args.get('page', '1'))
    except ValueError:
        page = 1

    all_items = _read_all_logs()
    total = len(all_items)
    per_page = LOGS_PER_PAGE
    start = (page - 1) * per_page
    end = start + per_page
    items = all_items[start:end]

    return jsonify({'enabled': True, 'items': items, 'page': page, 'per_page': per_page, 'total': total})


@app.route('/api/logs/clear', methods=['POST'])
def api_clear_logs():
    try:
        # Truncate file
        if portalocker:
            with open(CHAT_LOG_PATH, 'w', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.LOCK_EX)
                f.truncate(0)
                portalocker.unlock(f)
        else:
            with LOGS_LOCK:
                open(CHAT_LOG_PATH, 'w', encoding='utf-8').close()
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/logs/delete', methods=['POST'])
def api_delete_log():
    data = request.get_json() or {}
    index = data.get('index')
    if index is None:
        return jsonify({'ok': False, 'error': 'index required'}), 400
    try:
        index = int(index)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid index'}), 400

    items = _read_all_logs()
    if index < 0 or index >= len(items):
        return jsonify({'ok': False, 'error': 'index out of range'}), 400

    items.pop(index)
    _write_all_logs(items)
    return jsonify({'ok': True})


@app.route('/api/logs/update', methods=['POST'])
def api_update_log():
    data = request.get_json() or {}
    index = data.get('index')
    entry = data.get('entry')
    if index is None or entry is None:
        return jsonify({'ok': False, 'error': 'index and entry required'}), 400
    try:
        index = int(index)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid index'}), 400

    items = _read_all_logs()
    if index < 0 or index >= len(items):
        return jsonify({'ok': False, 'error': 'index out of range'}), 400

    # Ensure entry is a dict
    if not isinstance(entry, dict):
        return jsonify({'ok': False, 'error': 'entry must be an object'}), 400

    items[index] = entry
    _write_all_logs(items)
    return jsonify({'ok': True})


@app.route('/api/logs/download', methods=['GET'])
def api_download_logs():
    if not os.path.exists(CHAT_LOG_PATH):
        return jsonify({'ok': False, 'error': 'no logs'}), 404
    try:
        with open(CHAT_LOG_PATH, 'r', encoding='utf-8') as f:
            data = f.read()
        resp = make_response(data)
        resp.headers['Content-Type'] = 'text/plain; charset=utf-8'
        resp.headers['Content-Disposition'] = 'attachment; filename="chat_logs.jsonl"'
        return resp
    except Exception as e:
        logger.error(f"Failed to read logs for download: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/logs')
def view_logs():
    """View saved chat logs with pagination"""
    page = request.args.get('page', '1')
    try:
        page = max(1, int(page))
    except ValueError:
        page = 1

    start = (page - 1) * LOGS_PER_PAGE
    end = start + LOGS_PER_PAGE
    items = []
    next_page = None
    prev_page = page - 1 if page > 1 else None

    if os.path.exists(CHAT_LOG_PATH):
        try:
            with open(CHAT_LOG_PATH, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < start:
                        continue
                    if i >= end:
                        next_page = page + 1
                        break
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Unable to read chat logs: {e}")

    return render_template('logs.html', items=items, page=page, next_page=next_page, prev_page=prev_page, per_page=LOGS_PER_PAGE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
