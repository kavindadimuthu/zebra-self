# Project Sentinel Web Dashboard

A modular, enhanced web dashboard implementation for Project Sentinel retail intelligence system.

## Architecture

The web dashboard has been reorganized into a clean, modular architecture:

```
src/web_dashboard/
├── __init__.py              # Module exports and main interfaces
├── controller.py            # Dashboard controller and manager
├── server.py               # HTTP web server implementation
├── api/                    # RESTful API layer
│   ├── __init__.py
│   └── endpoints.py        # API endpoint handlers
├── static/                 # Frontend assets
│   ├── css/
│   │   └── styles.css      # Enhanced dashboard styles
│   └── js/
│       └── dashboard.js    # Dashboard JavaScript functionality
└── templates/              # HTML templates
    └── index.html          # Main dashboard template
```

## Features

### Real-time Monitoring
- **Live Data Updates**: Auto-refresh every 5 seconds
- **Connection Status**: Visual indicator of server connectivity
- **System Health**: Monitor detection engine, data streams, RFID, and POS systems

### Alert Management
- **Severity-based Filtering**: Critical, warning, and info alerts
- **Real-time Notifications**: New alerts appear immediately
- **Alert Details**: Station ID, product SKU, timestamps, and severity levels

### Station Analytics
- **Queue Monitoring**: Customer count and average wait times
- **Station Status**: Active, maintenance, or error states
- **Performance Metrics**: Transaction rates and service levels

### Visual Analytics
- **Interactive Charts**: Detection trends, queue analytics, transaction volume
- **Key Performance Indicators**: Visual metrics cards with trend indicators
- **System Performance**: Processing rates, uptime, and event counts

## Usage

### Basic Usage

```python
from web_dashboard import WebDashboard

# Create and start web dashboard
dashboard = WebDashboard(detection_engine, host='localhost', port=8080)
dashboard.start()

print(f"Dashboard available at: {dashboard.get_url()}")
```

### Using Dashboard Manager

```python
from web_dashboard import DashboardManager

# Create manager for multiple dashboard types
manager = DashboardManager(detection_engine)

# Start web dashboard
manager.start_web_dashboard(host='0.0.0.0', port=8080)

# Start console dashboard (optional)
manager.start_console_dashboard()

# Get web URL
print(f"Web dashboard: {manager.get_web_url()}")
```

### Backward Compatibility

The enhanced web dashboard maintains backward compatibility with existing code:

```python
# This still works with the new implementation
from dashboard import WebDashboard

dashboard = WebDashboard(detection_engine)
dashboard.start()
```

## API Endpoints

The web dashboard provides a comprehensive REST API:

- `GET /` - Main dashboard interface
- `GET /api/dashboard-data` - Complete dashboard data
- `GET /api/alerts` - Recent alerts (with optional filtering)
- `GET /api/stations` - Station status and queue info
- `GET /api/system-status` - System health and performance
- `GET /api/metrics` - Key performance metrics
- `GET /api/queue` - Queue analytics
- `GET /api/charts` - Chart data for visualizations

### API Parameters

Most endpoints support optional query parameters:
- `limit` - Limit number of results (default: 20-50)
- `severity` - Filter by alert severity (critical, warning, info)

## Configuration

### Environment Variables

- `DASHBOARD_HOST` - Server host (default: localhost)
- `DASHBOARD_PORT` - Server port (default: 8080)
- `REFRESH_INTERVAL` - Dashboard refresh rate in ms (default: 5000)

### Customization

The dashboard can be customized by:
1. Modifying CSS in `static/css/styles.css`
2. Updating JavaScript in `static/js/dashboard.js`
3. Editing HTML template in `templates/index.html`
4. Extending API endpoints in `api/endpoints.py`

## Performance Features

- **Efficient Data Loading**: Structured API responses
- **Error Handling**: Graceful degradation when detection engine is unavailable
- **Demo Mode**: Fallback data for testing without full system
- **Optimized Assets**: Minified and cached static resources

## Browser Compatibility

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Dependencies

- Python 3.9+
- Chart.js (CDN)
- Lucide Icons (CDN)
- Modern web browser with ES6 support

## Development

### Testing the Dashboard

```python
# Run the server module directly for testing
python src/web_dashboard/server.py

# Or test the controller
python src/web_dashboard/controller.py
```

### Adding New Features

1. **New API Endpoints**: Add methods to `api/endpoints.py`
2. **UI Components**: Update `templates/index.html` and `static/js/dashboard.js`
3. **Styling**: Modify `static/css/styles.css`
4. **Integration**: Update `controller.py` for new dashboard types

## Migration from Legacy

The new web dashboard automatically replaces the old implementation when imported. No code changes required for basic usage.

### Key Improvements

1. **Better Organization**: Separated concerns for maintainability
2. **Enhanced Error Handling**: Robust fallback mechanisms
3. **Improved Performance**: Optimized data loading and rendering
4. **Modern UI**: Enhanced visual design and user experience
5. **Extended API**: Comprehensive data endpoints
6. **Real-time Updates**: Better live data refresh

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all files are in the correct directory structure
2. **Port Conflicts**: Change the port number if 8080 is in use
3. **Permission Errors**: Run with appropriate permissions for network binding
4. **Browser Issues**: Clear cache and ensure modern browser support

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

This will show detailed information about requests, responses, and errors.