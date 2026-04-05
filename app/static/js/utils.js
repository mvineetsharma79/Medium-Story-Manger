// ============================================
// Utility Functions
// ============================================

const API_BASE = '/api';

function getTodayDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function getNowTimestamp() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T${hh}:${min}:${ss}`;
}

function formatNumber(num) {
    if (!num && num !== 0) return '0';
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
    if (!total || total === 0) return 0;
    return Math.round((member / total) * 100);
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
    if (el && lastTime) {
        el.textContent = lastTime;
    }
}

function updateLeaderboardTotal() {
    if (!window.allStories || !Array.isArray(window.allStories)) {
        const countEl = document.getElementById('leaderboardCount');
        const amountEl = document.getElementById('leaderboardAmount');
        if (countEl) countEl.textContent = '0';
        if (amountEl) amountEl.textContent = '0.00';
        return;
    }
    
    const storiesWithLeaderboard = window.allStories.filter(s => s.leaderboard === true);
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

function clearDate(elementId) {
    const el = document.getElementById(elementId);
    if (el) el.value = '';
}

function formatDateForDisplay(dateStr) {
    if (!dateStr || dateStr === 'Unknown') return '';
    if (dateStr.includes('-')) return dateStr.split('T')[0];
    return '';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function truncateString(str, maxLength = 50) {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    return str.substring(0, maxLength) + '...';
}

function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// Make functions globally available
window.getTodayDate = getTodayDate;
window.getNowTimestamp = getNowTimestamp;
window.formatNumber = formatNumber;
window.formatTimestampForDisplay = formatTimestampForDisplay;
window.escapeHtml = escapeHtml;
window.calcMemberPercent = calcMemberPercent;
window.updateLastFetchTime = updateLastFetchTime;
window.loadLastFetchTime = loadLastFetchTime;
window.updateLeaderboardTotal = updateLeaderboardTotal;
window.setTodayDate = setTodayDate;
window.clearDate = clearDate;
window.formatDateForDisplay = formatDateForDisplay;
window.debounce = debounce;
window.truncateString = truncateString;
window.isValidUrl = isValidUrl;