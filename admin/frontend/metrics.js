/**
 * LLM Performance Metrics Viewer
 *
 * Displays performance metrics for LLM backends including:
 * - Tokens per second
 * - Latency
 * - Request counts
 * - Time-series visualization
 */

let metricsData = [];
let filteredMetrics = [];

/**
 * Get authentication headers
 */
function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

/**
 * Safe wrapper to call app.js showToast function
 */
function safeShowToast(message, type = 'info') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}

/**
 * Load metrics from backend
 */
async function loadMetrics(model = null, backend = null, limit = 100) {
    try {
        showMetricsLoading();

        // Build query params
        const params = new URLSearchParams();
        if (model) params.append('model', model);
        if (backend) params.append('backend', backend);
        params.append('limit', limit);

        const response = await fetch(`/api/llm-backends/metrics?${params}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`Failed to load metrics: ${response.statusText}`);
        }

        metricsData = await response.json();
        filteredMetrics = [...metricsData];

        renderMetrics();
        renderMetricsStats();
        renderMetricsChart();

        console.log('Metrics loaded successfully:', metricsData.length, 'records');
    } catch (error) {
        console.error('Failed to load metrics:', error);
        safeShowToast('Failed to load performance metrics', 'error');
        showMetricsError(error.message);
    }
}

/**
 * Show loading state
 */
function showMetricsLoading() {
    const container = document.getElementById('metrics-table-container');
    if (container) {
        container.innerHTML = '<div class="loading">Loading metrics...</div>';
    }

    const statsContainer = document.getElementById('metrics-stats-container');
    if (statsContainer) {
        statsContainer.innerHTML = '<div class="loading">Calculating statistics...</div>';
    }
}

/**
 * Show error state
 */
function showMetricsError(message) {
    const container = document.getElementById('metrics-table-container');
    if (container) {
        container.innerHTML = `<div class="error">Error: ${message}</div>`;
    }
}

/**
 * Render metrics table
 */
function renderMetrics() {
    const container = document.getElementById('metrics-table-container');
    if (!container) return;

    if (filteredMetrics.length === 0) {
        container.innerHTML = '<div class="empty-state">No metrics data available</div>';
        return;
    }

    const html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Model</th>
                    <th>Backend</th>
                    <th>Tokens/sec</th>
                    <th>Latency (s)</th>
                    <th>Tokens</th>
                    <th>Source</th>
                    <th>Intent</th>
                    <th>Session ID</th>
                </tr>
            </thead>
            <tbody>
                ${filteredMetrics.map(metric => `
                    <tr>
                        <td>${formatTimestamp(metric.timestamp)}</td>
                        <td><span class="tag tag-model">${metric.model}</span></td>
                        <td><span class="tag tag-backend">${metric.backend}</span></td>
                        <td class="metric-value">${metric.tokens_per_second.toFixed(2)}</td>
                        <td class="metric-value">${metric.latency_seconds.toFixed(3)}</td>
                        <td class="metric-value">${metric.tokens_generated}</td>
                        <td>${metric.source ? `<span class="tag tag-source">${metric.source}</span>` : '-'}</td>
                        <td>${metric.intent || '-'}</td>
                        <td class="session-id">${metric.session_id ? truncateId(metric.session_id) : '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

/**
 * Render metrics statistics
 */
function renderMetricsStats() {
    const container = document.getElementById('metrics-stats-container');
    if (!container || filteredMetrics.length === 0) {
        if (container) container.innerHTML = '';
        return;
    }

    // Calculate statistics
    const stats = calculateStats(filteredMetrics);

    const html = `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value">${stats.totalRequests}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Tokens/sec</div>
                <div class="stat-value">${stats.avgTokensPerSec.toFixed(2)}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Latency</div>
                <div class="stat-value">${stats.avgLatency.toFixed(3)}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Tokens</div>
                <div class="stat-value">${stats.totalTokens.toLocaleString()}</div>
            </div>
        </div>

        <div class="stats-breakdown">
            <h3>By Backend</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Backend</th>
                        <th>Requests</th>
                        <th>Avg Tokens/sec</th>
                        <th>Avg Latency (s)</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(stats.byBackend).map(([backend, data]) => `
                        <tr>
                            <td><span class="tag tag-backend">${backend}</span></td>
                            <td>${data.count}</td>
                            <td class="metric-value">${data.avgTokensPerSec.toFixed(2)}</td>
                            <td class="metric-value">${data.avgLatency.toFixed(3)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <h3>By Model</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Model</th>
                        <th>Requests</th>
                        <th>Avg Tokens/sec</th>
                        <th>Avg Latency (s)</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(stats.byModel).map(([model, data]) => `
                        <tr>
                            <td><span class="tag tag-model">${model}</span></td>
                            <td>${data.count}</td>
                            <td class="metric-value">${data.avgTokensPerSec.toFixed(2)}</td>
                            <td class="metric-value">${data.avgLatency.toFixed(3)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = html;
}

/**
 * Calculate statistics from metrics
 */
function calculateStats(metrics) {
    const stats = {
        totalRequests: metrics.length,
        avgTokensPerSec: 0,
        avgLatency: 0,
        totalTokens: 0,
        byBackend: {},
        byModel: {}
    };

    let totalTokensPerSec = 0;
    let totalLatency = 0;

    metrics.forEach(metric => {
        // Overall stats
        totalTokensPerSec += metric.tokens_per_second;
        totalLatency += metric.latency_seconds;
        stats.totalTokens += metric.tokens_generated;

        // By backend
        if (!stats.byBackend[metric.backend]) {
            stats.byBackend[metric.backend] = {
                count: 0,
                totalTokensPerSec: 0,
                totalLatency: 0,
                avgTokensPerSec: 0,
                avgLatency: 0
            };
        }
        stats.byBackend[metric.backend].count++;
        stats.byBackend[metric.backend].totalTokensPerSec += metric.tokens_per_second;
        stats.byBackend[metric.backend].totalLatency += metric.latency_seconds;

        // By model
        if (!stats.byModel[metric.model]) {
            stats.byModel[metric.model] = {
                count: 0,
                totalTokensPerSec: 0,
                totalLatency: 0,
                avgTokensPerSec: 0,
                avgLatency: 0
            };
        }
        stats.byModel[metric.model].count++;
        stats.byModel[metric.model].totalTokensPerSec += metric.tokens_per_second;
        stats.byModel[metric.model].totalLatency += metric.latency_seconds;
    });

    // Calculate averages
    stats.avgTokensPerSec = totalTokensPerSec / metrics.length;
    stats.avgLatency = totalLatency / metrics.length;

    // Calculate backend averages
    Object.keys(stats.byBackend).forEach(backend => {
        const data = stats.byBackend[backend];
        data.avgTokensPerSec = data.totalTokensPerSec / data.count;
        data.avgLatency = data.totalLatency / data.count;
    });

    // Calculate model averages
    Object.keys(stats.byModel).forEach(model => {
        const data = stats.byModel[model];
        data.avgTokensPerSec = data.totalTokensPerSec / data.count;
        data.avgLatency = data.totalLatency / data.count;
    });

    return stats;
}

/**
 * Render metrics chart (simple bar chart using CSS)
 */
function renderMetricsChart() {
    const container = document.getElementById('metrics-chart-container');
    if (!container || filteredMetrics.length === 0) {
        if (container) container.innerHTML = '';
        return;
    }

    // Get last 20 metrics for chart
    const chartData = filteredMetrics.slice(0, 20).reverse();
    const maxTokensPerSec = Math.max(...chartData.map(m => m.tokens_per_second));

    const html = `
        <div class="chart">
            <h3>Recent Performance (Last 20 Requests)</h3>
            <div class="chart-bars">
                ${chartData.map((metric, index) => {
                    const height = (metric.tokens_per_second / maxTokensPerSec) * 100;
                    return `
                        <div class="chart-bar-container" title="${metric.model} - ${metric.tokens_per_second.toFixed(2)} tokens/sec">
                            <div class="chart-bar" style="height: ${height}%"></div>
                            <div class="chart-label">${index + 1}</div>
                        </div>
                    `;
                }).join('')}
            </div>
            <div class="chart-legend">
                <span>Tokens per second (higher is better)</span>
            </div>
        </div>
    `;

    container.innerHTML = html;
}

/**
 * Apply filters to metrics
 */
function applyFilters() {
    const modelFilter = document.getElementById('filter-model')?.value || '';
    const backendFilter = document.getElementById('filter-backend')?.value || '';
    const limitFilter = parseInt(document.getElementById('filter-limit')?.value || '100');

    // Reload with filters
    loadMetrics(
        modelFilter || null,
        backendFilter || null,
        limitFilter
    );
}

/**
 * Clear all filters
 */
function clearFilters() {
    const modelFilter = document.getElementById('filter-model');
    const backendFilter = document.getElementById('filter-backend');
    const limitFilter = document.getElementById('filter-limit');

    if (modelFilter) modelFilter.value = '';
    if (backendFilter) backendFilter.value = '';
    if (limitFilter) limitFilter.value = '100';

    loadMetrics(null, null, 100);
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Truncate long IDs for display
 */
function truncateId(id) {
    if (!id) return '';
    return id.length > 12 ? id.substring(0, 12) + '...' : id;
}

/**
 * Initialize metrics page
 */
function initMetricsPage() {
    console.log('Initializing metrics page');

    // Load initial metrics
    loadMetrics();

    // Set up auto-refresh (every 30 seconds)
    setInterval(() => {
        const modelFilter = document.getElementById('filter-model')?.value || null;
        const backendFilter = document.getElementById('filter-backend')?.value || null;
        const limitFilter = parseInt(document.getElementById('filter-limit')?.value || '100');

        loadMetrics(modelFilter, backendFilter, limitFilter);
    }, 30000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Don't auto-init - wait for page to be shown
    });
} else {
    // Don't auto-init - wait for page to be shown
}
