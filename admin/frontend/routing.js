/**
 * Intent Routing Management
 *
 * Manages intent classification patterns, routing configuration, and provider routing.
 */

// Global state
let patternsData = [];
let routingData = [];
let providerRoutingData = [];
let patternsSortField = 'category';
let patternsSortAsc = true;

/**
 * Get authentication headers for API requests
 */
function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

/**
 * Load all intent routing data
 */
async function loadIntentRoutingData() {
    try {
        // Show loading state
        showPatternsLoading();
        showRoutingLoading();
        showProviderRoutingLoading();

        // Load all data in parallel
        const [patterns, routing, providers] = await Promise.all([
            fetch('/api/intent-routing/patterns', { headers: getAuthHeaders() }).then(r => r.json()),
            fetch('/api/intent-routing/routing', { headers: getAuthHeaders() }).then(r => r.json()),
            fetch('/api/intent-routing/providers', { headers: getAuthHeaders() }).then(r => r.json())
        ]);

        patternsData = patterns;
        routingData = routing;

        // Transform provider routing data: group by intent_category
        providerRoutingData = groupProvidersByIntent(providers);

        // Render all sections
        renderPatterns();
        renderRouting();
        renderProviderRouting();

        console.log('Intent routing data loaded successfully');
    } catch (error) {
        console.error('Failed to load intent routing data:', error);
        safeShowToast('Failed to load intent routing data', 'error');
    }
}

/**
 * Group provider routing data by intent category
 */
function groupProvidersByIntent(providersList) {
    if (!Array.isArray(providersList)) return [];

    const grouped = {};

    // Group providers by intent_category
    providersList.forEach(item => {
        if (!grouped[item.intent_category]) {
            grouped[item.intent_category] = {
                intent_category: item.intent_category,
                providers: []
            };
        }
        grouped[item.intent_category].providers.push(item.provider_name);
    });

    // Convert to array and sort providers by priority
    return Object.values(grouped);
}

/**
 * Patterns Management
 */
function showPatternsLoading() {
    const tbody = document.getElementById('patterns-table-body');
    tbody.innerHTML = `
        <tr>
            <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                <div class="text-2xl mb-2">⏳</div>
                <p>Loading patterns...</p>
            </td>
        </tr>
    `;
}

function renderPatterns() {
    const tbody = document.getElementById('patterns-table-body');

    if (!patternsData || patternsData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                    <div class="text-2xl mb-2">📋</div>
                    <p>No patterns configured</p>
                </td>
            </tr>
        `;
        return;
    }

    // Sort patterns
    const sorted = [...patternsData].sort((a, b) => {
        let aVal = a[patternsSortField];
        let bVal = b[patternsSortField];

        if (patternsSortField === 'priority') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        } else {
            aVal = String(aVal).toLowerCase();
            bVal = String(bVal).toLowerCase();
        }

        if (patternsSortAsc) {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });

    // Render rows
    tbody.innerHTML = sorted.map(pattern => `
        <tr class="bg-dark-card hover:bg-dark-border transition-colors">
            <td class="px-6 py-4">
                <span class="px-3 py-1 rounded-full text-xs font-semibold ${getCategoryBadgeClass(pattern.intent_category)}">
                    ${pattern.intent_category}
                </span>
            </td>
            <td class="px-6 py-4 text-white">${escapeHtml(pattern.keyword)}</td>
            <td class="px-6 py-4 text-gray-400">${pattern.priority || 'N/A'}</td>
            <td class="px-6 py-4">
                <div class="flex gap-2">
                    <button onclick="editPattern(${pattern.id})"
                        class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors">
                        Edit
                    </button>
                    <button onclick="deletePattern(${pattern.id})"
                        class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm transition-colors">
                        Delete
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function getCategoryBadgeClass(category) {
    const colors = {
        'event_search': 'bg-purple-500/20 text-purple-300',
        'general': 'bg-blue-500/20 text-blue-300',
        'news': 'bg-green-500/20 text-green-300',
        'local_business': 'bg-yellow-500/20 text-yellow-300',
        'weather': 'bg-cyan-500/20 text-cyan-300',
        'sports': 'bg-orange-500/20 text-orange-300',
        'flights': 'bg-indigo-500/20 text-indigo-300',
        'airports': 'bg-pink-500/20 text-pink-300'
    };
    return colors[category] || 'bg-gray-500/20 text-gray-300';
}

function sortPatterns(field) {
    if (patternsSortField === field) {
        patternsSortAsc = !patternsSortAsc;
    } else {
        patternsSortField = field;
        patternsSortAsc = true;
    }

    // Update sort indicators
    document.querySelectorAll('[id^="sort-"]').forEach(el => {
        el.textContent = '↕️';
    });
    document.getElementById(`sort-${field}`).textContent = patternsSortAsc ? '⬆️' : '⬇️';

    renderPatterns();
}

function filterPatterns() {
    const searchTerm = document.getElementById('pattern-search').value.toLowerCase();

    if (!searchTerm) {
        renderPatterns();
        return;
    }

    const filtered = patternsData.filter(p =>
        p.intent_category.toLowerCase().includes(searchTerm) ||
        p.keyword.toLowerCase().includes(searchTerm)
    );

    const tbody = document.getElementById('patterns-table-body');
    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-8 text-center text-gray-400">
                    <div class="text-2xl mb-2">🔍</div>
                    <p>No patterns match your search</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(pattern => `
        <tr class="bg-dark-card hover:bg-dark-border transition-colors">
            <td class="px-6 py-4">
                <span class="px-3 py-1 rounded-full text-xs font-semibold ${getCategoryBadgeClass(pattern.intent_category)}">
                    ${pattern.intent_category}
                </span>
            </td>
            <td class="px-6 py-4 text-white">${escapeHtml(pattern.keyword)}</td>
            <td class="px-6 py-4 text-gray-400">${pattern.priority || 'N/A'}</td>
            <td class="px-6 py-4">
                <div class="flex gap-2">
                    <button onclick="editPattern(${pattern.id})"
                        class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors">
                        Edit
                    </button>
                    <button onclick="deletePattern(${pattern.id})"
                        class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-sm transition-colors">
                        Delete
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function showCreatePatternModal() {
    const modalHtml = `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
                <h3 class="text-xl font-semibold text-white mb-4">Add Intent Pattern</h3>

                <form onsubmit="createPattern(event)" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Intent Category</label>
                        <select id="pattern-category" required
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="">Select category...</option>
                            <option value="event_search">Event Search</option>
                            <option value="general">General</option>
                            <option value="news">News</option>
                            <option value="local_business">Local Business</option>
                            <option value="weather">Weather</option>
                            <option value="sports">Sports</option>
                            <option value="flights">Flights</option>
                            <option value="airports">Airports</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Keyword</label>
                        <input type="text" id="pattern-keyword" required
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g., concert, game, forecast">
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Priority (optional)</label>
                        <input type="number" id="pattern-priority" min="0" max="100"
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="0-100 (higher = more important)">
                    </div>

                    <div class="flex gap-3 pt-4">
                        <button type="submit"
                            class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                            Create Pattern
                        </button>
                        <button type="button" onclick="closeModal()"
                            class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.getElementById('modals-container').innerHTML = modalHtml;
}

async function createPattern(event) {
    event.preventDefault();

    const category = document.getElementById('pattern-category').value;
    const keyword = document.getElementById('pattern-keyword').value;
    const priority = document.getElementById('pattern-priority').value;

    try {
        const response = await fetch('/api/intent-routing/patterns', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                intent_category: category,
                keyword: keyword,
                priority: priority ? parseInt(priority) : null
            })
        });

        if (!response.ok) throw new Error('Failed to create pattern');

        safeShowToast('Pattern created successfully', 'success');
        closeModal();
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to create pattern:', error);
        safeShowToast('Failed to create pattern', 'error');
    }
}

async function deletePattern(id) {
    if (!confirm('Are you sure you want to delete this pattern?')) return;

    try {
        const response = await fetch(`/api/intent-routing/patterns/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error('Failed to delete pattern');

        safeShowToast('Pattern deleted successfully', 'success');
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to delete pattern:', error);
        safeShowToast('Failed to delete pattern', 'error');
    }
}

/**
 * Routing Configuration Management
 */
function showRoutingLoading() {
    const container = document.getElementById('routing-container');
    container.innerHTML = `
        <div class="col-span-2 text-center text-gray-400 py-8">
            <div class="text-2xl mb-2">⏳</div>
            <p>Loading routing rules...</p>
        </div>
    `;
}

function renderRouting() {
    const container = document.getElementById('routing-container');

    if (!routingData || routingData.length === 0) {
        container.innerHTML = `
            <div class="col-span-2 text-center text-gray-400 py-8">
                <div class="text-2xl mb-2">📋</div>
                <p>No routing rules configured</p>
            </div>
        `;
        return;
    }

    container.innerHTML = routingData.map(rule => `
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="flex justify-between items-start mb-3">
                <span class="px-3 py-1 rounded-full text-xs font-semibold ${getCategoryBadgeClass(rule.intent_category)}">
                    ${rule.intent_category}
                </span>
                <button onclick="deleteRouting('${rule.intent_category}')"
                    class="text-red-400 hover:text-red-300 text-sm">
                    🗑️
                </button>
            </div>

            <div class="space-y-2 text-sm">
                ${rule.use_rag ? `
                    <div class="flex items-center gap-2">
                        <span class="text-green-400">✓</span>
                        <span class="text-gray-400">Use RAG Service</span>
                    </div>
                ` : ''}

                ${rule.rag_service_url ? `
                    <div class="text-gray-400">
                        <span class="font-medium">RAG URL:</span>
                        <code class="text-xs bg-dark-card px-2 py-1 rounded ml-2">${rule.rag_service_url}</code>
                    </div>
                ` : ''}

                ${rule.use_web_search ? `
                    <div class="flex items-center gap-2">
                        <span class="text-blue-400">✓</span>
                        <span class="text-gray-400">Use Web Search</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function showCreateRoutingModal() {
    const modalHtml = `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
                <h3 class="text-xl font-semibold text-white mb-4">Add Routing Rule</h3>

                <form onsubmit="createRouting(event)" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Intent Category</label>
                        <select id="routing-category" required
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="">Select category...</option>
                            <option value="event_search">Event Search</option>
                            <option value="general">General</option>
                            <option value="news">News</option>
                            <option value="local_business">Local Business</option>
                            <option value="weather">Weather</option>
                            <option value="sports">Sports</option>
                            <option value="flights">Flights</option>
                            <option value="airports">Airports</option>
                        </select>
                    </div>

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="routing-use-rag"
                            class="w-4 h-4 bg-dark-bg border border-dark-border rounded">
                        <label for="routing-use-rag" class="text-sm text-gray-400">Use RAG Service</label>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">RAG Service URL (optional)</label>
                        <input type="url" id="routing-rag-url"
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="http://localhost:8010">
                    </div>

                    <div class="flex items-center gap-2">
                        <input type="checkbox" id="routing-use-web"
                            class="w-4 h-4 bg-dark-bg border border-dark-border rounded">
                        <label for="routing-use-web" class="text-sm text-gray-400">Use Web Search</label>
                    </div>

                    <div class="flex gap-3 pt-4">
                        <button type="submit"
                            class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                            Create Rule
                        </button>
                        <button type="button" onclick="closeModal()"
                            class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.getElementById('modals-container').innerHTML = modalHtml;
}

async function createRouting(event) {
    event.preventDefault();

    const category = document.getElementById('routing-category').value;
    const useRag = document.getElementById('routing-use-rag').checked;
    const ragUrl = document.getElementById('routing-rag-url').value;
    const useWeb = document.getElementById('routing-use-web').checked;

    try {
        const response = await fetch('/api/intent-routing/routing', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                intent_category: category,
                use_rag: useRag,
                rag_service_url: ragUrl || null,
                use_web_search: useWeb
            })
        });

        if (!response.ok) throw new Error('Failed to create routing rule');

        safeShowToast('Routing rule created successfully', 'success');
        closeModal();
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to create routing rule:', error);
        safeShowToast('Failed to create routing rule', 'error');
    }
}

async function deleteRouting(category) {
    if (!confirm(`Delete routing rule for ${category}?`)) return;

    try {
        const response = await fetch(`/api/intent-routing/routing/${category}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error('Failed to delete routing rule');

        safeShowToast('Routing rule deleted successfully', 'success');
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to delete routing rule:', error);
        safeShowToast('Failed to delete routing rule', 'error');
    }
}

/**
 * Provider Routing Management
 */
function showProviderRoutingLoading() {
    const container = document.getElementById('provider-routing-container');
    container.innerHTML = `
        <div class="text-center text-gray-400 py-8">
            <div class="text-2xl mb-2">⏳</div>
            <p>Loading provider routing...</p>
        </div>
    `;
}

function renderProviderRouting() {
    const container = document.getElementById('provider-routing-container');

    if (!providerRoutingData || providerRoutingData.length === 0) {
        container.innerHTML = `
            <div class="text-center text-gray-400 py-8">
                <div class="text-2xl mb-2">📋</div>
                <p>No provider routing configured</p>
            </div>
        `;
        return;
    }

    container.innerHTML = providerRoutingData.map(mapping => `
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="flex justify-between items-start mb-3">
                <span class="px-3 py-1 rounded-full text-xs font-semibold ${getCategoryBadgeClass(mapping.intent_category)}">
                    ${mapping.intent_category}
                </span>
                <button onclick="deleteProviderRouting('${mapping.intent_category}')"
                    class="text-red-400 hover:text-red-300 text-sm">
                    🗑️
                </button>
            </div>

            <div class="space-y-2">
                <div class="text-sm text-gray-400 font-medium">Providers (in order):</div>
                <div class="flex flex-wrap gap-2">
                    ${mapping.providers.map((provider, idx) => `
                        <span class="px-2 py-1 bg-dark-card text-gray-300 text-xs rounded">
                            ${idx + 1}. ${provider}
                        </span>
                    `).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

function showCreateProviderRoutingModal() {
    const modalHtml = `
        <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
                <h3 class="text-xl font-semibold text-white mb-4">Add Provider Mapping</h3>

                <form onsubmit="createProviderRouting(event)" class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Intent Category</label>
                        <select id="provider-category" required
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="">Select category...</option>
                            <option value="event_search">Event Search</option>
                            <option value="general">General</option>
                            <option value="news">News</option>
                            <option value="local_business">Local Business</option>
                        </select>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-400 mb-2">Providers (comma-separated, in priority order)</label>
                        <input type="text" id="provider-list" required
                            class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder="ticketmaster, eventbrite, duckduckgo">
                        <p class="text-xs text-gray-500 mt-1">Available: ticketmaster, eventbrite, duckduckgo, brave</p>
                    </div>

                    <div class="flex gap-3 pt-4">
                        <button type="submit"
                            class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors">
                            Create Mapping
                        </button>
                        <button type="button" onclick="closeModal()"
                            class="flex-1 px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors">
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;

    document.getElementById('modals-container').innerHTML = modalHtml;
}

async function createProviderRouting(event) {
    event.preventDefault();

    const category = document.getElementById('provider-category').value;
    const providerList = document.getElementById('provider-list').value;
    const providers = providerList.split(',').map(p => p.trim()).filter(p => p);

    try {
        const response = await fetch('/api/intent-routing/providers', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                intent_category: category,
                providers: providers
            })
        });

        if (!response.ok) throw new Error('Failed to create provider mapping');

        safeShowToast('Provider mapping created successfully', 'success');
        closeModal();
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to create provider mapping:', error);
        safeShowToast('Failed to create provider mapping', 'error');
    }
}

async function deleteProviderRouting(category) {
    if (!confirm(`Delete provider mapping for ${category}?`)) return;

    try {
        const response = await fetch(`/api/intent-routing/providers/${category}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if (!response.ok) throw new Error('Failed to delete provider mapping');

        safeShowToast('Provider mapping deleted successfully', 'success');
        loadIntentRoutingData();
    } catch (error) {
        console.error('Failed to delete provider mapping:', error);
        safeShowToast('Failed to delete provider mapping', 'error');
    }
}

/**
 * Utility Functions
 */
function closeModal() {
    document.getElementById('modals-container').innerHTML = '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Safe wrapper to call app.js showToast function.
 * Uses different name to avoid creating window.showToast property.
 */
function safeShowToast(message, type = 'info') {
    // Try to call the global showToast from app.js
    if (typeof window.showToast === 'function') {
        window.safeShowToast(message, type);
    } else {
        // Fallback to console if showToast not available yet
        console.log(`[${type}] ${message}`);
    }
}

console.log('Intent Routing JS loaded');
