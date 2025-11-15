/**
 * Conversation Context Management Functions
 * Phase 0-2: Database, Session Management, and Device Sessions
 */

// ============================================================================
// CONVERSATION SETTINGS
// ============================================================================

async function loadConversationSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/conversation/settings`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load conversation settings');
        }

        const data = await response.json();
        renderConversationSettings(data);

        // Load other sections
        loadClarificationTypes();
        loadSportsTeams();
        loadConversationAnalytics();

    } catch (error) {
        console.error('Failed to load conversation settings:', error);
        showError('Failed to load conversation settings');
    }
}

function renderConversationSettings(settings) {
    const container = document.getElementById('conversation-settings-container');

    container.innerHTML = `
        <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">Session Timeout (seconds)</label>
            <input type="number" id="session-timeout" value="${settings.session_timeout_seconds}"
                class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
            <p class="text-xs text-gray-500 mt-1">Time before session expires (default: 300 = 5 min)</p>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">Max Session Age (seconds)</label>
            <input type="number" id="max-session-age" value="${settings.max_session_age_seconds}"
                class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
            <p class="text-xs text-gray-500 mt-1">Maximum session lifetime (default: 86400 = 24 hours)</p>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">Max Context Messages</label>
            <input type="number" id="max-context-messages" value="${settings.max_context_messages}"
                class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
            <p class="text-xs text-gray-500 mt-1">Number of messages to include in context (default: 10)</p>
        </div>

        <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">Context Window Size</label>
            <input type="number" id="context-window-size" value="${settings.context_window_size}"
                class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
            <p class="text-xs text-gray-500 mt-1">Max characters in context window (default: 4000)</p>
        </div>

        <div class="flex items-center">
            <input type="checkbox" id="enable-session-context" ${settings.enable_session_context ? 'checked' : ''}
                class="w-4 h-4 bg-dark-bg border border-dark-border rounded">
            <label class="ml-2 text-sm text-gray-400">Enable Session Context</label>
        </div>

        <div class="flex items-center">
            <input type="checkbox" id="enable-clarification" ${settings.enable_clarification_system ? 'checked' : ''}
                class="w-4 h-4 bg-dark-bg border border-dark-border rounded">
            <label class="ml-2 text-sm text-gray-400">Enable Clarification System</label>
        </div>

        <div class="col-span-2 mt-4">
            <button onclick="saveConversationSettings()"
                class="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors">
                💾 Save Settings
            </button>
        </div>
    `;
}

async function saveConversationSettings() {
    try {
        const settings = {
            session_timeout_seconds: parseInt(document.getElementById('session-timeout').value),
            max_session_age_seconds: parseInt(document.getElementById('max-session-age').value),
            max_context_messages: parseInt(document.getElementById('max-context-messages').value),
            context_window_size: parseInt(document.getElementById('context-window-size').value),
            enable_session_context: document.getElementById('enable-session-context').checked,
            enable_clarification_system: document.getElementById('enable-clarification').checked
        };

        const response = await fetch(`${API_BASE}/api/conversation/settings`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            throw new Error('Failed to save settings');
        }

        showSuccess('Settings saved successfully');
        loadConversationSettings(); // Reload to show updated values

    } catch (error) {
        console.error('Failed to save settings:', error);
        showError('Failed to save conversation settings');
    }
}

// ============================================================================
// CLARIFICATION TYPES
// ============================================================================

async function loadClarificationTypes() {
    try {
        const response = await fetch(`${API_BASE}/api/conversation/clarification/types`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load clarification types');
        }

        const types = await response.json();
        renderClarificationTypes(types);

    } catch (error) {
        console.error('Failed to load clarification types:', error);
        showError('Failed to load clarification types');
    }
}

function renderClarificationTypes(types) {
    const container = document.getElementById('clarification-types-container');

    if (!types || types.length === 0) {
        container.innerHTML = '<p class="text-gray-400 text-sm">No clarification types configured. Click "Add Clarification Type" to create one.</p>';
        return;
    }

    container.innerHTML = types.map(type => `
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h4 class="font-medium text-white">${type.type_name}</h4>
                    <p class="text-sm text-gray-400 mt-1">${type.question_template}</p>
                </div>
                <span class="px-2 py-1 rounded text-xs ${type.enabled ? 'bg-green-900/30 text-green-400' : 'bg-gray-900/30 text-gray-400'}">
                    ${type.enabled ? 'Enabled' : 'Disabled'}
                </span>
            </div>
            ${type.example_response ? `
                <div class="mt-2 text-xs text-gray-500">
                    <span class="font-medium">Example:</span> ${type.example_response}
                </div>
            ` : ''}
        </div>
    `).join('');
}

function showCreateClarificationTypeModal() {
    const modal = document.createElement('div');
    modal.id = 'clarification-type-modal';
    modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
            <h3 class="text-lg font-semibold text-white mb-4">Create Clarification Type</h3>

            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Type Name</label>
                    <input type="text" id="new-clarification-type" placeholder="e.g., location"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Question Template</label>
                    <textarea id="new-clarification-question" placeholder="e.g., Which location did you mean?"
                        rows="2" class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white"></textarea>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Example Response (optional)</label>
                    <input type="text" id="new-clarification-example" placeholder="e.g., I meant Baltimore"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>

                <div class="flex items-center">
                    <input type="checkbox" id="new-clarification-enabled" checked
                        class="w-4 h-4 bg-dark-bg border border-dark-border rounded">
                    <label class="ml-2 text-sm text-gray-400">Enabled</label>
                </div>
            </div>

            <div class="flex gap-3 mt-6">
                <button onclick="createClarificationType()"
                    class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors">
                    Create
                </button>
                <button onclick="closeModal('clarification-type-modal')"
                    class="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
                    Cancel
                </button>
            </div>
        </div>
    `;

    document.getElementById('modals-container').appendChild(modal);
}

async function createClarificationType() {
    try {
        const data = {
            type_name: document.getElementById('new-clarification-type').value,
            question_template: document.getElementById('new-clarification-question').value,
            example_response: document.getElementById('new-clarification-example').value || null,
            enabled: document.getElementById('new-clarification-enabled').checked
        };

        const response = await fetch(`${API_BASE}/api/conversation/clarification/types`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to create clarification type');
        }

        showSuccess('Clarification type created');
        closeModal('clarification-type-modal');
        loadClarificationTypes();

    } catch (error) {
        console.error('Failed to create clarification type:', error);
        showError('Failed to create clarification type');
    }
}

// ============================================================================
// SPORTS TEAMS
// ============================================================================

async function loadSportsTeams() {
    try {
        const response = await fetch(`${API_BASE}/api/conversation/sports-teams`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load sports teams');
        }

        const teams = await response.json();
        renderSportsTeams(teams);

    } catch (error) {
        console.error('Failed to load sports teams:', error);
        showError('Failed to load sports teams');
    }
}

function renderSportsTeams(teams) {
    const container = document.getElementById('sports-teams-container');

    if (!teams || teams.length === 0) {
        container.innerHTML = '<p class="col-span-3 text-gray-400 text-sm">No sports teams configured. Click "Add Team" to create one.</p>';
        return;
    }

    container.innerHTML = teams.map(team => `
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h4 class="font-medium text-white">${team.team_name}</h4>
                    <p class="text-xs text-gray-400 mt-1">${team.sport}</p>
                </div>
            </div>
            <div class="space-y-1 text-xs">
                ${team.city ? `<div><span class="text-gray-500">City:</span> <span class="text-gray-300">${team.city}</span></div>` : ''}
                ${team.league ? `<div><span class="text-gray-500">League:</span> <span class="text-gray-300">${team.league}</span></div>` : ''}
                ${team.aliases && team.aliases.length > 0 ? `
                    <div class="mt-2">
                        <span class="text-gray-500">Aliases:</span>
                        <div class="flex flex-wrap gap-1 mt-1">
                            ${team.aliases.map(alias => `<span class="px-2 py-0.5 bg-blue-900/30 text-blue-400 rounded">${alias}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function showCreateSportsTeamModal() {
    const modal = document.createElement('div');
    modal.id = 'sports-team-modal';
    modal.className = 'fixed inset-0 bg-black/50 flex items-center justify-center z-50';
    modal.innerHTML = `
        <div class="bg-dark-card border border-dark-border rounded-lg p-6 w-full max-w-md">
            <h3 class="text-lg font-semibold text-white mb-4">Add Sports Team</h3>

            <div class="space-y-4">
                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Team Name</label>
                    <input type="text" id="new-team-name" placeholder="e.g., Baltimore Ravens"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Sport</label>
                    <select id="new-team-sport" class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                        <option value="nfl">NFL</option>
                        <option value="nba">NBA</option>
                        <option value="mlb">MLB</option>
                        <option value="nhl">NHL</option>
                        <option value="mls">MLS</option>
                        <option value="ncaa_football">NCAA Football</option>
                        <option value="ncaa_basketball">NCAA Basketball</option>
                    </select>
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">City</label>
                    <input type="text" id="new-team-city" placeholder="e.g., Baltimore"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">League (optional)</label>
                    <input type="text" id="new-team-league" placeholder="e.g., AFC North"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>

                <div>
                    <label class="block text-sm font-medium text-gray-400 mb-2">Aliases (comma-separated)</label>
                    <input type="text" id="new-team-aliases" placeholder="e.g., Ravens, Baltimore"
                        class="w-full px-3 py-2 bg-dark-bg border border-dark-border rounded-lg text-white">
                </div>
            </div>

            <div class="flex gap-3 mt-6">
                <button onclick="createSportsTeam()"
                    class="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors">
                    Create
                </button>
                <button onclick="closeModal('sports-team-modal')"
                    class="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
                    Cancel
                </button>
            </div>
        </div>
    `;

    document.getElementById('modals-container').appendChild(modal);
}

async function createSportsTeam() {
    try {
        const aliases = document.getElementById('new-team-aliases').value
            .split(',')
            .map(a => a.trim())
            .filter(a => a.length > 0);

        const data = {
            team_name: document.getElementById('new-team-name').value,
            sport: document.getElementById('new-team-sport').value,
            city: document.getElementById('new-team-city').value || null,
            league: document.getElementById('new-team-league').value || null,
            aliases: aliases.length > 0 ? aliases : null
        };

        const response = await fetch(`${API_BASE}/api/conversation/sports-teams`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to create sports team');
        }

        showSuccess('Sports team added');
        closeModal('sports-team-modal');
        loadSportsTeams();

    } catch (error) {
        console.error('Failed to create sports team:', error);
        showError('Failed to create sports team');
    }
}

// ============================================================================
// ANALYTICS
// ============================================================================

async function loadConversationAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/api/conversation/analytics`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to load analytics');
        }

        const analytics = await response.json();
        renderConversationAnalytics(analytics);

    } catch (error) {
        console.error('Failed to load analytics:', error);
        // Don't show error - analytics might not exist yet
        const container = document.getElementById('conversation-analytics-container');
        container.innerHTML = '<p class="col-span-4 text-gray-400 text-sm">No analytics data available yet.</p>';
    }
}

function renderConversationAnalytics(analytics) {
    const container = document.getElementById('conversation-analytics-container');

    if (!analytics || analytics.length === 0) {
        container.innerHTML = '<p class="col-span-4 text-gray-400 text-sm">No analytics data available yet.</p>';
        return;
    }

    // Calculate totals
    const totalConversations = analytics.reduce((sum, a) => sum + a.conversation_count, 0);
    const totalMessages = analytics.reduce((sum, a) => sum + a.total_messages, 0);
    const avgPerConversation = totalMessages / totalConversations || 0;
    const totalClarifications = analytics.reduce((sum, a) => sum + a.clarification_count, 0);

    container.innerHTML = `
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="text-2xl font-bold text-blue-400">${totalConversations}</div>
            <div class="text-sm text-gray-400 mt-1">Total Conversations</div>
        </div>
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="text-2xl font-bold text-green-400">${totalMessages}</div>
            <div class="text-sm text-gray-400 mt-1">Total Messages</div>
        </div>
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="text-2xl font-bold text-purple-400">${avgPerConversation.toFixed(1)}</div>
            <div class="text-sm text-gray-400 mt-1">Avg Messages/Conv</div>
        </div>
        <div class="bg-dark-bg border border-dark-border rounded-lg p-4">
            <div class="text-2xl font-bold text-yellow-400">${totalClarifications}</div>
            <div class="text-sm text-gray-400 mt-1">Clarifications</div>
        </div>
    `;
}
