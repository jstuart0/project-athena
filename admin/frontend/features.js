/**
 * Feature Flag Management UI
 *
 * Displays system features with toggle controls organized by category:
 * - Processing Layer (intent classification, multi-intent, conversation context)
 * - RAG Layer (weather, sports, airports)
 * - Optimization Layer (caching, MLX backend, streaming)
 * - Integration Layer (Home Assistant, clarifications)
 *
 * Features:
 * - Visual on/off indicators (green/gray toggle switches)
 * - Latency contribution display per feature
 * - Lock icon for required features (cannot be disabled)
 * - What-if analysis showing projected latency impact
 */

let featuresData = [];
let impactData = [];
let whatIfScenarios = [];

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
 * Load all features from backend
 */
async function loadFeatures() {
    try {
        const response = await fetch('/api/features', {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error(`Failed to load features: ${response.statusText}`);
        }

        featuresData = await response.json();
        console.log('Features loaded:', featuresData.length);

        // Load feature impact analysis and what-if scenarios in parallel
        await Promise.all([
            loadFeatureImpact(),
            loadWhatIfScenarios()
        ]);

        renderFeatures();
    } catch (error) {
        console.error('Failed to load features:', error);
        safeShowToast('Failed to load features', 'error');
        showFeaturesError(error.message);
    }
}

/**
 * Load feature impact analysis
 */
async function loadFeatureImpact() {
    try {
        const response = await fetch('/api/features/impact/analysis', {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            impactData = await response.json();
        }
    } catch (error) {
        console.error('Failed to load feature impact:', error);
    }
}

/**
 * Load what-if scenarios
 */
async function loadWhatIfScenarios() {
    try {
        const response = await fetch('/api/features/what-if/scenarios', {
            headers: getAuthHeaders()
        });

        if (response.ok) {
            whatIfScenarios = await response.json();
        }
    } catch (error) {
        console.error('Failed to load what-if scenarios:', error);
    }
}

/**
 * Toggle feature on/off
 */
async function toggleFeature(featureId) {
    try {
        const response = await fetch(`/api/features/${featureId}/toggle`, {
            method: 'PUT',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to toggle feature');
        }

        const updatedFeature = await response.json();

        // Update local data
        const index = featuresData.findIndex(f => f.id === featureId);
        if (index !== -1) {
            featuresData[index] = updatedFeature;
        }

        // Refresh displays
        await loadWhatIfScenarios();
        renderFeatures();

        const status = updatedFeature.enabled ? 'enabled' : 'disabled';
        safeShowToast(`Feature "${updatedFeature.display_name}" ${status}`, 'success');

    } catch (error) {
        console.error('Failed to toggle feature:', error);
        safeShowToast(error.message, 'error');

        // Reload features to restore correct state
        await loadFeatures();
    }
}

/**
 * Render features grouped by category
 */
function renderFeatures() {
    const container = document.getElementById('features-container');
    if (!container) return;

    if (featuresData.length === 0) {
        container.innerHTML = '<div class="empty-state">No features configured</div>';
        return;
    }

    // Group features by category
    const categories = {
        processing: [],
        rag: [],
        optimization: [],
        integration: []
    };

    featuresData.forEach(feature => {
        if (categories[feature.category]) {
            categories[feature.category].push(feature);
        }
    });

    const categoryNames = {
        processing: 'Processing Layer',
        rag: 'RAG Layer',
        optimization: 'Optimization Layer',
        integration: 'Integration Layer'
    };

    let html = '<div class="features-grid">';

    Object.keys(categories).forEach(categoryKey => {
        const features = categories[categoryKey];
        if (features.length === 0) return;

        // Sort by priority
        features.sort((a, b) => a.priority - b.priority);

        html += `
            <div class="feature-category">
                <h3>${categoryNames[categoryKey]}</h3>
                <div class="feature-list">
                    ${features.map(feature => renderFeatureCard(feature)).join('')}
                </div>
            </div>
        `;
    });

    html += '</div>';

    // Add what-if analysis section
    html += renderWhatIfAnalysis();

    // Add feature impact table
    html += renderFeatureImpact();

    container.innerHTML = html;
}

/**
 * Render individual feature card
 */
function renderFeatureCard(feature) {
    const isEnabled = feature.enabled;
    const isRequired = feature.required;
    const statusClass = isEnabled ? 'enabled' : 'disabled';
    const lockIcon = isRequired ? '🔒' : '';
    const latency = feature.avg_latency_ms ? `${feature.avg_latency_ms.toFixed(1)}ms` : 'N/A';
    const hitRate = feature.hit_rate ? `${(feature.hit_rate * 100).toFixed(0)}% hit` : '';

    return `
        <div class="feature-card ${statusClass} ${isRequired ? 'required' : ''}">
            <div class="feature-header">
                <div class="feature-name">
                    ${lockIcon} ${feature.display_name}
                </div>
                <div class="feature-toggle">
                    <label class="toggle-switch">
                        <input
                            type="checkbox"
                            ${isEnabled ? 'checked' : ''}
                            ${isRequired ? 'disabled' : ''}
                            onchange="toggleFeature(${feature.id})"
                        />
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
            <div class="feature-description">${feature.description || ''}</div>
            <div class="feature-metrics">
                <span class="metric-badge">⏱ ${latency}</span>
                ${hitRate ? `<span class="metric-badge">📊 ${hitRate}</span>` : ''}
            </div>
        </div>
    `;
}

/**
 * Render what-if analysis section
 */
function renderWhatIfAnalysis() {
    if (whatIfScenarios.length === 0) {
        return '';
    }

    const currentScenario = whatIfScenarios.find(s => s.scenario_name === 'Current Configuration');
    const currentLatency = currentScenario ? currentScenario.total_latency_ms : 0;

    return `
        <div class="what-if-section">
            <h3>What-If Analysis</h3>
            <p class="section-description">See how different feature configurations impact system latency</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Scenario</th>
                        <th>Description</th>
                        <th>Total Latency</th>
                        <th>Change</th>
                        <th>Percent</th>
                    </tr>
                </thead>
                <tbody>
                    ${whatIfScenarios.map(scenario => {
                        const changeClass = scenario.change_percent > 0 ? 'increase' :
                                          scenario.change_percent < 0 ? 'decrease' : 'neutral';
                        const changeSign = scenario.change_percent > 0 ? '+' : '';

                        return `
                            <tr class="${scenario.scenario_name === 'Current Configuration' ? 'current-scenario' : ''}">
                                <td><strong>${scenario.scenario_name}</strong></td>
                                <td>${scenario.description}</td>
                                <td class="metric-value">${scenario.total_latency_ms.toFixed(1)}ms</td>
                                <td class="metric-value ${changeClass}">
                                    ${changeSign}${scenario.change_from_current_ms.toFixed(1)}ms
                                </td>
                                <td class="metric-value ${changeClass}">
                                    ${changeSign}${scenario.change_percent.toFixed(1)}%
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Render feature impact table
 */
function renderFeatureImpact() {
    if (impactData.length === 0) {
        return '';
    }

    return `
        <div class="feature-impact-section">
            <h3>Feature Impact Analysis</h3>
            <p class="section-description">Average latency contribution per feature based on historical data</p>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Feature</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Avg Latency</th>
                        <th>% of Total</th>
                        <th>Request Count</th>
                    </tr>
                </thead>
                <tbody>
                    ${impactData.map(impact => {
                        const statusIcon = impact.enabled ? '✓' : '✗';
                        const statusClass = impact.enabled ? 'enabled' : 'disabled';

                        return `
                            <tr>
                                <td><strong>${impact.display_name}</strong></td>
                                <td><span class="tag tag-category">${impact.category}</span></td>
                                <td class="feature-status ${statusClass}">${statusIcon} ${impact.enabled ? 'On' : 'Off'}</td>
                                <td class="metric-value">${impact.avg_latency_ms.toFixed(1)}ms</td>
                                <td class="metric-value">${impact.percent_of_total.toFixed(1)}%</td>
                                <td class="metric-value">${impact.request_count.toLocaleString()}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

/**
 * Show error state
 */
function showFeaturesError(message) {
    const container = document.getElementById('features-container');
    if (container) {
        container.innerHTML = `<div class="error">Error: ${message}</div>`;
    }
}

/**
 * Initialize features page
 */
function initFeaturesPage() {
    console.log('Initializing features page');

    // Load features data
    loadFeatures();

    // Set up auto-refresh (every 30 seconds)
    setInterval(() => {
        loadFeatures();
    }, 30000);
}

// Export for external use
if (typeof window !== 'undefined') {
    window.toggleFeature = toggleFeature;
    window.initFeaturesPage = initFeaturesPage;
}
