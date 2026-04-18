/**
 * edit-story.js - Edit Story Modal Module
 * Complete working version with all features
 */

// ============================================
// MODULE STATE
// ============================================

let currentStoryKey = null;
let currentStoryData = null;
let allSeries = [];

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatCurrencyFromNanos(nanos) {
    if (!nanos && nanos !== 0) return '$0.00';
    var dollars = nanos / 1000000000;
    return '$' + dollars.toFixed(2);
}

function formatNumberShort(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function minutesToHoursMinutes(minutes) {
    if (!minutes && minutes !== 0) return '0:00';
    var hours = Math.floor(minutes / 60);
    var mins = minutes % 60;
    if (hours > 0) {
        return hours + ':' + mins.toString().padStart(2, '0');
    }
    return mins + ':00';
}

function formatDateFromTimestamp(timestamp) {
    if (!timestamp) return '—';
    var date = new Date(timestamp);
    return date.toISOString().split('T')[0];
}

function formatDateTimeFromTimestamp(timestamp) {
    if (!timestamp) return '—';
    var date = new Date(timestamp);
    return date.toISOString().replace('T', ' ').substring(0, 16);
}

function formatPeriodDisplay(period) {
    if (!period) return '';
    var parts = period.split('-');
    var year = parseInt(parts[0]);
    var month = parseInt(parts[1]) - 1;
    var date = new Date(year, month, 1);
    return date.toLocaleString('default', { month: 'long', year: 'numeric' });
}

function getTodayDate() {
    var today = new Date();
    var yyyy = today.getFullYear();
    var mm = String(today.getMonth() + 1).padStart(2, '0');
    var dd = String(today.getDate()).padStart(2, '0');
    return yyyy + '-' + mm + '-' + dd;
}

function getNowTimestamp() {
    var now = new Date();
    var yyyy = now.getFullYear();
    var mm = String(now.getMonth() + 1).padStart(2, '0');
    var dd = String(now.getDate()).padStart(2, '0');
    var hh = String(now.getHours()).padStart(2, '0');
    var min = String(now.getMinutes()).padStart(2, '0');
    var ss = String(now.getSeconds()).padStart(2, '0');
    return yyyy + '-' + mm + '-' + dd + 'T' + hh + ':' + min + ':' + ss;
}

// ============================================
// CLEAR MONTHLY STATS TABLE
// ============================================

function clearMonthlyStatsTable() {
    var tbody = document.getElementById('monthlyStatsTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No monthly data available</td</tr>';
    }
}

// ============================================
// LOAD SERIES LIST
// ============================================

async function loadSeriesList() {
    try {
        var response = await fetch(API_BASE + '/series/');
        if (!response.ok) throw new Error('Failed to load series');
        
        var series = await response.json();
        allSeries = series;
        
        var seriesSelect = document.getElementById('editStorySeries');
        if (!seriesSelect) return;
        
        var currentValue = seriesSelect.value;
        seriesSelect.innerHTML = '<option value="">— No Series —</option>';
        
        for (var i = 0; i < series.length; i++) {
            var option = document.createElement('option');
            option.value = series[i].name;
            option.textContent = series[i].name;
            if (series[i].name === currentValue) option.selected = true;
            seriesSelect.appendChild(option);
        }
        
        var refreshBtn = document.querySelector('[data-action="refresh-series"]');
        if (refreshBtn) {
            refreshBtn.onclick = function() { loadSeriesList(); };
        }
    } catch (error) {
        console.error('Error loading series:', error);
    }
}

// ============================================
// BUILD MONTHLY STATS TABLE - NO DUMMY DATA
// ============================================

function buildMonthlyStatsTable(medium) {
    var tbody = document.getElementById('monthlyStatsTableBody');
    if (!tbody) return;
    
    // ALWAYS clear first
    tbody.innerHTML = '';
    
    // Check if we have real data
    var hasRealData = false;
    if (medium && medium.monthlyStats && medium.monthlyStats.length > 0) {
        for (var i = 0; i < medium.monthlyStats.length; i++) {
            var stat = medium.monthlyStats[i];
            if (stat && (stat.views > 0 || stat.reads > 0)) {
                hasRealData = true;
                break;
            }
        }
    }
    
    if (!hasRealData) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No monthly data available</td</tr>';
        return;
    }
    
    // Build earnings map
    var earningsMap = {};
    if (medium.monthlyEarnings && medium.monthlyEarnings.length > 0) {
        for (var j = 0; j < medium.monthlyEarnings.length; j++) {
            var earn = medium.monthlyEarnings[j];
            if (earn && earn.period) {
                earningsMap[earn.period] = earn.nanos || 0;
            }
        }
    }
    
    // Build table data
    var tableData = [];
    for (var k = 0; k < medium.monthlyStats.length; k++) {
        var stat = medium.monthlyStats[k];
        if (stat && stat.period) {
            tableData.push({
                period: stat.period,
                views: stat.views || 0,
                reads: stat.reads || 0,
                earnings: earningsMap[stat.period] || 0
            });
        }
    }
    
    if (tableData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No monthly data available</td</tr>';
        return;
    }
    
    // Sort descending (latest first)
    tableData.sort(function(a, b) {
        return b.period.localeCompare(a.period);
    });
    
    // Render rows
    for (var m = 0; m < tableData.length; m++) {
        var data = tableData[m];
        var row = tbody.insertRow();
        var periodDisplay = formatPeriodDisplay(data.period);
        row.innerHTML = '<td><strong>' + periodDisplay + '</strong></td>' +
            '<td class="text-end">' + formatNumberShort(data.views) + '</td>' +
            '<td class="text-end">' + formatNumberShort(data.reads) + '</td>' +
            '<td class="text-end">' + formatCurrencyFromNanos(data.earnings) + '</td>';
    }
}

// ============================================
// UPDATE UI ELEMENTS
// ============================================

function updateModalTitle(storyName) {
    var titleSpan = document.getElementById('editStoryModalTitle');
    if (titleSpan) titleSpan.textContent = storyName || 'Untitled';
}

function updateStatusBadge(status) {
    var badge = document.getElementById('storyStatusBadge');
    if (!badge) return;
    
    var statusClass = 'status-draft';
    var statusText = status || 'Draft';
    
    switch(status) {
        case 'Published': statusClass = 'status-published'; break;
        case 'Published Due': statusClass = 'status-published-due'; break;
        case 'Ready': statusClass = 'status-ready'; break;
        case 'Done': statusClass = 'status-done'; break;
        default: statusClass = 'status-draft';
    }
    
    badge.className = 'status-badge ' + statusClass;
    badge.textContent = statusText;
}

function updateLinkedInBadge() {
    var badge = document.getElementById('linkedinStatusBadge');
    var statusSelect = document.getElementById('editStoryLinkedinStatus');
    if (!badge || !statusSelect) return;
    
    var status = statusSelect.value;
    
    if (status === 'scheduled') {
        badge.className = 'linkedin-badge linkedin-scheduled';
        badge.innerHTML = '<i class="bi bi-calendar"></i> Scheduled';
    } else if (status === 'posted') {
        badge.className = 'linkedin-badge linkedin-posted';
        badge.innerHTML = '<i class="bi bi-check-circle-fill"></i> Posted';
    } else {
        badge.className = 'linkedin-badge linkedin-not-posted';
        badge.innerHTML = '<i class="bi bi-linkedin"></i> Not Posted';
    }
}

function updateUrlLinks() {
    var mediumUrl = document.getElementById('editStoryMediumUrl');
    var mediumLink = document.getElementById('editStoryMediumUrlLink');
    if (mediumUrl && mediumLink) {
        var url = mediumUrl.value;
        if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            mediumLink.href = url;
            mediumLink.style.display = 'inline-flex';
        } else {
            mediumLink.style.display = 'none';
        }
    }
    
    var linkedinUrl = document.getElementById('editStoryLinkedinUrl');
    var linkedinLink = document.getElementById('editStoryLinkedinUrlLink');
    if (linkedinUrl && linkedinLink) {
        var url = linkedinUrl.value;
        if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
            linkedinLink.href = url;
            linkedinLink.style.display = 'inline-flex';
        } else {
            linkedinLink.style.display = 'none';
        }
    }
}

// ============================================
// POPULATE MODAL FROM BACKEND DATA
// ============================================

function populateModalFromStory(story) {
    if (!story) return;
    
    // Clear monthly stats table first
    clearMonthlyStatsTable();
    
    currentStoryKey = story.key;
    currentStoryData = story;
    
    // Modal title
    updateModalTitle(story.name || story.title);
    
    // Hidden fields
    var keyField = document.getElementById('editStoryKey');
    if (keyField) keyField.value = story.key || '';
    
    var slugField = document.getElementById('editStoryUniqueSlug');
    if (slugField) slugField.value = story.uniqueSlug || '';
    
    // Display fields
    var pathDisplay = document.getElementById('editStoryPath');
    if (pathDisplay) pathDisplay.textContent = story.raw_path || story.rel_path || story.key || '';
    
    // Editable fields
    var nameInput = document.getElementById('editStoryName');
    if (nameInput) nameInput.value = story.name || story.title || '';
    
    var statusSelect = document.getElementById('editStoryStatus');
    if (statusSelect) statusSelect.value = story.status || 'Draft';
    updateStatusBadge(story.status);
    
    var seriesSelect = document.getElementById('editStorySeries');
    if (seriesSelect && story.series) seriesSelect.value = story.series;
    
    var createdDate = document.getElementById('editStoryCreatedDate');
    if (createdDate) createdDate.value = story.createdDate || '';
    
    var publishedDate = document.getElementById('editStoryPublishedDate');
    if (publishedDate) publishedDate.value = story.publishedDate || '';
    
    var dueDate = document.getElementById('editStoryDueDate');
    if (dueDate) dueDate.value = story.publishedDueDate || '';
    
    var tagsInput = document.getElementById('editStoryTags');
    if (tagsInput) {
        var tags = story.tags || [];
        tagsInput.value = tags.join(', ');
    }
    
    var mediumUrl = document.getElementById('editStoryMediumUrl');
    if (mediumUrl) mediumUrl.value = story.medium_url || '';
    
    var notes = document.getElementById('editStoryNotes');
    if (notes) notes.value = story.notes || '';
    
    var bookmarked = document.getElementById('editStoryBookmarked');
    if (bookmarked) bookmarked.checked = story.bookmarked === true;
    
    var lastUpdated = document.getElementById('editStoryLastUpdated');
    if (lastUpdated) lastUpdated.textContent = story.lastUpdated || 'Never';
    
    // LinkedIn fields
    var linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    if (linkedinStatus) linkedinStatus.value = story.linkedin_status || '';
    updateLinkedInBadge();
    
    var linkedinTimestamp = document.getElementById('editStoryLinkedinTimestamp');
    if (linkedinTimestamp) linkedinTimestamp.value = story.linkedin_timestamp || '';
    
    var linkedinImpressions = document.getElementById('editStoryLinkedinImpressions');
    if (linkedinImpressions) linkedinImpressions.value = story.linkedin_impressions || 0;
    
    var linkedinType = document.getElementById('editStoryLinkedinType');
    if (linkedinType) linkedinType.value = story.linkedin_type || 'Article';
    
    var linkedinUrl = document.getElementById('editStoryLinkedinUrl');
    if (linkedinUrl) linkedinUrl.value = story.linkedin_url || '';
    
    updateUrlLinks();
    
    // Medium stats
    var medium = story.medium;
    if (medium) {
        var mediumId = document.getElementById('mediumId');
        if (mediumId) mediumId.textContent = medium.id || '—';
        
        var uniqueSlug = document.getElementById('mediumUniqueSlug');
        if (uniqueSlug) uniqueSlug.textContent = medium.uniqueSlug || '—';
        
        var firstPublished = document.getElementById('mediumFirstPublished');
        if (firstPublished) firstPublished.textContent = formatDateFromTimestamp(medium.firstPublishedAt);
        
        var publication = document.getElementById('mediumPublication');
        if (publication) {
            var collectionName = (medium.collection && medium.collection.name) ? medium.collection.name : null;
            publication.textContent = collectionName || '—';
        }
        
        var responses = document.getElementById('mediumResponses');
        if (responses) responses.textContent = formatNumberShort(medium.responsesCount || 0);
        
        var readTime = document.getElementById('mediumReadTime');
        if (readTime) readTime.textContent = minutesToHoursMinutes(medium.readingTime || 0);
        
        var wordCount = document.getElementById('mediumWordCount');
        if (wordCount) wordCount.textContent = formatNumberShort(medium.wordCount || 0);
        
        var lastUpdate = document.getElementById('mediumLastUpdate');
        if (lastUpdate) lastUpdate.textContent = formatDateTimeFromTimestamp(medium.updatedAt);
        
        var votes = document.getElementById('mediumVotes');
        if (votes) votes.textContent = formatNumberShort(medium.voterCount || 0);
        
        var claps = document.getElementById('mediumClaps');
        if (claps) claps.textContent = formatNumberShort(medium.clapCount || 0);
        
        // Build monthly stats table from actual data
        buildMonthlyStatsTable(medium);
    }
    
    // Lifetime stats
    var lifetimeReads = document.getElementById('editStoryLifetimeReads');
    if (lifetimeReads) lifetimeReads.textContent = formatNumberShort(story.lifetime_reads || 0);
    
    var lifetimeViews = document.getElementById('editStoryLifetimeViews');
    if (lifetimeViews) lifetimeViews.textContent = formatNumberShort(story.lifetime_views || 0);
    
    var lifetimeClaps = document.getElementById('editStoryLifetimeClaps');
    if (lifetimeClaps) lifetimeClaps.textContent = formatNumberShort(story.lifetime_claps || 0);
    
    var presentationCount = document.getElementById('editStoryPresentationCount');
    if (presentationCount) presentationCount.textContent = formatNumberShort(story.presentation_count || 0);
}

// ============================================
// SAVE STORY
// ============================================

async function saveStoryEdit() {
    if (!currentStoryKey) {
        alert('No story selected');
        return;
    }
    
    var updateData = {
        name: document.getElementById('editStoryName')?.value || '',
        status: document.getElementById('editStoryStatus')?.value || 'Draft',
        series: document.getElementById('editStorySeries')?.value || null,
        createdDate: document.getElementById('editStoryCreatedDate')?.value || null,
        publishedDate: document.getElementById('editStoryPublishedDate')?.value || null,
        publishedDueDate: document.getElementById('editStoryDueDate')?.value || null,
        notes: document.getElementById('editStoryNotes')?.value || '',
        tags: (document.getElementById('editStoryTags')?.value || '').split(',').map(function(t) { return t.trim(); }).filter(function(t) { return t; }),
        bookmarked: document.getElementById('editStoryBookmarked')?.checked || false,
        medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions')?.value) || 0,
        linkedin_type: document.getElementById('editStoryLinkedinType')?.value || 'Article',
        linkedin_url: document.getElementById('editStoryLinkedinUrl')?.value || null
    };
    
    // Remove null/empty values
    for (var key in updateData) {
        if (updateData[key] === null || updateData[key] === '') {
            delete updateData[key];
        }
    }
    if (updateData.tags && updateData.tags.length === 0) delete updateData.tags;
    
    try {
        var encodedKey = encodeURIComponent(currentStoryKey);
        var response = await fetch(API_BASE + '/stories/story/by-key/' + encodedKey, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });
        
        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to save story');
        }
        
        var modalEl = document.getElementById('editStoryModal');
        if (modalEl) {
            var modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
        
        if (typeof window.loadStories === 'function') {
            await window.loadStories();
        }
        
        alert('Story saved successfully');
        
    } catch (error) {
        console.error('Error saving story:', error);
        alert('Error saving story: ' + error.message);
    }
}

// ============================================
// SYNC WITH MEDIUM
// ============================================

async function syncWithMedium() {
    var uniqueSlug = document.getElementById('editStoryUniqueSlug')?.value;
    if (!uniqueSlug) {
        alert('No story selected');
        return;
    }
    
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;
    
    var confirmMsg = '⚠️ WARNING: This will refresh the entire page and discard unsaved changes.\n\nSync stats from Medium for ' + year + '-' + String(month).padStart(2, '0') + '?';
    if (!confirm(confirmMsg)) return;
    
    var btn = document.querySelector('[data-action="sync-monthly-stats"]');
    var originalText = btn ? btn.innerHTML : 'Syncing...';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Syncing...';
    }
    
    try {
        var encodedSlug = encodeURIComponent(uniqueSlug);
        var response = await fetch(API_BASE + '/stories/fetch-lifetime-stats/' + encodedSlug + '?year=' + year + '&month=' + month, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to sync stats');
        
        window.location.reload();
        
    } catch (error) {
        console.error('Error syncing stats:', error);
        alert('Error syncing stats: ' + error.message);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

// ============================================
// ADD TO CURRENT MONTH
// ============================================

async function addStoryToCurrentMonth() {
    if (!currentStoryKey) {
        alert('No story selected');
        return;
    }
    
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;
    var monthStr = year + '-' + String(month).padStart(2, '0');
    var periodDisplay = formatPeriodDisplay(monthStr);
    
    if (!confirm('Add story to ' + periodDisplay + '?')) {
        return;
    }
    
    try {
        var encodedKey = encodeURIComponent(currentStoryKey);
        var response = await fetch(API_BASE + '/stories/ensure-story-in-month?story_key=' + encodedKey + '&year=' + year + '&month=' + month, {
            method: 'POST'
        });
        
        if (!response.ok) throw new Error('Failed to add story to month');
        
        alert('Story added to ' + periodDisplay + ' successfully');
        
    } catch (error) {
        console.error('Error adding to month:', error);
        alert('Error: ' + error.message);
    }
}

// ============================================
// LOAD STORY FROM BACKEND
// ============================================

async function loadStoryForEdit(encodedStoryKey) {
    try {
        var url = API_BASE + '/stories/story/' + encodedStoryKey;
        console.log('Loading story from:', url);
        
        var response = await fetch(url);
        if (!response.ok) {
            throw new Error('Story not found (HTTP ' + response.status + ')');
        }
        
        var story = await response.json();
        populateModalFromStory(story);
        
    } catch (error) {
        console.error('Error loading story:', error);
        alert('Error loading story: ' + error.message);
    }
}

// ============================================
// SET TODAY DATE
// ============================================

function setEditStoryTodayDate() {
    var createdDate = document.getElementById('editStoryCreatedDate');
    if (createdDate) {
        createdDate.value = getTodayDate();
    }
}

function setEditStoryNowLinkedinTimestamp() {
    var timestamp = document.getElementById('editStoryLinkedinTimestamp');
    if (timestamp) {
        timestamp.value = getNowTimestamp();
        updateLinkedInBadge();
    }
}

function clearEditStoryLinkedinTimestamp() {
    var timestamp = document.getElementById('editStoryLinkedinTimestamp');
    if (timestamp) {
        timestamp.value = '';
        updateLinkedInBadge();
    }
}

function clearAllEditStoryLinkedinData() {
    if (!confirm('Clear all LinkedIn data for this story?')) return;
    
    var statusSelect = document.getElementById('editStoryLinkedinStatus');
    var timestamp = document.getElementById('editStoryLinkedinTimestamp');
    var impressions = document.getElementById('editStoryLinkedinImpressions');
    var url = document.getElementById('editStoryLinkedinUrl');
    
    if (statusSelect) statusSelect.value = '';
    if (timestamp) timestamp.value = '';
    if (impressions) impressions.value = '0';
    if (url) url.value = '';
    
    updateLinkedInBadge();
    updateUrlLinks();
}

// ============================================
// PUBLIC API
// ============================================

window.EditStoryModal = {
    open: async function(encodedStoryKey) {
        if (!encodedStoryKey) {
            console.error('No story key provided');
            return;
        }
        
        await loadSeriesList();
        await loadStoryForEdit(encodedStoryKey);
        
        var modalEl = document.getElementById('editStoryModal');
        if (modalEl) {
            var modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    },
    
    close: function() {
        var modalEl = document.getElementById('editStoryModal');
        if (modalEl) {
            var modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
    }
};

// ============================================
// EXPOSE HELPER FUNCTIONS GLOBALLY
// ============================================

window.setEditStoryTodayDate = setEditStoryTodayDate;
window.setEditStoryNowLinkedinTimestamp = setEditStoryNowLinkedinTimestamp;
window.clearEditStoryLinkedinTimestamp = clearEditStoryLinkedinTimestamp;
window.clearAllEditStoryLinkedinData = clearAllEditStoryLinkedinData;
window.updateLinkedInBadge = updateLinkedInBadge;

// ============================================
// EVENT HANDLERS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Save button
    var saveBtn = document.querySelector('[data-action="save-story"]');
    if (saveBtn) {
        saveBtn.onclick = function(e) {
            e.preventDefault();
            saveStoryEdit();
        };
    }
    
    // Sync button
    var syncBtn = document.querySelector('[data-action="sync-monthly-stats"]');
    if (syncBtn) {
        syncBtn.onclick = function(e) {
            e.preventDefault();
            syncWithMedium();
        };
    }
    
    // Add to month button
    var addToMonthBtn = document.querySelector('[data-action="add-to-month"]');
    if (addToMonthBtn) {
        addToMonthBtn.onclick = function(e) {
            e.preventDefault();
            addStoryToCurrentMonth();
        };
    }
    
    // LinkedIn status change
    var linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    if (linkedinStatus) {
        linkedinStatus.addEventListener('change', updateLinkedInBadge);
    }
    
    // Set now button for LinkedIn timestamp
    var setNowBtn = document.getElementById('editStorySetNowLinkedinBtn');
    if (setNowBtn) {
        setNowBtn.onclick = function() { setEditStoryNowLinkedinTimestamp(); };
    }
    
    // Clear timestamp button
    var clearTimestampBtn = document.getElementById('editStoryClearLinkedinTimestampBtn');
    if (clearTimestampBtn) {
        clearTimestampBtn.onclick = function() { clearEditStoryLinkedinTimestamp(); };
    }
    
    // Clear all LinkedIn data button
    var clearAllBtn = document.getElementById('editStoryClearAllLinkedinBtn');
    if (clearAllBtn) {
        clearAllBtn.onclick = function() { clearAllEditStoryLinkedinData(); };
    }
    
    // Set today button for created date
    var setTodayBtn = document.getElementById('editStorySetTodayBtn');
    if (setTodayBtn) {
        setTodayBtn.onclick = function() { setEditStoryTodayDate(); };
    }
    
    // URL input listeners
    var mediumUrl = document.getElementById('editStoryMediumUrl');
    if (mediumUrl) {
        mediumUrl.addEventListener('input', updateUrlLinks);
        mediumUrl.addEventListener('change', updateUrlLinks);
    }
    
    var linkedinUrl = document.getElementById('editStoryLinkedinUrl');
    if (linkedinUrl) {
        linkedinUrl.addEventListener('input', updateUrlLinks);
        linkedinUrl.addEventListener('change', updateUrlLinks);
    }
});