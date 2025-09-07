class DeepSeekProxyApp {
    constructor() {
        this.apiKey = '';
        this.selectedModel = 'deepseek/deepseek-chat';
        this.fetchFromDeepSeek = false;
        this.toast = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateProxyUrls();
        this.loadDefaultModels(); // Start with default models to avoid API calls
        this.updateStatus();
        
        // Initialize toast
        const toastEl = document.getElementById('notification-toast');
        this.toast = new bootstrap.Toast(toastEl);
        
        // Auto-refresh status every 10 minutes (further reduced to save tokens)
        setInterval(() => this.updateStatus(), 600000);
    }

    setupEventListeners() {
        // API Key validation
        document.getElementById('validate-key').addEventListener('click', () => this.validateApiKey());
        document.getElementById('toggle-key-visibility').addEventListener('click', () => this.toggleKeyVisibility());
        
        // Model management  
        document.getElementById('fetch-models-toggle').addEventListener('change', (e) => {
            this.fetchFromDeepSeek = e.target.checked;
            if (e.target.checked) {
                // Only fetch when explicitly enabled by user
                this.loadModels(true);
            } else {
                // Load default models when disabled
                this.loadDefaultModels();
            }
        });
        document.getElementById('refresh-models').addEventListener('click', () => this.loadModels(true));
        document.getElementById('model-select').addEventListener('change', (e) => {
            this.selectedModel = e.target.value;
        });
        
        // URL copying
        document.getElementById('copy-proxy-url').addEventListener('click', () => 
            this.copyToClipboard('proxy-url', 'Proxy URL copied!'));
        document.getElementById('copy-models-url').addEventListener('click', () => 
            this.copyToClipboard('models-url', 'Models URL copied!'));
        
        // Log management
        document.getElementById('clear-logs').addEventListener('click', () => this.clearLogs());
        
        // API Key input changes
        document.getElementById('api-key').addEventListener('input', () => {
            document.getElementById('key-validation-result').innerHTML = '';
        });
    }

    updateProxyUrls() {
        const baseUrl = window.location.origin;
        document.getElementById('proxy-url').value = `${baseUrl}/v1/chat/completions`;
        document.getElementById('models-url').value = `${baseUrl}/v1/models`;
    }

    async validateApiKey() {
        const apiKey = document.getElementById('api-key').value.trim();
        const button = document.getElementById('validate-key');
        const resultDiv = document.getElementById('key-validation-result');
        
        if (!apiKey) {
            this.showValidationResult(false, 'Please enter an API key');
            return;
        }

        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Validating...';
        button.disabled = true;

        try {
            const response = await fetch('/api/validate-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ api_key: apiKey })
            });

            const data = await response.json();
            
            if (data.valid) {
                this.apiKey = apiKey;
                this.showValidationResult(true, 'API key is valid and saved');
                // Don't automatically fetch models - let user decide with toggle
                this.logActivity('success', 'API key validated successfully');
            } else {
                this.showValidationResult(false, data.error || 'Invalid API key');
                this.logActivity('error', `API key validation failed: ${data.error}`);
            }
        } catch (error) {
            this.showValidationResult(false, 'Validation failed - check connection');
            this.logActivity('error', `API key validation error: ${error.message}`);
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }

    showValidationResult(isValid, message) {
        const resultDiv = document.getElementById('key-validation-result');
        const alertClass = isValid ? 'alert-success' : 'alert-danger';
        const icon = isValid ? 'fa-check-circle' : 'fa-exclamation-triangle';
        
        resultDiv.innerHTML = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${icon} me-2"></i>${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
    }

    async loadModels(forceRefresh = false) {
        const select = document.getElementById('model-select');
        const refreshButton = document.getElementById('refresh-models');
        const sourceSpan = document.getElementById('model-source');
        
        // Show loading state
        if (forceRefresh) {
            refreshButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            refreshButton.disabled = true;
        }
        
        select.innerHTML = '<option value="">Loading models...</option>';

        try {
            const fetchParam = this.fetchFromDeepSeek ? 'true' : 'false';
            // Only add timestamp param if force refresh to prevent unnecessary cache busting
            const timestampParam = forceRefresh ? `&t=${Date.now()}` : '';
            const response = await fetch(`/api/models?fetch=${fetchParam}${timestampParam}`);
            const data = await response.json();
            
            // Clear and populate select
            select.innerHTML = '';
            
            if (data.data && data.data.length > 0) {
                data.data.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model.id;
                    option.textContent = model.id;
                    if (model.id === this.selectedModel) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
                
                // Update model count
                document.getElementById('models-count').innerHTML = 
                    `<i class="fas fa-robot me-1"></i>Models: ${data.data.length}`;
                
                // Update source info
                sourceSpan.textContent = data.source || 'unknown';
                sourceSpan.className = this.getSourceClass(data.source);
                
                this.logActivity('info', `Loaded ${data.data.length} models from ${data.source}`);
            } else {
                select.innerHTML = '<option value="">No models available</option>';
                this.logActivity('warning', 'No models available');
            }
            
        } catch (error) {
            select.innerHTML = '<option value="">Error loading models</option>';
            sourceSpan.textContent = 'error';
            sourceSpan.className = 'text-danger';
            this.logActivity('error', `Failed to load models: ${error.message}`);
        } finally {
            if (forceRefresh) {
                refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
                refreshButton.disabled = false;
            }
        }
    }

    getSourceClass(source) {
        switch(source) {
            case 'deepseek_api': return 'text-success';
            case 'cache': return 'text-info';
            case 'default': return 'text-warning';
            default: return 'text-muted';
        }
    }

    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const status = await response.json();
            
            // Update connection status
            const connectionStatus = document.getElementById('connection-status');
            if (status.api_key_configured && status.api_connection === 'configured') {
                connectionStatus.innerHTML = '<i class="fas fa-circle me-1"></i>Key Set';
                connectionStatus.className = 'badge bg-success';
            } else if (status.api_key_configured) {
                connectionStatus.innerHTML = '<i class="fas fa-circle me-1"></i>Key Set';
                connectionStatus.className = 'badge bg-warning';
            } else {
                connectionStatus.innerHTML = '<i class="fas fa-circle me-1"></i>No Key';
                connectionStatus.className = 'badge bg-danger';
            }
            
            // Update cache status
            const cacheStatus = document.getElementById('cache-status');
            if (status.cache_valid) {
                cacheStatus.innerHTML = `<i class="fas fa-database me-1"></i>Cache: Valid (${status.cache_size})`;
                cacheStatus.className = 'badge bg-success';
            } else {
                cacheStatus.innerHTML = '<i class="fas fa-database me-1"></i>Cache: Expired';
                cacheStatus.className = 'badge bg-secondary';
            }
            
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    }

    toggleKeyVisibility() {
        const input = document.getElementById('api-key');
        const button = document.getElementById('toggle-key-visibility');
        const icon = button.querySelector('i');
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }

    async copyToClipboard(elementId, message) {
        const element = document.getElementById(elementId);
        try {
            await navigator.clipboard.writeText(element.value);
            this.showToast('Success', message, 'success');
        } catch (error) {
            // Fallback for older browsers
            element.select();
            document.execCommand('copy');
            this.showToast('Success', message, 'success');
        }
    }

    showToast(title, message, type = 'info') {
        document.getElementById('toast-title').textContent = title;
        document.getElementById('toast-body').textContent = message;
        
        const toastEl = document.getElementById('notification-toast');
        toastEl.className = `toast ${type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info'}`;
        
        this.toast.show();
    }

    logActivity(level, message) {
        const logContainer = document.getElementById('activity-log');
        const timestamp = new Date().toLocaleTimeString();
        
        const levelClass = {
            'success': 'text-success',
            'error': 'text-danger',
            'warning': 'text-warning',
            'info': 'text-info'
        }[level] || 'text-muted';
        
        const levelIcon = {
            'success': 'fa-check-circle',
            'error': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle',
            'info': 'fa-info-circle'
        }[level] || 'fa-circle';

        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry mb-1 font-monospace small';
        logEntry.innerHTML = `
            <span class="text-muted">[${timestamp}]</span>
            <i class="fas ${levelIcon} ${levelClass} me-1"></i>
            <span class="${levelClass}">${level.toUpperCase()}</span>: ${message}
        `;

        // Remove placeholder text if it exists
        if (logContainer.querySelector('.text-muted') && logContainer.children.length === 1) {
            logContainer.innerHTML = '';
        }

        logContainer.appendChild(logEntry);
        logContainer.scrollTop = logContainer.scrollHeight;
        
        // Keep only last 100 entries
        while (logContainer.children.length > 100) {
            logContainer.removeChild(logContainer.firstChild);
        }
    }

    clearLogs() {
        const logContainer = document.getElementById('activity-log');
        logContainer.innerHTML = '<div class="text-muted">Activity will be logged here...</div>';
    }

    loadDefaultModels() {
        const select = document.getElementById('model-select');
        const sourceSpan = document.getElementById('model-source');
        
        // Default models without API call
        const defaultModels = [
            { id: 'deepseek/deepseek-chat', name: 'DeepSeek Chat' },
            { id: 'deepseek/deepseek-coder', name: 'DeepSeek Coder' }
        ];
        
        select.innerHTML = '';
        defaultModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.id;
            if (model.id === this.selectedModel) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        
        // Update UI indicators
        document.getElementById('models-count').innerHTML = 
            `<i class="fas fa-robot me-1"></i>Models: ${defaultModels.length}`;
        sourceSpan.textContent = 'default';
        sourceSpan.className = 'text-warning';
        
        this.logActivity('info', `Loaded ${defaultModels.length} default models (no API call)`);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DeepSeekProxyApp();
});
