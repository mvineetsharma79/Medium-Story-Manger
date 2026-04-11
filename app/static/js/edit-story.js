/**
 * edit-story.js - Edit Story Modal Module
 * 
 * Handles the edit story modal functionality including:
 * - Loading story data into the modal
 * - Saving story metadata and LinkedIn data
 * - Syncing stats with Medium API
 * - Displaying Medium read-only statistics
 * - Rendering monthly stats table
 * 
 * No inline HTML, no IIFE - pure module pattern
 */

// ============================================
// MODULE STATE (Private via closure)
// ============================================

let currentStoryKey = null;
let currentStoryUniqueSlug = null;
let currentYear = null;
let currentMonth = null;
let allSeries = [];

// ============================================
// HELPER FUNCTIONS
// ============================================

function formatCurrencyFromNanos(nanos) {
    if (!nanos && nanos !== 0) return '$0.00';
    const dollars = nanos / 1000000000;
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
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
        return hours + ':' + mins.toString().padStart(2, '0');
    }
    return mins + ':00';
}

function formatDateFromTimestamp(timestamp) {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toISOString().split('T')[0];
}

function formatDateTimeFromTimestamp(timestamp) {
    if (!timestamp) return '—';
    const date = new Date(timestamp);
    return date.toISOString().replace('T', ' ').substring(0, 16);
}

function getCurrentYearMonth() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    return year + '-' + month;
}

function formatPeriodDisplay(period) {
    if (!period) return '';
    var parts = period.split('-');
    var year = parseInt(parts[0]);
    var month = parseInt(parts[1]) - 1;
    var date = new Date(year, month, 1);
    return date.toLocaleString('default', { month: 'long', year: 'numeric' });
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
            var s = series[i];
            var option = document.createElement('option');
            option.value = s.name;
            option.textContent = s.name;
            if (s.name === currentValue) option.selected = true;
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
// LOAD AVAILABLE MONTHS
// ============================================

async function loadAvailableMonths() {
    try {
        var response = await fetch(API_BASE + '/stories/months');
        if (!response.ok) throw new Error('Failed to load months');
        
        var data = await response.json();
        var months = data.months || [];
        
        var monthSelector = document.getElementById('monthStatsSelector');
        if (!monthSelector) return;
        
        monthSelector.innerHTML = '<option value="">Select month...</option>';
        for (var i = 0; i < months.length; i++) {
            var month = months[i];
            var option = document.createElement('option');
            option.value = month;
            option.textContent = formatPeriodDisplay(month);
            monthSelector.appendChild(option);
        }
        
        var currentYM = getCurrentYearMonth();
        if (months.indexOf(currentYM) !== -1) {
            monthSelector.value = currentYM;
        }
        
        monthSelector.onchange = function() {
            var selectedMonth = monthSelector.value;
            if (selectedMonth && currentStoryUniqueSlug) {
                updateMonthlyStatsTableForMonth(selectedMonth);
            }
        };
        
    } catch (error) {
        console.error('Error loading months:', error);
    }
}

// ============================================
// UPDATE MONTHLY STATS TABLE FOR SPECIFIC MONTH
// ============================================

async function updateMonthlyStatsTableForMonth(yearmonth) {
    if (!currentStoryUniqueSlug) return;
    
    try {
        var encodedSlug = encodeURIComponent(currentStoryUniqueSlug);
        var response = await fetch(API_BASE + '/stories/stats/' + encodedSlug + '/' + yearmonth);
        if (!response.ok) throw new Error('Failed to fetch monthly stats');
        
        var stats = await response.json();
        renderSingleMonthStats(stats, yearmonth);
        
    } catch (error) {
        console.error('Error fetching monthly stats:', error);
        var tbody = document.getElementById('monthlyStatsTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-2">Failed to load stats</td></tr>';
        }
    }
}

function renderSingleMonthStats(stats, yearmonth) {
    var tbody = document.getElementById('monthlyStatsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    var row = tbody.insertRow();
    row.innerHTML = '<td><strong>' + formatPeriodDisplay(yearmonth) + '</strong></td>' +
        '<td class="text-end">' + formatNumberShort(stats.views || 0) + '</td>' +
        '<td class="text-end">' + formatNumberShort(stats.reads || 0) + '</td>' +
        '<td class="text-end">' + formatCurrencyFromNanos(stats.medium_earnings || 0) + '</td>';
}

// ============================================
// BUILD MONTHLY STATS TABLE
// ============================================

function buildMonthlyStatsTable(medium) {
    var tbody = document.getElementById('monthlyStatsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!medium || !medium.monthlyStats || medium.monthlyStats.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No monthly data available</td></tr>';
        return;
    }
    
    var earningsMap = {};
    if (medium.monthlyEarnings && Array.isArray(medium.monthlyEarnings)) {
        for (var i = 0; i < medium.monthlyEarnings.length; i++) {
            var earning = medium.monthlyEarnings[i];
            if (earning.period) {
                earningsMap[earning.period] = earning.nanos || 0;
            }
        }
    }
    
    var tableData = [];
    for (var j = 0; j < medium.monthlyStats.length; j++) {
        var stat = medium.monthlyStats[j];
        if (stat.period) {
            tableData.push({
                period: stat.period,
                views: stat.views || 0,
                reads: stat.reads || 0,
                earnings: earningsMap[stat.period] || 0
            });
        }
    }
    
    tableData.sort(function(a, b) {
        return b.period.localeCompare(a.period);
    });
    
    for (var k = 0; k < tableData.length; k++) {
        var data = tableData[k];
        var row = tbody.insertRow();
        row.innerHTML = '<td><strong>' + formatPeriodDisplay(data.period) + '</strong></td>' +
            '<td class="text-end">' + formatNumberShort(data.views) + '</td>' +
            '<td class="text-end">' + formatNumberShort(data.reads) + '</td>' +
            '<td class="text-end">' + formatCurrencyFromNanos(data.earnings) + '</td>';
    }
}

// ============================================
// POPULATE MODAL FIELDS
// ============================================

function populateMetadata(story) {
    var keyField = document.getElementById('editStoryKey');
    if (keyField) keyField.value = story.key || '';
    
    var slugField = document.getElementById('editStoryUniqueSlug');
    if (slugField) slugField.value = story.uniqueSlug || '';
    
    var nameDisplay = document.getElementById('editStoryNameDisplay');
    if (nameDisplay) nameDisplay.textContent = story.name || story.title || 'Untitled';
    
    var pathDisplay = document.getElementById('editStoryPath');
    if (pathDisplay) pathDisplay.textContent = story.raw_path || story.rel_path || story.key || '';
    
    var nameInput = document.getElementById('editStoryName');
    if (nameInput) nameInput.value = story.name || story.title || '';
    
    var statusSelect = document.getElementById('editStoryStatus');
    if (statusSelect) statusSelect.value = story.status || 'Draft';
    
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
    if (lastUpdated) {
        var updateTime = story.lastUpdated ? formatDateTimeFromTimestamp(new Date(story.lastUpdated).getTime()) : 'Never';
        lastUpdated.textContent = updateTime;
    }
}

function populateLinkedIn(story) {
    var statusSelect = document.getElementById('editStoryLinkedinStatus');
    if (statusSelect) statusSelect.value = story.linkedin_status || '';
    
    var timestamp = document.getElementById('editStoryLinkedinTimestamp');
    if (timestamp) timestamp.value = story.linkedin_timestamp || '';
    
    var impressions = document.getElementById('editStoryLinkedinImpressions');
    if (impressions) impressions.value = story.linkedin_impressions || 0;
    
    var typeSelect = document.getElementById('editStoryLinkedinType');
    if (typeSelect) typeSelect.value = story.linkedin_type || 'Article';
    
    var url = document.getElementById('editStoryLinkedinUrl');
    if (url) url.value = story.linkedin_url || '';
    
    if (typeof window.updateLinkedinDisplay === 'function') {
        window.updateLinkedinDisplay();
    }
}

function populateMediumDisplay(medium) {
    var mediumId = document.getElementById('mediumId');
    if (mediumId) mediumId.textContent = (medium && medium.id) ? medium.id : '—';
    
    var uniqueSlug = document.getElementById('mediumUniqueSlug');
    if (uniqueSlug) uniqueSlug.textContent = (medium && medium.uniqueSlug) ? medium.uniqueSlug : '—';
    
    var firstPublished = document.getElementById('mediumFirstPublished');
    if (firstPublished) firstPublished.textContent = formatDateFromTimestamp(medium ? medium.firstPublishedAt : null);
    
    var publication = document.getElementById('mediumPublication');
    if (publication) {
        var collectionName = (medium && medium.collection && medium.collection.name) ? medium.collection.name : null;
        publication.textContent = collectionName || '—';
    }
    
    var responses = document.getElementById('mediumResponses');
    if (responses) responses.textContent = formatNumberShort((medium && medium.responsesCount) ? medium.responsesCount : 0);
    
    var readTime = document.getElementById('mediumReadTime');
    if (readTime) readTime.textContent = minutesToHoursMinutes((medium && medium.readingTime) ? medium.readingTime : 0);
    
    var wordCount = document.getElementById('mediumWordCount');
    if (wordCount) wordCount.textContent = formatNumberShort((medium && medium.wordCount) ? medium.wordCount : 0);
    
    var lastUpdate = document.getElementById('mediumLastUpdate');
    if (lastUpdate) lastUpdate.textContent = formatDateTimeFromTimestamp(medium ? medium.updatedAt : null);
    
    var votes = document.getElementById('mediumVotes');
    if (votes) votes.textContent = formatNumberShort((medium && medium.voterCount) ? medium.voterCount : 0);
    
    var claps = document.getElementById('mediumClaps');
    if (claps) claps.textContent = formatNumberShort((medium && medium.clapCount) ? medium.clapCount : 0);
}

// ============================================
// SAVE STORY
// ============================================

async function saveStoryEdit() {
    var storyKey = document.getElementById('editStoryKey');
    if (!storyKey || !storyKey.value) {
        alert('No story selected');
        return;
    }
    
    storyKey = storyKey.value;
    
    var updateData = {};
    
    var nameInput = document.getElementById('editStoryName');
    if (nameInput && nameInput.value) updateData.name = nameInput.value;
    
    var statusSelect = document.getElementById('editStoryStatus');
    if (statusSelect && statusSelect.value) updateData.status = statusSelect.value;
    
    var seriesSelect = document.getElementById('editStorySeries');
    if (seriesSelect && seriesSelect.value) updateData.series = seriesSelect.value;
    else updateData.series = null;
    
    var createdDate = document.getElementById('editStoryCreatedDate');
    if (createdDate && createdDate.value) updateData.createdDate = createdDate.value;
    
    var publishedDate = document.getElementById('editStoryPublishedDate');
    if (publishedDate && publishedDate.value) updateData.publishedDate = publishedDate.value;
    
    var dueDate = document.getElementById('editStoryDueDate');
    if (dueDate && dueDate.value) updateData.publishedDueDate = dueDate.value;
    
    var tagsInput = document.getElementById('editStoryTags');
    if (tagsInput && tagsInput.value) {
        var tags = tagsInput.value.split(',').map(function(t) { return t.trim(); }).filter(function(t) { return t; });
        if (tags.length) updateData.tags = tags;
    }
    
    var mediumUrl = document.getElementById('editStoryMediumUrl');
    if (mediumUrl && mediumUrl.value) updateData.medium_url = mediumUrl.value;
    else updateData.medium_url = null;
    
    var notes = document.getElementById('editStoryNotes');
    if (notes) updateData.notes = notes.value || '';
    
    var bookmarked = document.getElementById('editStoryBookmarked');
    if (bookmarked) updateData.bookmarked = bookmarked.checked;
    
    var linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    if (linkedinStatus && linkedinStatus.value) updateData.linkedin_status = linkedinStatus.value;
    else updateData.linkedin_status = null;
    
    var linkedinTimestamp = document.getElementById('editStoryLinkedinTimestamp');
    if (linkedinTimestamp && linkedinTimestamp.value) updateData.linkedin_timestamp = linkedinTimestamp.value;
    else updateData.linkedin_timestamp = null;
    
    var linkedinImpressions = document.getElementById('editStoryLinkedinImpressions');
    if (linkedinImpressions) updateData.linkedin_impressions = parseInt(linkedinImpressions.value) || 0;
    
    var linkedinType = document.getElementById('editStoryLinkedinType');
    if (linkedinType && linkedinType.value) updateData.linkedin_type = linkedinType.value;
    
    var linkedinUrl = document.getElementById('editStoryLinkedinUrl');
    if (linkedinUrl && linkedinUrl.value) updateData.linkedin_url = linkedinUrl.value;
    else updateData.linkedin_url = null;
    
    try {
        var encodedKey = encodeURIComponent(storyKey);
        var response = await fetch(API_BASE + '/stories/' + encodedKey, {
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
    var uniqueSlugField = document.getElementById('editStoryUniqueSlug');
    if (!uniqueSlugField || !uniqueSlugField.value) {
        alert('No story selected');
        return;
    }
    
    var uniqueSlug = uniqueSlugField.value;
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;
    
    var confirmMsg = '⚠️ WARNING: This will refresh the entire page and discard any unsaved changes in this modal.\n\nSync stats from Medium for ' + year + '-' + String(month).padStart(2, '0') + '?';
    if (!confirm(confirmMsg)) {
        return;
    }
    
    var btn = document.querySelector('[data-action="sync-monthly-stats"]');
    var originalText = btn ? btn.innerHTML : 'Syncing...';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Syncing...';
    }
    
    try {
        var encodedSlug = encodeURIComponent(uniqueSlug);
        var url = API_BASE + '/stories/fetch-lifetime-stats/' + encodedSlug + '?year=' + year + '&month=' + month;
        var response = await fetch(url, { method: 'POST' });
        
        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to sync stats');
        }
        
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
// ADD TO CURRENT MONTH (Future Use)
// ============================================

async function addStoryToCurrentMonth() {
    var storyKeyField = document.getElementById('editStoryKey');
    if (!storyKeyField || !storyKeyField.value) {
        alert('No story selected');
        return;
    }
    
    var storyKey = storyKeyField.value;
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;
    var monthStr = year + '-' + String(month).padStart(2, '0');
    
    if (!confirm('Add story to ' + formatPeriodDisplay(monthStr) + '?')) {
        return;
    }
    
    try {
        var encodedKey = encodeURIComponent(storyKey);
        var url = API_BASE + '/stories/ensure-story-in-month?story_key=' + encodedKey + '&year=' + year + '&month=' + month;
        var response = await fetch(url, { method: 'POST' });
        
        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to add story to month');
        }
        
        alert('Story added to current month successfully');
        
    } catch (error) {
        console.error('Error adding to month:', error);
        alert('Error: ' + error.message);
    }
}

// ============================================
// LOAD STORY FOR EDIT
// ============================================

async function loadStoryForEdit(encodedStoryKey) {
    try {
        var url = `${API_BASE}/stories/content/${encodeURIComponent(encodedStoryKey)}`
        var response = await fetch(url);
        console.log('Loading story from:', url);  // Debug log
        
        var response = await fetch(url);
        if (!response.ok) {
            console.error('Response status:', response.status);
            throw new Error('Story not found (HTTP ' + response.status + ')');
        }
        
        var story = await response.json();
        
        currentStoryKey = story.key;
        currentStoryUniqueSlug = story.uniqueSlug;
        
        populateMetadata(story);
        populateLinkedIn(story);
        populateMediumDisplay(story.medium);
        
        if (story.medium) {
            buildMonthlyStatsTable(story.medium);
        }
        
        await loadAvailableMonths();
        
    } catch (error) {
        console.error('Error loading story:', error);
        alert('Error loading story: ' + error.message);
    }
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
// EVENT HANDLERS SETUP
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    var saveBtn = document.querySelector('[data-action="save-story"]');
    if (saveBtn) {
        saveBtn.onclick = function(e) {
            e.preventDefault();
            saveStoryEdit();
        };
    }
    
    var syncBtn = document.querySelector('[data-action="sync-monthly-stats"]');
    if (syncBtn) {
        syncBtn.onclick = function(e) {
            e.preventDefault();
            syncWithMedium();
        };
    }
    
    var addToMonthBtn = document.querySelector('[data-action="add-to-month"]');
    if (addToMonthBtn) {
        addToMonthBtn.onclick = function(e) {
            e.preventDefault();
            addStoryToCurrentMonth();
        };
    }
    
    var linkedinStatus = document.getElementById('editStoryLinkedinStatus');
    if (linkedinStatus && typeof window.onLinkedinStatusChange === 'function') {
        linkedinStatus.addEventListener('change', window.onLinkedinStatusChange);
    }
    
    var setNowBtn = document.getElementById('editStorySetNowLinkedinBtn');
    if (setNowBtn && typeof window.setNowLinkedinTimestamp === 'function') {
        setNowBtn.onclick = function() { window.setNowLinkedinTimestamp(); };
    }
    
    var clearTimestampBtn = document.getElementById('editStoryClearLinkedinTimestampBtn');
    if (clearTimestampBtn && typeof window.clearLinkedinTimestamp === 'function') {
        clearTimestampBtn.onclick = function() { window.clearLinkedinTimestamp(); };
    }
    
    var clearAllBtn = document.getElementById('editStoryClearAllLinkedinBtn');
    if (clearAllBtn && typeof window.clearAllLinkedinData === 'function') {
        clearAllBtn.onclick = function() { window.clearAllLinkedinData(); };
    }
    
    var setTodayBtn = document.getElementById('editStorySetTodayBtn');
    if (setTodayBtn && typeof window.setEditStoryTodayDate === 'function') {
        setTodayBtn.onclick = function() { window.setEditStoryTodayDate(); };
    }
});