class ProjectSentinelDashboard {
    constructor() {
        this.refreshInterval = 5000; // 5 seconds
        this.connected = false;
        this.charts = {};
        this.startTime = Date.now();
        
        this.init();
    }

    async init() {
        this.initializeLucideIcons();
        this.setupEventListeners();
        this.initializeCharts();
        
        // Initial data load
        await this.fetchDashboardData();
        
        // Start real-time updates
        this.startDataRefresh();
    }

    initializeLucideIcons() {
        // Initialize Lucide icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    setupEventListeners() {
        // Alert filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.filterAlerts(e.target.dataset.filter);
            });
        });

        // Analytics timeframe selector
        document.getElementById('analytics-timeframe')?.addEventListener('change', (e) => {
            this.updateAnalyticsChart(e.target.value);
        });
    }

    async fetchDashboardData() {
        try {
            const response = await fetch('/api/dashboard-data');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            this.updateConnectionStatus(true);
            this.updateMetrics(data.metrics);
            this.updateAlerts(data.alerts);
            this.updateStations(data.stations);
            this.updateCharts(data.chart_data);
            
            return data;
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            this.updateConnectionStatus(false);
            return null;
        }
    }

    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connection-status');
        const systemStatusElement = document.getElementById('system-status');
        
        if (connected) {
            statusElement.className = 'connection-status connected';
            statusElement.innerHTML = '<i data-lucide="wifi" class="connection-icon"></i><span>Connected</span>';
            systemStatusElement.className = 'status-indicator healthy';
            systemStatusElement.innerHTML = '<i data-lucide="check-circle" class="status-icon"></i><span>System Healthy</span>';
        } else {
            statusElement.className = 'connection-status disconnected';
            statusElement.innerHTML = '<i data-lucide="wifi-off" class="connection-icon"></i><span>Disconnected</span>';
            systemStatusElement.className = 'status-indicator error';
            systemStatusElement.innerHTML = '<i data-lucide="alert-circle" class="status-icon"></i><span>Connection Lost</span>';
        }
        
        // Refresh icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    updateMetrics(data) {
        if (!data) return;

        // Update key metrics
        document.getElementById('active-alerts').textContent = data.metrics?.active_alerts || 0;
        document.getElementById('queue-customers').textContent = data.metrics?.queue_customers || 0;
        document.getElementById('transaction-rate').textContent = data.metrics?.transaction_rate || 0;
        document.getElementById('inventory-issues').textContent = data.metrics?.inventory_issues || 0;

        // Update metric changes
        document.getElementById('alerts-change').textContent = `+${data.metrics?.alerts_change || 0} this hour`;
        document.getElementById('queue-change').textContent = `Avg wait: ${data.metrics?.avg_wait_time || 0}s`;
        document.getElementById('transaction-change').textContent = 'Last 5 min';
        document.getElementById('inventory-change').textContent = 'Items flagged';

        // Update queue metrics
        document.getElementById('avg-wait-time').textContent = `${data.queue?.avg_wait_time || 0}s`;
        document.getElementById('peak-queue-length').textContent = data.queue?.peak_length || 0;
        document.getElementById('service-rate').textContent = `${data.queue?.service_rate || 0}/min`;

        // Update system health
        document.getElementById('events-processed').textContent = data.system?.events_processed || 0;
        document.getElementById('processing-rate').textContent = `${data.system?.processing_rate || 0}/sec`;
        document.getElementById('system-uptime').textContent = this.formatUptime();
    }

    updateAlerts(alerts) {
        if (!alerts) return;

        const container = document.getElementById('alerts-container');
        
        // Clear existing alerts except the welcome message
        const existingAlerts = container.querySelectorAll('.alert-item:not(.welcome)');
        existingAlerts.forEach(alert => alert.remove());

        // Add new alerts
        alerts.slice(0, 10).forEach(alert => {
            const alertElement = this.createAlertElement(alert);
            container.appendChild(alertElement);
        });
    }

    createAlertElement(alert) {
        const div = document.createElement('div');
        div.className = `alert-item ${alert.severity || 'info'}`;
        
        const iconMap = {
            'critical': 'alert-triangle',
            'warning': 'alert-circle',
            'info': 'info',
            'success': 'check-circle'
        };

        const icon = iconMap[alert.severity] || 'info';
        const timeStr = this.formatTime(alert.timestamp);

        div.innerHTML = `
            <div class="alert-content">
                <div class="alert-header">
                    <i data-lucide="${icon}" class="alert-icon"></i>
                    <span class="alert-type">${alert.event_name || 'Alert'}</span>
                    <span class="alert-time">${timeStr}</span>
                </div>
                <div class="alert-message">${this.formatAlertMessage(alert)}</div>
                ${alert.station_id ? `<div class="alert-station">Station: ${alert.station_id}</div>` : ''}
            </div>
        `;

        return div;
    }

    formatAlertMessage(alert) {
        const data = alert.event_data || {};
        
        switch (data.event_name) {
            case 'Scan Avoidance':
                return `Item ${data.product_sku} detected in scan area but not scanned`;
            case 'Weight Discrepancy':
                return `Expected ${data.expected_weight}g, actual ${data.actual_weight}g for ${data.product_sku}`;
            case 'Long Queue':
                return `Queue length: ${data.customer_count} customers`;
            case 'Barcode Switching':
                return `Possible switching: ${data.actual_sku} scanned as ${data.scanned_sku}`;
            case 'Inventory Discrepancy':
                return `${data.SKU}: Expected ${data.Expected_Inventory}, Found ${data.Actual_Inventory}`;
            case 'System Crash':
                return `Station offline for ${data.duration_seconds}s`;
            default:
                return alert.message || 'Alert detected';
        }
    }

    updateStations(stations) {
        if (!stations) return;

        const container = document.getElementById('stations-grid');
        container.innerHTML = '';

        Object.entries(stations).forEach(([stationId, station]) => {
            const stationElement = this.createStationElement(stationId, station);
            container.appendChild(stationElement);
        });
    }

    createStationElement(stationId, station) {
        const div = document.createElement('div');
        div.className = `station-card ${station.status?.toLowerCase() || 'inactive'}`;
        
        const statusIcon = station.status === 'Active' ? 'check-circle' : 'x-circle';
        const customerCount = station.queue_length || 0;
        const waitTime = station.avg_wait_time || 0;

        div.innerHTML = `
            <div class="station-header">
                <h3>${stationId}</h3>
                <i data-lucide="${statusIcon}" class="station-status-icon"></i>
            </div>
            <div class="station-metrics">
                <div class="station-metric">
                    <span class="metric-label">Queue</span>
                    <span class="metric-value">${customerCount}</span>
                </div>
                <div class="station-metric">
                    <span class="metric-label">Wait</span>
                    <span class="metric-value">${waitTime}s</span>
                </div>
                <div class="station-metric">
                    <span class="metric-label">Status</span>
                    <span class="metric-value">${station.status || 'Unknown'}</span>
                </div>
            </div>
        `;

        return div;
    }

    initializeCharts() {
        // Detection Analytics Chart
        const detectionCtx = document.getElementById('detection-chart')?.getContext('2d');
        if (detectionCtx) {
            this.charts.detection = new Chart(detectionCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Scan Avoidance',
                            data: [],
                            borderColor: '#ff6b6b',
                            backgroundColor: 'rgba(255, 107, 107, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Weight Discrepancy',
                            data: [],
                            borderColor: '#4ecdc4',
                            backgroundColor: 'rgba(78, 205, 196, 0.1)',
                            fill: true
                        },
                        {
                            label: 'Queue Issues',
                            data: [],
                            borderColor: '#45b7d1',
                            backgroundColor: 'rgba(69, 183, 209, 0.1)',
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }

        // Queue Performance Chart
        const queueCtx = document.getElementById('queue-chart')?.getContext('2d');
        if (queueCtx) {
            this.charts.queue = new Chart(queueCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Average Wait Time (seconds)',
                        data: [],
                        backgroundColor: 'rgba(69, 183, 209, 0.8)',
                        borderColor: '#45b7d1',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    updateCharts(data) {
        if (!data) return;

        // Update detection chart
        if (this.charts.detection && data.chart_data) {
            const chartData = data.chart_data.detection || {};
            this.charts.detection.data.labels = chartData.labels || [];
            this.charts.detection.data.datasets.forEach((dataset, index) => {
                dataset.data = chartData.datasets?.[index]?.data || [];
            });
            this.charts.detection.update('none');
        }

        // Update queue chart
        if (this.charts.queue && data.chart_data) {
            const queueData = data.chart_data.queue || {};
            this.charts.queue.data.labels = queueData.labels || [];
            this.charts.queue.data.datasets[0].data = queueData.data || [];
            this.charts.queue.update('none');
        }
    }

    filterAlerts(filter) {
        const alerts = document.querySelectorAll('.alert-item');
        alerts.forEach(alert => {
            if (filter === 'all' || alert.classList.contains(filter)) {
                alert.style.display = 'block';
            } else {
                alert.style.display = 'none';
            }
        });
    }

    formatTime(timestamp) {
        if (!timestamp) return 'Unknown';
        const date = new Date(timestamp);
        const now = new Date();
        const diff = (now - date) / 1000; // seconds

        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        return `${Math.floor(diff / 3600)}h ago`;
    }

    formatUptime() {
        const uptime = (Date.now() - this.startTime) / 1000; // seconds
        const hours = Math.floor(uptime / 3600);
        const minutes = Math.floor((uptime % 3600) / 60);
        const seconds = Math.floor(uptime % 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }

    async startDataRefresh() {
        const refreshData = async () => {
            const data = await this.fetchDashboardData();
            if (data) {
                this.updateMetrics(data);
                this.updateAlerts(data.alerts);
                this.updateStations(data.stations);
                this.updateCharts(data);
            }
        };

        // Initial load
        await refreshData();

        // Set up periodic refresh
        setInterval(refreshData, this.refreshInterval);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new ProjectSentinelDashboard();
});

// Utility functions for demo mode
window.generateDemoData = function() {
    return {
        metrics: {
            active_alerts: Math.floor(Math.random() * 10) + 1,
            queue_customers: Math.floor(Math.random() * 15) + 2,
            transaction_rate: Math.floor(Math.random() * 30) + 10,
            inventory_issues: Math.floor(Math.random() * 5),
            alerts_change: Math.floor(Math.random() * 5),
            avg_wait_time: Math.floor(Math.random() * 120) + 30
        },
        alerts: [
            {
                timestamp: new Date().toISOString(),
                event_data: {
                    event_name: 'Scan Avoidance',
                    station_id: 'SCC1',
                    product_sku: 'PRD_F_01'
                },
                severity: 'warning'
            },
            {
                timestamp: new Date(Date.now() - 60000).toISOString(),
                event_data: {
                    event_name: 'Weight Discrepancy',
                    station_id: 'SCC2',
                    product_sku: 'PRD_B_01',
                    expected_weight: 150,
                    actual_weight: 200
                },
                severity: 'critical'
            }
        ],
        stations: {
            'SCC1': {
                status: 'Active',
                queue_length: 3,
                avg_wait_time: 45
            },
            'SCC2': {
                status: 'Active',
                queue_length: 1,
                avg_wait_time: 20
            },
            'SCC3': {
                status: 'Inactive',
                queue_length: 0,
                avg_wait_time: 0
            }
        },
        queue: {
            avg_wait_time: 35,
            peak_length: 8,
            service_rate: 12
        },
        system: {
            events_processed: 1247,
            processing_rate: 15
        },
        chart_data: {
            detection: {
                labels: ['10:00', '10:05', '10:10', '10:15', '10:20'],
                datasets: [
                    { data: [2, 1, 3, 0, 1] },
                    { data: [1, 2, 1, 2, 0] },
                    { data: [0, 1, 2, 1, 1] }
                ]
            },
            queue: {
                labels: ['SCC1', 'SCC2', 'SCC3'],
                data: [45, 20, 0]
            }
        }
    };
};