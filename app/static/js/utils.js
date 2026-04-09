// ============================================
// UTILITIES - Shared functions across all screens
// ============================================

const API_BASE = '/api';

// ============================================
// STRING UTILITIES
// ============================================

function normalizeTitle(title) {
    if (!title) return '';
    let normalized = decodeURIComponent(title);
    normalized = normalized.toLowerCase();
    normalized = normalized.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
    normalized = normalized.replace(/[^\w\s-]/g, '');
    normalized = normalized.replace(/[\s]+/g, '-');
    normalized = normalized.replace(/-+/g, '-');
    normalized = normalized.replace(/^-|-$/g, '');
    return normalized.substring(0, 100);
}

function normalizeMediumUrl(url) {
    if (!url) return '';
    return url.replace(/\/$/, '');
}

function getStoryIdentifier(story) {
    // Priority: medium_url > name (NOT key)
    if (story.medium_url && story.medium_url !== 'null' && story.medium_url !== 'undefined') {
        return normalizeMediumUrl(story.medium_url);
    }
    // Use name, not key
    if (story.name) {
        return story.name;
    }
    return '';
}

function encodeStoryIdentifier(identifier) {
    if (!identifier) return '';
    return encodeURIComponent(identifier);
}

function decodeStoryIdentifier(encoded) {
    if (!encoded) return '';
    return decodeURIComponent(encoded);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// NUMBER FORMATTING
// ============================================

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatCurrency(nanos) {
    if (!nanos && nanos !== 0) return '$0.00';
    const dollars = nanos / 1000000000;
    return `$${dollars.toFixed(2)}`;
}

function formatReadTime(minutes) {
    if (!minutes || minutes === 0) return '0:00';
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
        return `${hours}:${mins.toString().padStart(2, '0')}`;
    }
    return `${mins}:00`;
}

function calcPercent(part, total) {
    if (!total || total === 0) return 0;
    return Math.round((part / total) * 100);
}

// ============================================
// DATE/TIME UTILITIES
// ============================================

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

function getCurrentYearMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function formatTimestampForDisplay(timestamp) {
    if (!timestamp) return '';
    return timestamp.replace('T', ' ').substring(0, 16);
}

// ============================================
// UI UTILITIES
// ============================================

function showLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'none';
}

function showToast(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    if (type === 'error') {
        alert(message);
    }
}

// ============================================
// VALIDATION
// ============================================

function isValidYearMonth(value) {
    if (!value) return false;
    return /^\d{4}-\d{2}$/.test(value);
}

function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

// ============================================
// EXTRACT POST ID FROM MEDIUM URL
// ============================================

function extractPostIdFromUrl(mediumUrl) {
    if (!mediumUrl) return null;
    const url = mediumUrl.replace(/\/$/, '');
    const parts = url.split('/');
    const lastPart = parts[parts.length - 1];
    if (lastPart && lastPart.includes('-')) {
        const postId = lastPart.split('-').pop();
        if (postId && postId.length >= 10) return postId;
    }
    if (lastPart && lastPart.length >= 10 && /^[a-f0-9]+$/.test(lastPart)) {
        return lastPart;
    }
    return null;
}

function formatCurrency(nanos) {
    if (!nanos && nanos !== 0) return '$0.00';
    const dollars = nanos / 1000000000;
    return `$${dollars.toFixed(2)}`;
}

// Make functions globally available
window.API_BASE = API_BASE;
window.normalizeTitle = normalizeTitle;
window.normalizeMediumUrl = normalizeMediumUrl;
window.getStoryIdentifier = getStoryIdentifier;
window.encodeStoryIdentifier = encodeStoryIdentifier;
window.decodeStoryIdentifier = decodeStoryIdentifier;
window.escapeHtml = escapeHtml;
window.formatNumber = formatNumber;
window.formatCurrency = formatCurrency;
window.formatReadTime = formatReadTime;
window.calcPercent = calcPercent;
window.getTodayDate = getTodayDate;
window.getNowTimestamp = getNowTimestamp;
window.getCurrentYearMonth = getCurrentYearMonth;
window.formatTimestampForDisplay = formatTimestampForDisplay;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showToast = showToast;
window.isValidYearMonth = isValidYearMonth;
window.isValidUrl = isValidUrl;
window.extractPostIdFromUrl = extractPostIdFromUrl;