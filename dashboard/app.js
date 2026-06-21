/**
 * Sentinel Dashboard - Live alert feed and triage visualization
 */

// Uses current origin so this works on HF Spaces, Railway, localhost, etc.
const API_BASE = window.location.origin;
const POLL_INTERVAL = 2000; // 2 seconds
const MAX_ALERTS_DISPLAY = 100;

let currentFilter = 'all';
let allAlerts = [];
let pollTimeout;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    startPolling();
});

function setupEventListeners() {
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.dataset.filter;
            renderAlerts();
        });
    });

    // Modal close
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.getElementById('detail-modal').addEventListener('click', (e) => {
        if (e.target.id === 'detail-modal') closeModal();
    });
}

function startPolling() {
    fetchAlerts();
    fetchStats();
    pollTimeout = setInterval(() => {
        fetchAlerts();
        fetchStats();
    }, POLL_INTERVAL);
}

async function fetchAlerts() {
    try {
        const response = await fetch(`${API_BASE}/alerts?limit=${MAX_ALERTS_DISPLAY}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        allAlerts = data.alerts || [];

        updateConnectionStatus(true);
        renderAlerts();
    } catch (error) {
        console.error('Error fetching alerts:', error);
        updateConnectionStatus(false);
    }
}

async function fetchStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const stats = await response.json();
        updateStats(stats);
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

function updateConnectionStatus(connected) {
    const dot = document.getElementById('connection-status');
    const text = document.getElementById('status-text');

    if (connected) {
        dot.classList.add('connected');
        dot.classList.remove('disconnected');
        text.textContent = 'Connected';
    } else {
        dot.classList.add('disconnected');
        dot.classList.remove('connected');
        text.textContent = 'Disconnected';
    }
}

function updateStats(stats) {
    document.getElementById('stat-total').textContent = stats.total_alerts || 0;
    document.getElementById('stat-auto').textContent = stats.auto_resolve_count || 0;
    document.getElementById('stat-escalate').textContent = stats.escalate_count || 0;
    document.getElementById('stat-info').textContent = stats.needs_more_info_count || 0;

    const avgConf = stats.avg_confidence || 0;
    document.getElementById('stat-confidence').textContent =
        avgConf > 0 ? (avgConf * 100).toFixed(0) + '%' : '--';
}

function renderAlerts() {
    const container = document.getElementById('alerts-container');

    // Filter alerts
    const filtered = allAlerts.filter(alert => {
        if (currentFilter === 'all') return true;
        return alert.action === currentFilter;
    });

    if (filtered.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No alerts match the current filter.</p></div>`;
        return;
    }

    container.innerHTML = filtered.map(alert => createAlertElement(alert)).join('');

    // Add click handlers
    container.querySelectorAll('.alert-item').forEach(el => {
        el.addEventListener('click', () => showAlertDetail(el.dataset.alertId));
    });
}

function createAlertElement(alert) {
    const action = alert.action || 'unknown';
    const severity = alert.severity || 'medium';
    const timestamp = new Date(alert.created_at).toLocaleTimeString();
    const confidence = alert.confidence ? (alert.confidence * 100).toFixed(0) : '0';

    return `
        <div class="alert-item ${action}" data-alert-id="${alert.alert_id}">
            <div class="alert-header">
                <div>
                    <div class="alert-source">${alert.source}</div>
                    <div class="alert-message">${escapeHtml(alert.message)}</div>
                </div>
                <span class="alert-severity severity-${severity}">${severity}</span>
            </div>
            <div class="alert-footer">
                <span class="action-badge ${action}">${formatAction(action)}</span>
                <span class="confidence-score">Confidence: ${confidence}%</span>
                <span class="timestamp">${timestamp}</span>
            </div>
        </div>
    `;
}

async function showAlertDetail(alertId) {
    try {
        const response = await fetch(`${API_BASE}/alerts/${alertId}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const alert = await response.json();
        displayAlertModal(alert);
    } catch (error) {
        console.error('Error fetching alert detail:', error);
        alert('Failed to load alert details');
    }
}

function displayAlertModal(alert) {
    const modal = document.getElementById('detail-modal');
    const body = document.getElementById('modal-body');

    const metadata = JSON.parse(alert.metadata || '{}');
    const metadataHtml = Object.entries(metadata).length > 0
        ? `
            <table class="metadata-table">
                <thead>
                    <tr>
                        <th>Key</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    ${Object.entries(metadata)
                        .map(
                            ([key, value]) => `
                        <tr>
                            <td>${escapeHtml(key)}</td>
                            <td>${escapeHtml(JSON.stringify(value))}</td>
                        </tr>
                    `
                        )
                        .join('')}
                </tbody>
            </table>
        `
        : '<p><em>No metadata</em></p>';

    const timestamp = new Date(alert.created_at).toLocaleString();
    const severity = alert.severity || 'medium';
    const action = alert.action || 'unknown';
    const confidence = alert.confidence ? (alert.confidence * 100).toFixed(1) : '0';

    body.innerHTML = `
        <div class="modal-header">
            <div class="modal-title">Alert Detail</div>
            <div class="alert-source">${alert.source}</div>
        </div>

        <div class="modal-section">
            <div class="modal-section-title">Alert Information</div>
            <table class="metadata-table">
                <tbody>
                    <tr>
                        <td><strong>Alert ID</strong></td>
                        <td><code>${escapeHtml(alert.alert_id)}</code></td>
                    </tr>
                    <tr>
                        <td><strong>Severity</strong></td>
                        <td><span class="alert-severity severity-${severity}">${severity}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Message</strong></td>
                        <td>${escapeHtml(alert.message)}</td>
                    </tr>
                    <tr>
                        <td><strong>Received</strong></td>
                        <td>${timestamp}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="modal-section">
            <div class="modal-section-title">Metadata</div>
            ${metadataHtml}
        </div>

        <div class="modal-section">
            <div class="modal-section-title">Triage Decision</div>
            <table class="metadata-table">
                <tbody>
                    <tr>
                        <td><strong>Action</strong></td>
                        <td><span class="action-badge ${action}">${formatAction(action)}</span></td>
                    </tr>
                    <tr>
                        <td><strong>Confidence</strong></td>
                        <td>${confidence}%</td>
                    </tr>
                    <tr>
                        <td><strong>Reasoning</strong></td>
                        <td>${escapeHtml(alert.reasoning)}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="modal-section">
            <div class="modal-section-title">Claude Reasoning Trace</div>
            <div class="trace-box">${escapeHtml(alert.trace)}</div>
        </div>
    `;

    modal.classList.add('show');
}

function closeModal() {
    document.getElementById('detail-modal').classList.remove('show');
}

function formatAction(action) {
    return action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (pollTimeout) clearInterval(pollTimeout);
});
