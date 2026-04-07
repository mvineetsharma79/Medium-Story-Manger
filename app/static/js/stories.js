// ============================================
// STORIES JS - Working with all modal elements
// ============================================

let allStories = [];
let allSeriesNames = [];
let currentEditStoryName = null;
let currentStatsStoryName = null;
let currentMonth = 'all';
let currentSort = { column: 'name', direction: 'asc' };
let totalEarnings = 0;
let monthlyEarnings = 0;

// ============================================
// SORTING
// ============================================

function sortStories(column) {
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }
    renderStoryTable();
    updateSortIcons(column, currentSort.direction);
}

function updateSortIcons(column, direction) {
    const headers = document.querySelectorAll('#storiesTableHeader .sortable');
    headers.forEach(header => {
        header.classList.remove('active');
        const icon = header.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    });
    const activeHeader = document.querySelector(`#storiesTableHeader .sortable[data-sort="${column}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active');
        const icon = activeHeader.querySelector('i');
        if (icon) icon.className = direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
    }
}

// ============================================
// LOAD ALL SERIES NAMES
// ============================================

async function loadAllSeriesNames() {
    try {
        const response = await fetch(`${API_BASE}/stories/list`);
        if (!response.ok) return;
        const data = await response.json();
        const allStoriesData = data.stories || [];
        
        const seriesSet = new Set();
        allStoriesData.forEach(story => {
            if (story.series && story.series !== 'null' && story.series !== 'undefined' && story.series !== '') {
                seriesSet.add(story.series);
            }
        });
        
        allSeriesNames = Array.from(seriesSet).sort();
        updateSeriesDropdown();
    } catch (error) {
        console.error('Error loading all series names:', error);
    }
}

function updateSeriesDropdown() {
    const seriesFilter = document.getElementById('seriesFilter');
    if (!seriesFilter) return;
    
    const currentValue = seriesFilter.value;
    seriesFilter.innerHTML = '<option value="">All Series</option>';
    
    allSeriesNames.forEach(series => {
        const option = document.createElement('option');
        option.value = series;
        option.textContent = series;
        seriesFilter.appendChild(option);
    });
    
    if (currentValue && allSeriesNames.includes(currentValue)) {
        seriesFilter.value = currentValue;
    }
}

// ============================================
// MONTH SELECTOR
// ============================================

async function loadMonths() {
    try {
        const response = await fetch(`${API_BASE}/stories/months`);
        if (!response.ok) return;
        const data = await response.json();
        const selector = document.getElementById('monthSelector');
        if (selector) {
            selector.innerHTML = '<option value="all">All Time (Dashboard)</option>';
            if (data.months && Array.isArray(data.months)) {
                data.months.forEach(month => {
                    const option = document.createElement('option');
                    option.value = month;
                    option.textContent = month;
                    selector.appendChild(option);
                });
            }
        }
        const savedMonth = localStorage.getItem('selectedMonth');
        if (savedMonth && savedMonth !== 'all' && isValidYearMonth(savedMonth)) {
            if (selector) selector.value = savedMonth;
            currentMonth = savedMonth;
        } else {
            currentMonth = 'all';
        }
        
        await loadAllSeriesNames();
        await loadStories();
    } catch (error) {
        console.error('Error loading months:', error);
        currentMonth = 'all';
        await loadStories();
    }
}

async function onMonthChange() {
    const selector = document.getElementById('monthSelector');
    if (!selector) return;
    
    currentMonth = selector.value;
    localStorage.setItem('selectedMonth', currentMonth);
    await loadStories();
}

// ============================================
// LOAD STORIES
// ============================================

async function loadStories() {
    showLoading();
    try {
        const url = currentMonth === 'all' ? 
            `${API_BASE}/stories/list` : 
            `${API_BASE}/stories/list/${currentMonth}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        allStories = data.stories || [];
        
        restoreSeriesFilter();
        
        if (currentMonth === 'all') {
            totalEarnings = allStories.reduce((sum, s) => sum + (s.medium_earnings || 0), 0);
        } else {
            monthlyEarnings = allStories.reduce((sum, s) => sum + (s.medium_earnings || 0), 0);
            totalEarnings = await fetchTotalEarnings();
        }
        
        renderStoryTable();
        
        if (currentMonth === 'all') {
            updateDashboardStats();
        }
        
        console.log(`Loaded ${allStories.length} stories`);
    } catch (error) {
        console.error('Error loading stories:', error);
        showToast('Error loading stories: ' + error.message, 'error');
        const tbody = document.getElementById('storiesTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="16" class="text-center text-danger py-3">Error loading stories. Please try again. </td></tr>';
        }
    } finally {
        hideLoading();
    }
}

function restoreSeriesFilter() {
    const savedSeries = sessionStorage.getItem('storiesFilterSeries');
    const seriesFilter = document.getElementById('seriesFilter');
    if (savedSeries && seriesFilter) {
        let exists = false;
        for (let i = 0; i < seriesFilter.options.length; i++) {
            if (seriesFilter.options[i].value === savedSeries) {
                exists = true;
                break;
            }
        }
        if (exists) {
            seriesFilter.value = savedSeries;
            renderStoryTable();
        } else {
            sessionStorage.removeItem('storiesFilterSeries');
        }
    }
}

async function fetchTotalEarnings() {
    try {
        const response = await fetch(`${API_BASE}/stories/earnings/total`);
        if (!response.ok) return 0;
        const data = await response.json();
        return data.total_earnings || 0;
    } catch (error) {
        return 0;
    }
}

// ============================================
// RENDER STORY TABLE
// ============================================

function applyFilters() { 
    const seriesFilter = document.getElementById('seriesFilter');
    if (seriesFilter) {
        sessionStorage.setItem('storiesFilterSeries', seriesFilter.value);
    }
    renderStoryTable(); 
}

function clearFilters() {
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkFilter = document.getElementById('bookmarkFilter');
    const leaderboardFilter = document.getElementById('leaderboardFilter');
    
    if (statusFilter) statusFilter.value = 'All';
    if (seriesFilter) seriesFilter.value = '';
    if (searchFilter) searchFilter.value = '';
    if (bookmarkFilter) bookmarkFilter.checked = false;
    if (leaderboardFilter) leaderboardFilter.checked = false;
    
    sessionStorage.removeItem('storiesFilterSeries');
    renderStoryTable();
}

function renderStoryTable() {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;
    
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkedOnly = document.getElementById('bookmarkFilter');
    const leaderboardOnly = document.getElementById('leaderboardFilter');
    
    let filtered = [...allStories];
    if (statusFilter && statusFilter.value !== 'All') filtered = filtered.filter(s => s.status === statusFilter.value);
    if (seriesFilter && seriesFilter.value) filtered = filtered.filter(s => s.series === seriesFilter.value);
    if (searchFilter && searchFilter.value) {
        filtered = filtered.filter(s => s.name.toLowerCase().includes(searchFilter.value.toLowerCase()));
    }
    if (bookmarkedOnly && bookmarkedOnly.checked) filtered = filtered.filter(s => s.bookmarked === true);
    if (leaderboardOnly && leaderboardOnly.checked) filtered = filtered.filter(s => s.leaderboard === true);
    
    filtered.sort((a, b) => {
        let aVal = a[currentSort.column];
        let bVal = b[currentSort.column];
        if (typeof aVal === 'boolean') { aVal = aVal ? 1 : 0; bVal = bVal ? 1 : 0; }
        if (typeof aVal === 'string') { aVal = (aVal || '').toLowerCase(); bVal = (bVal || '').toLowerCase(); }
        if (typeof aVal === 'number') { aVal = aVal || 0; bVal = bVal || 0; }
        return currentSort.direction === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
    });
    
    const filterCountDisplay = document.getElementById('filterCountDisplay');
    if (filterCountDisplay) {
        filterCountDisplay.textContent = `Showing ${filtered.length} of ${allStories.length} stories`;
    }
    
    tbody.innerHTML = '';
    
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="16" class="text-center text-muted py-3">No stories found</td</tr>';
        return;
    }
    
    filtered.forEach(story => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        row.onclick = () => openEditModal(story.name);
        
        const encodedName = encodeURIComponent(story.name);
        
        row.insertCell(0).innerHTML = `<i class="bi bi-bookmark${story.bookmarked ? '-fill' : ''}" style="color:${story.bookmarked ? '#ffc107' : '#6c757d'}; cursor:pointer" onclick="event.stopPropagation();toggleBookmark('${encodedName}')"></i>`;
        row.insertCell(1).innerHTML = `<i class="bi bi-trophy${story.leaderboard ? '-fill' : ''}" style="color:${story.leaderboard ? '#ffd700' : '#6c757d'}; cursor:pointer" onclick="event.stopPropagation();toggleLeaderboard('${encodedName}')"></i>`;
        row.insertCell(2).innerHTML = `<span class="status-badge status-${(story.status || 'draft').toLowerCase()}">${story.status || 'Draft'}</span>`;
        row.insertCell(3).innerHTML = escapeHtml(story.name);
        row.insertCell(4).innerHTML = story.created_date ? story.created_date.split('T')[0] : '-';
        row.insertCell(5).innerHTML = story.published_date ? story.published_date.split('T')[0] : '-';
        row.insertCell(6).innerHTML = `${formatNumber(story.member_reads)}/${formatNumber(story.reads)}<br><small>${story.reads_percent || 0}%</small>`;
        row.insertCell(7).innerHTML = `${formatNumber(story.member_views)}/${formatNumber(story.views)}<br><small>${story.views_percent || 0}%</small>`;
        row.insertCell(8).innerHTML = `${formatNumber(story.lifetime_reads)}/${formatNumber(story.lifetime_views)}/${formatNumber(story.presentation_count)}`;
        row.insertCell(9).innerHTML = `${formatNumber(story.claps)}<br><small>${formatNumber(story.lifetime_claps)}</small>`;
        row.insertCell(10).innerHTML = formatCurrency(story.medium_earnings);
        row.insertCell(11).innerHTML = `${formatNumber(story.medium_new_followers)}/${formatNumber(story.total_followers)}`;
        row.insertCell(12).innerHTML = `${formatReadTime(story.medium_reading_time || story.read_time)} / ${formatNumber(story.word_count)}`;
        row.insertCell(13).innerHTML = story.medium_publication || '—';
        
        let linkedinText = 'Not Posted';
        if (story.linkedin_status === 'scheduled') linkedinText = '📅 Scheduled';
        else if (story.linkedin_status === 'posted') linkedinText = '✅ Posted';
        row.insertCell(14).innerHTML = `<span class="linkedin-badge linkedin-${story.linkedin_status || 'not-posted'}">${linkedinText}</span>`;
        
        row.insertCell(15).innerHTML = `
            <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation();openStatsModal('${encodedName}')"><i class="bi bi-graph-up"></i></button>
            <button class="btn btn-sm btn-outline-primary ms-1" onclick="event.stopPropagation();openEditModal('${encodedName}')"><i class="bi bi-pencil"></i></button>
            <button class="btn btn-sm btn-danger ms-1" onclick="event.stopPropagation();deleteStory('${encodedName}')"><i class="bi bi-trash"></i></button>
        `;
    });
}

// ============================================
// TOGGLE BOOKMARK
// ============================================

async function toggleBookmark(encodedName) {
    const storyName = decodeURIComponent(encodedName);
    const story = allStories.find(s => s.name === storyName);
    if (!story) return;
    
    const identifier = story.medium_url || story.name;
    const newState = !story.bookmarked;
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(identifier)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookmarked: newState })
        });
        
        if (response.ok) {
            story.bookmarked = newState;
            renderStoryTable();
            showToast('Bookmark updated', 'success');
        }
    } catch (error) {
        console.error('Error toggling bookmark:', error);
    }
}

// ============================================
// TOGGLE LEADERBOARD
// ============================================

async function toggleLeaderboard(encodedName) {
    const storyName = decodeURIComponent(encodedName);
    const story = allStories.find(s => s.name === storyName);
    if (!story) return;
    
    const yearmonth = currentMonth === 'all' ? getCurrentYearMonth() : currentMonth;
    const newState = !story.leaderboard;
    const identifier = story.medium_url || story.name;
    
    try {
        const response = await fetch(`${API_BASE}/stories/stats/${encodeURIComponent(identifier)}/${yearmonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ leaderboard: newState })
        });
        
        if (response.ok) {
            story.leaderboard = newState;
            renderStoryTable();
            if (window.updateLeaderboardTotal) window.updateLeaderboardTotal();
            showToast(`Leaderboard updated for ${yearmonth}`, 'success');
        }
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
    }
}

// ============================================
// DELETE STORY
// ============================================

async function deleteStory(encodedName) {
    const storyName = decodeURIComponent(encodedName);
    if (!confirm(`Delete story "${storyName}"?`)) return;
    
    const story = allStories.find(s => s.name === storyName);
    if (!story) return;
    
    const identifier = story.medium_url || story.name;
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(identifier)}`, { method: 'DELETE' });
        if (response.ok) {
            showToast('Story deleted', 'success');
            await loadAllSeriesNames();
            await loadStories();
        }
    } catch (error) {
        console.error('Error deleting story:', error);
        alert('Error deleting story');
    }
}

// ============================================
// OPEN EDIT MODAL
// ============================================

async function openEditModal(encodedName) {
    const storyName = decodeURIComponent(encodedName);
    const story = allStories.find(s => s.name === storyName);
    if (!story) return;
    
    currentEditStoryName = story.name;
    const identifier = story.medium_url || story.name;
    const now = new Date();
    const targetYear = now.getFullYear();
    const targetMonth = now.getMonth() + 1;
    
    await loadStoryIntoEditModal(identifier, targetYear, targetMonth, story);
    const modalElement = document.getElementById('editStoryModal');
    if (modalElement) new bootstrap.Modal(modalElement).show();
}

async function loadStoryIntoEditModal(identifier, year, month, story) {
    try {
        const encodedIdentifier = encodeURIComponent(identifier);
        
        // Get story metadata
        const storyRes = await fetch(`${API_BASE}/stories/story/${encodedIdentifier}`);
        if (!storyRes.ok) throw new Error('Story not found');
        const storyData = await storyRes.json();
        
        // Get monthly stats
        let monthlyStats = {};
        try {
            const monthlyRes = await fetch(`${API_BASE}/stories/stats/${encodedIdentifier}/${year}-${String(month).padStart(2, '0')}`);
            if (monthlyRes.ok) monthlyStats = await monthlyRes.json();
        } catch (error) {
            console.log('No monthly stats found, using defaults');
        }
        
        // Helper functions
        const setValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = (value !== null && value !== undefined) ? value : '';
        };
        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = (text !== null && text !== undefined) ? text : '0';
        };
        const setSelectValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
        };
        
        // Set form values
        setValue('editStoryKey', storyData.key);
        setValue('editStoryName', storyData.name);
        setSelectValue('editStatus', storyData.status || 'Draft');
        setValue('editCreatedDate', storyData.created_date ? storyData.created_date.split('T')[0] : '');
        setValue('editPublishedDate', storyData.published_date ? storyData.published_date.split('T')[0] : '');
        setValue('editMediumUrl', storyData.medium_url || '');
        setValue('editPublication', storyData.medium_publication || '');
        setValue('editTags', (storyData.tags || []).join(', '));
        setValue('editNotes', storyData.notes || '');
        setSelectValue('editLinkedinStatus', storyData.linkedin_status || '');
        setValue('editLinkedinTimestamp', storyData.linkedin_timestamp || '');
        setValue('editLinkedinImpressions', storyData.linkedin_impressions || 0);
        setValue('editLinkedinUrl', storyData.linkedin_url || '');
        setSelectValue('editBookmarked', storyData.bookmarked ? 'true' : 'false');
        
        // Lifetime stats
        setText('lifetimeReads', formatNumber(storyData.lifetime_reads || 0));
        setText('lifetimeViews', formatNumber(storyData.lifetime_views || 0));
        setText('lifetimeClaps', formatNumber(storyData.lifetime_claps || 0));
        setText('presentationCount', formatNumber(storyData.presentation_count || 0));
        setText('wordCount', formatNumber(storyData.word_count || 0));
        setText('readingTime', storyData.medium_reading_time || storyData.read_time || 0);
        setText('totalFollowers', formatNumber(storyData.total_followers || 0));
        
        // Monthly stats
        setValue('editMemberReads', monthlyStats.member_reads || 0);
        setValue('editNonMemberReads', monthlyStats.nonmember_reads || 0);
        setValue('editMemberViews', monthlyStats.member_views || 0);
        setValue('editNonMemberViews', monthlyStats.nonmember_views || 0);
        setValue('editClaps', monthlyStats.claps || 0);
        setValue('editResponses', monthlyStats.responses || 0);
        setValue('editNewFollowers', monthlyStats.medium_new_followers || 0);
        setValue('editHighlights', monthlyStats.medium_highlights || 0);
        setSelectValue('editLeaderboard', monthlyStats.leaderboard ? 'true' : 'false');
        setValue('editLeaderboardNanos', monthlyStats.leaderboard_nanos || 0);
        setValue('editMediumEarnings', (monthlyStats.medium_earnings || 0) / 1000000000);
        
        // Series dropdown
        const seriesSelect = document.getElementById('editSeries');
        if (seriesSelect) {
            const currentSeries = storyData.series || '';
            seriesSelect.innerHTML = '<option value="">None</option>';
            allSeriesNames.forEach(seriesName => {
                const option = document.createElement('option');
                option.value = seriesName;
                option.textContent = seriesName;
                if (seriesName === currentSeries) option.selected = true;
                seriesSelect.appendChild(option);
            });
        }
        
        const monthLabel = document.getElementById('currentMonthLabel');
        if (monthLabel) monthLabel.textContent = `${year}-${String(month).padStart(2, '0')}`;
        
        window.currentEditYear = year;
        window.currentEditMonth = month;
        
        // Load monthly stats list
        await loadAllMonthsStats(storyData.name);
        
    } catch (error) {
        console.error('Error loading story for edit:', error);
        showToast('Error loading story: ' + error.message, 'error');
    }
}

async function loadAllMonthsStats(storyName) {
    if (!storyName) return;
    try {
        const response = await fetch(`${API_BASE}/stories/story-months/${encodeURIComponent(storyName)}`);
        const data = await response.json();
        const container = document.getElementById('allMonthsStatsList');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!data.months || data.months.length === 0) {
            container.innerHTML = '<div class="text-center p-3 text-muted">No monthly data available</div>';
            return;
        }
        
        const listGroup = document.createElement('div');
        listGroup.className = 'list-group list-group-flush';
        
        for (const month of data.months) {
            const item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <strong>${month.yearmonth}</strong>
                    <span class="badge ${month.leaderboard ? 'bg-warning' : 'bg-secondary'}">${month.leaderboard ? '🏆 Leaderboard' : 'Normal'}</span>
                    <button class="btn btn-sm btn-outline-primary" onclick="refreshStoryStatsForMonth('${encodeURIComponent(storyName)}', '${month.yearmonth}')">
                        <i class="bi bi-cloud-download"></i> Fetch
                    </button>
                </div>
                <div class="row small mt-1">
                    <div class="col-3">Reads: ${formatNumber(month.reads)}</div>
                    <div class="col-3">Views: ${formatNumber(month.views)}</div>
                    <div class="col-3">Claps: ${formatNumber(month.claps)}</div>
                    <div class="col-3">Responses: ${formatNumber(month.responses)}</div>
                </div>
                <div class="row small">
                    <div class="col-6">Member Reads: ${formatNumber(month.member_reads)}</div>
                    <div class="col-6">Member Views: ${formatNumber(month.member_views)}</div>
                </div>
                <div class="row small">
                    <div class="col-12">Earnings: ${formatCurrency(month.medium_earnings || 0)}</div>
                </div>
            `;
            listGroup.appendChild(item);
        }
        container.appendChild(listGroup);
    } catch (error) {
        console.error('Error loading all months stats:', error);
    }
}

// ============================================
// SAVE STORY EDIT
// ============================================

async function saveStoryEdit() {
    const storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) return;
    
    const story = allStories.find(s => s.key === storyKey);
    if (!story) return;
    
    const identifier = story.medium_url || story.name;
    const selectedSeries = document.getElementById('editSeries')?.value || null;
    
    const storyData = {
        status: document.getElementById('editStatus')?.value,
        created_date: document.getElementById('editCreatedDate')?.value || null,
        published_date: document.getElementById('editPublishedDate')?.value || null,
        medium_url: document.getElementById('editMediumUrl')?.value || null,
        medium_publication: document.getElementById('editPublication')?.value || null,
        tags: document.getElementById('editTags')?.value.split(',').map(t => t.trim()).filter(t => t),
        notes: document.getElementById('editNotes')?.value || '',
        linkedin_status: document.getElementById('editLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editLinkedinImpressions')?.value) || 0,
        linkedin_url: document.getElementById('editLinkedinUrl')?.value || null,
        bookmarked: document.getElementById('editBookmarked')?.value === 'true',
        series: selectedSeries,
        lifetime_reads: parseInt(document.getElementById('lifetimeReads')?.textContent) || 0,
        lifetime_views: parseInt(document.getElementById('lifetimeViews')?.textContent) || 0,
        lifetime_claps: parseInt(document.getElementById('lifetimeClaps')?.textContent) || 0,
        presentation_count: parseInt(document.getElementById('presentationCount')?.textContent) || 0,
        word_count: parseInt(document.getElementById('wordCount')?.textContent) || 0,
        medium_reading_time: parseInt(document.getElementById('readingTime')?.textContent) || 0,
        total_followers: parseInt(document.getElementById('totalFollowers')?.textContent) || 0
    };
    
    const memberReads = parseInt(document.getElementById('editMemberReads')?.value) || 0;
    const nonmemberReads = parseInt(document.getElementById('editNonMemberReads')?.value) || 0;
    const memberViews = parseInt(document.getElementById('editMemberViews')?.value) || 0;
    const nonmemberViews = parseInt(document.getElementById('editNonMemberViews')?.value) || 0;
    
    const monthlyData = {
        member_reads: memberReads,
        nonmember_reads: nonmemberReads,
        member_views: memberViews,
        nonmember_views: nonmemberViews,
        claps: parseInt(document.getElementById('editClaps')?.value) || 0,
        responses: parseInt(document.getElementById('editResponses')?.value) || 0,
        medium_new_followers: parseInt(document.getElementById('editNewFollowers')?.value) || 0,
        medium_highlights: parseInt(document.getElementById('editHighlights')?.value) || 0,
        leaderboard: document.getElementById('editLeaderboard')?.value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editLeaderboardNanos')?.value) || 0,
        medium_earnings: parseFloat(document.getElementById('editMediumEarnings')?.value) || 0,
        reads: memberReads + nonmemberReads,
        view_count: memberViews + nonmemberViews
    };
    
    const year = window.currentEditYear || new Date().getFullYear();
    const month = window.currentEditMonth || new Date().getMonth() + 1;
    
    showLoading();
    try {
        // Update stories.json
        const permRes = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(identifier)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(storyData)
        });
        
        if (!permRes.ok) throw new Error('Failed to update story');
        
        // Ensure story in month
        await fetch(`${API_BASE}/stories/ensure-story-in-month?story_key=${encodeURIComponent(storyKey)}&year=${year}&month=${month}`, {
            method: 'POST'
        });
        
        // Update monthly stats
        const monthlyRes = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(story.name)}/stats/${year}-${String(month).padStart(2, '0')}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
        if (modal) modal.hide();
        
        await loadAllSeriesNames();
        await loadStories();
        showToast('Story saved successfully', 'success');
        
    } catch (error) {
        console.error('Error saving story:', error);
        showToast('Error saving story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// STATS FUNCTIONS
// ============================================

async function openStatsModal(encodedName) {
    const storyName = decodeURIComponent(encodedName);
    const story = allStories.find(s => s.name === storyName);
    if (!story) return;
    
    document.getElementById('statsStoryName').textContent = story.name;
    document.getElementById('statsReads').textContent = formatNumber(story.reads);
    document.getElementById('statsViews').textContent = formatNumber(story.views);
    document.getElementById('statsClaps').textContent = formatNumber(story.claps);
    new bootstrap.Modal(document.getElementById('statsModal')).show();
}

async function refreshStoryStatsForMonth(encodedName, yearmonth) {
    const storyName = decodeURIComponent(encodedName);
    const story = allStories.find(s => s.name === storyName);
    if (!story || !story.medium_url) {
        showToast('Story has no Medium URL', 'error');
        return;
    }
    
    const postId = extractPostIdFromUrl(story.medium_url);
    if (!postId) {
        showToast('Could not extract post ID', 'error');
        return;
    }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-story-stats/${postId}/${yearmonth}`, { method: 'POST' });
        const data = await response.json();
        if (response.ok && data.success) {
            showToast(`Stats refreshed for ${yearmonth}`, 'success');
            const [year, month] = yearmonth.split('-');
            const identifier = story.medium_url || story.name;
            await loadStoryIntoEditModal(identifier, parseInt(year), parseInt(month), story);
            await loadStories();
        } else {
            showToast('Error refreshing stats', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function refreshCurrentStoryStats() {
    const mediumUrl = document.getElementById('editMediumUrl')?.value;
    if (!mediumUrl) {
        showToast('No Medium URL found', 'error');
        return;
    }
    
    const postId = extractPostIdFromUrl(mediumUrl);
    if (!postId) {
        showToast('Could not extract post ID', 'error');
        return;
    }
    
    const year = window.currentEditYear || new Date().getFullYear();
    const month = window.currentEditMonth || new Date().getMonth() + 1;
    const yearmonth = `${year}-${String(month).padStart(2, '0')}`;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-story-stats/${postId}/${yearmonth}`, { method: 'POST' });
        const data = await response.json();
        if (response.ok && data.success) {
            const stats = data.stats.totals;
            
            document.getElementById('editMemberReads').value = stats.member_reads || 0;
            document.getElementById('editNonMemberReads').value = stats.nonmember_reads || 0;
            document.getElementById('editMemberViews').value = stats.member_views || 0;
            document.getElementById('editNonMemberViews').value = stats.nonmember_views || 0;
            document.getElementById('editClaps').value = stats.claps || 0;
            document.getElementById('editResponses').value = stats.replies || 0;
            document.getElementById('editNewFollowers').value = stats.new_followers || 0;
            document.getElementById('editHighlights').value = stats.highlights || 0;
            document.getElementById('editMediumEarnings').value = (stats.earnings || 0) / 1000000000;
            
            showToast(`Stats fetched for ${yearmonth}`, 'success');
        } else {
            showToast('Error refreshing stats', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// ADD STORY MODAL
// ============================================

async function openAddStoryModal() {
    try {
        const response = await fetch(`${API_BASE}/series/`);
        const seriesList = await response.json();
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect && Array.isArray(seriesList)) {
            seriesSelect.innerHTML = '<option value="">None</option>';
            seriesList.forEach(s => {
                seriesSelect.innerHTML += `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading series:', error);
    }
    
    document.getElementById('addStoryName').value = '';
    document.getElementById('addStoryTags').value = '';
    document.getElementById('addStoryCreatedDate').value = getTodayDate();
    document.getElementById('addStoryReadTime').value = '';
    document.getElementById('addStoryPublishedDate').value = '';
    document.getElementById('addStoryMediumUrl').value = '';
    document.getElementById('addStoryPublication').value = '';
    
    new bootstrap.Modal(document.getElementById('addStoryModal')).show();
}

async function createStory() {
    const name = document.getElementById('addStoryName')?.value.trim();
    if (!name) {
        showToast('Story name is required', 'error');
        return;
    }
    
    const data = {
        name: name,
        series: document.getElementById('addStorySeries')?.value || null,
        tags: document.getElementById('addStoryTags')?.value.split(',').map(t => t.trim()).filter(t => t),
        read_time: parseInt(document.getElementById('addStoryReadTime')?.value) || null,
        created_date: document.getElementById('addStoryCreatedDate')?.value || getTodayDate(),
        published_date: document.getElementById('addStoryPublishedDate')?.value || null,
        medium_url: document.getElementById('addStoryMediumUrl')?.value || null,
        medium_publication: document.getElementById('addStoryPublication')?.value || null
    };
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance(document.getElementById('addStoryModal'))?.hide();
            await loadAllSeriesNames();
            await loadStories();
            showToast('Story created', 'success');
        } else {
            const error = await response.json();
            showToast('Error: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error creating story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// SYNC AND LEADERBOARD
// ============================================

async function syncStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            showToast(`Sync completed: ${data.added || 0} added`, 'success');
            await loadAllSeriesNames();
            await loadStories();
        }
    } catch (error) {
        showToast('Error syncing stories', 'error');
    } finally {
        hideLoading();
    }
}

async function updateLeaderboardStats() {
    const yearmonth = currentMonth === 'all' ? getCurrentYearMonth() : currentMonth;
    if (!confirm(`Fetch leaderboard stats for ${yearmonth}?`)) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-leaderboard-stats/${yearmonth}`, { method: 'POST' });
        if (response.ok) {
            showToast('Leaderboard stats updated', 'success');
            await loadStories();
        }
    } catch (error) {
        showToast('Error updating leaderboard', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// DASHBOARD STATS
// ============================================

function updateDashboardStats() {
    const elements = {
        totalCount: allStories.length,
        publishedCount: allStories.filter(s => s.status === 'Published').length,
        readyCount: allStories.filter(s => s.status === 'Ready').length,
        draftCount: allStories.filter(s => s.status === 'Draft').length,
        doneCount: allStories.filter(s => s.status === 'Done').length,
        bookmarkedCount: allStories.filter(s => s.bookmarked === true).length,
        leaderboardStoryCount: allStories.filter(s => s.leaderboard === true).length
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    await loadMonths();
    
    document.getElementById('addStoryCreateBtn')?.addEventListener('click', createStory);
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
    document.getElementById('syncStoriesBtn')?.addEventListener('click', syncStories);
});

// Make functions globally available
window.sortStories = sortStories;
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;
window.openEditModal = openEditModal;
window.openStatsModal = openStatsModal;
window.onMonthChange = onMonthChange;
window.openAddStoryModal = openAddStoryModal;
window.updateLeaderboardStats = updateLeaderboardStats;
window.saveStoryEdit = saveStoryEdit;
window.toggleBookmark = toggleBookmark;
window.toggleLeaderboard = toggleLeaderboard;
window.deleteStory = deleteStory;
window.refreshCurrentStoryStats = refreshCurrentStoryStats;
window.refreshStoryStatsForMonth = refreshStoryStatsForMonth;
window.syncStories = syncStories;