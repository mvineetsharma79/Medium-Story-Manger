// ============================================
// Utility Functions
// ============================================

const API_BASE = '/api';

function getTodayDate() {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
}

function getNowTimestamp() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
}

function formatNumber(num) {
    if (!num) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatTimestampForDisplay(timestamp) {
    if (!timestamp) return '';
    return timestamp.replace('T', ' ').substring(0, 16);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function calcMemberPercent(member, total) {
    return total > 0 ? Math.round((member / total) * 100) : 0;
}

function updateLastFetchTime() {
    const now = new Date().toLocaleString();
    localStorage.setItem('lastFetchTime', now);
    const el = document.getElementById('lastFetchTime');
    if (el) el.textContent = now;
}

function loadLastFetchTime() {
    const lastTime = localStorage.getItem('lastFetchTime');
    const el = document.getElementById('lastFetchTime');
    if (el && lastTime) el.textContent = lastTime;
}

function updateLeaderboardTotal() {
    const storiesWithLeaderboard = window.allStories ? window.allStories.filter(s => s.leaderboard === true) : [];
    const totalNanos = storiesWithLeaderboard.reduce((sum, s) => sum + (s.leaderboard_nanos || 0), 0);
    const countEl = document.getElementById('leaderboardCount');
    const amountEl = document.getElementById('leaderboardAmount');
    if (countEl) countEl.textContent = storiesWithLeaderboard.length;
    if (amountEl) amountEl.textContent = (totalNanos / 1000000000).toFixed(2);
}

function setTodayDate(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.value = getTodayDate();
}