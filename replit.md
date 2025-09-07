# Overview

This is a DeepSeek Proxy application that serves as an OpenAI-compatible middleware specifically designed for Janitor.AI. The application acts as a bridge between Janitor.AI and the DeepSeek API, translating requests and responses to maintain compatibility with OpenAI's API format while leveraging DeepSeek's language models.

The proxy provides a web interface for configuration, model management, and monitoring, along with REST API endpoints that mirror OpenAI's structure for seamless integration with existing applications expecting OpenAI-compatible interfaces.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology Stack**: Pure HTML5, CSS3, and vanilla JavaScript with Bootstrap 5 for UI components
- **Theme**: Dark theme implementation using Bootstrap's dark mode with custom CSS overrides
- **Architecture Pattern**: Single-page application with class-based JavaScript organization
- **Real-time Updates**: Automatic status polling every 30 seconds and toast notifications for user feedback
- **Responsive Design**: Mobile-first approach using Bootstrap's grid system

## Backend Architecture
- **Framework**: Flask (Python) with CORS enabled for cross-origin requests
- **Architecture Pattern**: Simple MVC pattern with route handlers, service functions, and template rendering
- **Session Management**: Flask sessions with configurable secret key for security
- **Logging**: Python's built-in logging module with DEBUG level for development
- **Error Handling**: HTTP status codes and JSON error responses

## API Design
- **Compatibility Layer**: OpenAI-compatible endpoints (`/v1/models`, `/v1/chat/completions`) that proxy to DeepSeek API
- **Authentication**: Bearer token authentication forwarding to DeepSeek API
- **Request/Response Translation**: Automatic conversion between OpenAI and DeepSeek API formats
- **Model Management**: Dynamic model fetching from DeepSeek with fallback to default model list

## Caching Strategy
- **Models Caching**: In-memory cache with 5-minute TTL to reduce API calls to DeepSeek
- **Cache Validation**: Timestamp-based expiration checking before serving cached data
- **Fallback Mechanism**: Default model list when DeepSeek API is unavailable

## Configuration Management
- **Environment Variables**: Session secrets and API keys stored as environment variables
- **Runtime Configuration**: Web-based interface for API key management and model selection
- **Validation**: Client-side and server-side API key validation

# External Dependencies

## Third-party APIs
- **DeepSeek API**: Primary language model provider at `https://api.deepseek.com`
- **Authentication**: Bearer token-based authentication with DeepSeek

## Frontend Libraries
- **Bootstrap 5**: UI framework with dark theme support from CDN
- **Font Awesome 6**: Icon library for consistent iconography
- **Custom CSS**: Application-specific styling and theme overrides

## Python Dependencies
- **Flask**: Web framework for HTTP request handling
- **Flask-CORS**: Cross-origin resource sharing support
- **Requests**: HTTP client for DeepSeek API communication

## Infrastructure Requirements
- **Session Storage**: Server-side session management for user preferences
- **Logging System**: File-based or console logging for debugging and monitoring
- **HTTP Server**: WSGI-compatible server for production deployment

## Development Dependencies
- **Debug Mode**: Flask development server with auto-reload
- **CORS Configuration**: Wildcard origin access for development (should be restricted in production)