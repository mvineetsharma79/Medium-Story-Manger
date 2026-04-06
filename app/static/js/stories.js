// ============================================
// STORIES JS - Complete with Medium API Fetch Integration
// ============================================

let allStories = [];
let currentEditStoryKey = null;
let currentStatsStoryKey = null;
let currentMonth = 'all';
let currentSort = { column: 'name', direction: 'asc' };

// ============================================
// UTILITIES
// ============================================

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function showLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.style.display = 'none';
}

function showToast(message, type) {
    alert(message);
}

// ============================================
// MEDIUM STATS FETCHING
// ============================================

/**
 * Fetch stats for a single story from Medium API
 * @param {string} storyKey - The story key
 * @param {string} yearmonth - Optional: YYYY-MM format for specific month
 * @returns {Promise<object>} - Stats result
 */
async function fetchStoryStatsFromMedium(storyKey, yearmonth = null) {
    try {
        let url = `${API_BASE}/stories/fetch-lifetime-stats/${encodeURIComponent(storyKey)}`;
        if (yearmonth) {
            const [year, month] = yearmonth.split('-');
            url += `?year=${year}&month=${month}`;
        }
        
        const response = await fetch(url, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            return { success: true, data: data };
        } else {
            return { success: false, error: data.detail || 'Failed to fetch stats' };
        }
    } catch (error) {
        return { success: false, error: error.message };
    }
}

/**
 * Refresh single story stats and update edit modal
 * @param {string} storyKey - The story key
 * @param {string} yearmonth - Optional: YYYY-MM format
 */
async function refreshStoryStats(storyKey, yearmonth = null) {
    if (!storyKey) {
        showToast('No story selected', 'error');
        return;
    }
    
    showLoading();
    try {
        const result = await fetchStoryStatsFromMedium(storyKey, yearmonth);
        
        if (result.success) {
            showToast('Stats refreshed successfully from Medium', 'success');
            await loadStoryIntoEditModal(storyKey, yearmonth);
        } else {
            showToast('Error refreshing stats: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
        showToast('Error refreshing stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// LOAD STORY INTO EDIT MODAL
// ============================================

async function loadStoryIntoEditModal(storyKey, yearmonth = null) {
    try {
        let url;
        if (yearmonth) {
            url = `${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/${yearmonth}`;
        } else if (currentMonth !== 'all') {
            url = `${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/${currentMonth}`;
        } else {
            url = `${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`;
        }
        
        const response = await fetch(url);
        const story = await response.json();
        
        // Helper function to safely set value
        const setValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.value = value;
            else console.warn(`Element ${id} not found`);
        };
        
        const setText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.textContent = text;
            else console.warn(`Element ${id} not found`);
        };
        
        // Populate series dropdown
        const seriesSelect = document.getElementById('editSeries');
        if (seriesSelect) {
            seriesSelect.innerHTML = '<option value="">None</option>';
            const seriesRes = await fetch(`${API_BASE}/series/`);
            const seriesList = await seriesRes.json();
            if (Array.isArray(seriesList)) {
                seriesList.forEach(s => {
                    const option = document.createElement('option');
                    option.value = s.name;
                    option.textContent = s.name;
                    if (story.series === s.name) option.selected = true;
                    seriesSelect.appendChild(option);
                });
            }
        }
        
        setText('editStoryName', story.name);
        setValue('editStoryKey', story.key);
        setValue('editStatus', story.status || 'Draft');
        setValue('editPublishedDate', story.published_date || '');
        setValue('editMediumUrl', story.medium_url || '');
        setValue('editTags', (story.tags || []).join(', '));
        setValue('editNotes', story.notes || '');
        setValue('editPublication', story.medium_publication || '');
        setValue('editLinkedinStatus', story.linkedin_status || '');
        setValue('editLinkedinTimestamp', story.linkedin_timestamp || '');
        setValue('editLinkedinImpressions', story.linkedin_impressions || 0);
        setValue('editLinkedinUrl', story.linkedin_url || '');
        
        let displayMonth;
        if (yearmonth) {
            displayMonth = yearmonth;
        } else if (currentMonth !== 'all') {
            displayMonth = currentMonth;
        } else {
            const now = new Date();
            displayMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        }
        setText('currentMonthLabel', displayMonth);
        
        setValue('editMemberReads', story.member_reads || 0);
        setValue('editNonMemberReads', story.nonmember_reads || 0);
        setValue('editMemberViews', story.member_views || 0);
        setValue('editNonMemberViews', story.nonmember_views || 0);
        setValue('editClaps', story.claps || 0);
        setValue('editResponses', story.responses || 0);
        setValue('editLeaderboard', story.leaderboard ? 'true' : 'false');
        setValue('editLeaderboardNanos', story.leaderboard_nanos || 0);
        
        setText('lifetimeReads', formatNumber(story.lifetime_reads || 0));
        setText('lifetimeViews', formatNumber(story.lifetime_views || 0));
        setText('lifetimeClaps', formatNumber(story.lifetime_claps || 0));
        
        // Load all months stats list
        await loadAllMonthsStats(storyKey);
        
        window.currentEditMonth = displayMonth;
        
    } catch (error) {
        console.error('Error loading story into edit modal:', error);
        showToast('Error loading story data: ' + error.message, 'error');
    }
}

// ============================================
// LOAD ALL MONTHS STATS (for edit modal)
// ============================================

async function loadAllMonthsStats(storyKey) {
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats`);
        const data = await response.json();
        
        const container = document.getElementById('allMonthsStatsList');
        if (!container) return;
        
        if (!data.months || data.months.length === 0) {
            container.innerHTML = '<div class="text-center p-3 text-muted">No monthly data available</div>';
            return;
        }
        
        let html = '<div class="list-group list-group-flush">';
        for (const month of data.months) {
            html += `
                <div class="list-group-item list-group-item-action">
                    <div class="d-flex justify-content-between align-items-center">
                        <strong>${month.yearmonth}</strong>
                        <span class="badge ${month.leaderboard ? 'bg-warning' : 'bg-secondary'}">${month.leaderboard ? '🏆 Leaderboard' : 'Normal'}</span>
                        <button class="btn btn-sm btn-outline-primary" onclick="refreshStoryStatsForMonth('${storyKey}', '${month.yearmonth}')">
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
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Error loading all months stats:', error);
        const container = document.getElementById('allMonthsStatsList');
        if (container) {
            container.innerHTML = '<div class="text-center p-3 text-danger">Error loading months</div>';
        }
    }
}

// ============================================
// REFRESH STATS FOR SPECIFIC MONTH
// ============================================

async function refreshStoryStatsForMonth(storyKey, yearmonth) {
    showLoading();
    try {
        const result = await fetchStoryStatsFromMedium(storyKey, yearmonth);
        
        if (result.success) {
            showToast(`Stats refreshed for ${yearmonth}`, 'success');
            await loadStoryIntoEditModal(storyKey, yearmonth);
        } else {
            showToast('Error refreshing stats: ' + result.error, 'error');
        }
    } catch (error) {
        console.error('Error refreshing stats for month:', error);
        showToast('Error refreshing stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// OPEN EDIT MODAL
// ============================================

async function openEditModal(storyKey) {
    currentEditStoryKey = storyKey;
    showLoading();
    try {
        await loadStoryIntoEditModal(storyKey);
        
        const modalElement = document.getElementById('editStoryModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } else {
            console.error('Modal element not found');
            showToast('Error: Modal not found', 'error');
        }
        
    } catch (error) {
        console.error('Error opening edit modal:', error);
        showToast('Error loading story data: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// SAVE STORY EDIT
// ============================================

async function saveStoryEdit() {
    const storyKey = document.getElementById('editStoryKey').value;
    
    const storyData = {
        status: document.getElementById('editStatus').value,
        published_date: document.getElementById('editPublishedDate').value || null,
        medium_url: document.getElementById('editMediumUrl').value || null,
        tags: document.getElementById('editTags').value.split(',').map(t => t.trim()).filter(t => t),
        notes: document.getElementById('editNotes').value,
        medium_publication: document.getElementById('editPublication').value || null,
        linkedin_status: document.getElementById('editLinkedinStatus').value || null,
        linkedin_timestamp: document.getElementById('editLinkedinTimestamp').value || null,
        linkedin_impressions: parseInt(document.getElementById('editLinkedinImpressions').value) || 0,
        linkedin_url: document.getElementById('editLinkedinUrl').value || null,
        series: document.getElementById('editSeries').value || null
    };
    
    const monthlyData = {
        member_reads: parseInt(document.getElementById('editMemberReads').value) || 0,
        nonmember_reads: parseInt(document.getElementById('editNonMemberReads').value) || 0,
        member_views: parseInt(document.getElementById('editMemberViews').value) || 0,
        nonmember_views: parseInt(document.getElementById('editNonMemberViews').value) || 0,
        claps: parseInt(document.getElementById('editClaps').value) || 0,
        responses: parseInt(document.getElementById('editResponses').value) || 0,
        leaderboard: document.getElementById('editLeaderboard').value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editLeaderboardNanos').value) || 0
    };
    
    let yearmonth = window.currentEditMonth;
    if (!yearmonth) {
        const now = new Date();
        yearmonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }
    
    showLoading();
    try {
        await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(storyData)
        });
        
        await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats/${yearmonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
        if (modal) modal.hide();
        
        await loadStories();
        showToast('Story saved', 'success');
        
    } catch (error) {
        console.error('Error saving story:', error);
        showToast('Error saving story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// REFRESH CURRENT STORY STATS (for edit modal button)
// ============================================

async function refreshCurrentStoryStats() {
    if (!currentEditStoryKey) {
        showToast('No story selected', 'error');
        return;
    }
    
    let yearmonth = null;
    if (currentMonth !== 'all') {
        yearmonth = currentMonth;
    }
    
    await refreshStoryStats(currentEditStoryKey, yearmonth);
}

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
}

// ============================================
// MONTH SELECTOR
// ============================================

async function loadMonths() {
    try {
        const response = await fetch(`${API_BASE}/stories/months`);
        const data = await response.json();
        
        const selector = document.getElementById('monthSelector');
        selector.innerHTML = '<option value="all">All Time</option>';
        
        if (data.months) {
            data.months.forEach(month => {
                const option = document.createElement('option');
                option.value = month;
                option.textContent = month;
                selector.appendChild(option);
            });
        }
        
        const savedMonth = localStorage.getItem('selectedMonth');
        if (savedMonth && savedMonth !== 'all') {
            selector.value = savedMonth;
        }
        currentMonth = selector.value;
        
        await loadStories();
        
    } catch (error) {
        console.error('Error loading months:', error);
    }
}

async function onMonthChange() {
    const selector = document.getElementById('monthSelector');
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
        let url;
        if (currentMonth === 'all') {
            url = `${API_BASE}/stories/list`;
        } else {
            url = `${API_BASE}/stories/list/${currentMonth}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        allStories = data.stories || [];
        
        // Populate series filter
        const seriesSet = new Set();
        allStories.forEach(s => { if (s.series) seriesSet.add(s.series); });
        const seriesSelect = document.getElementById('seriesFilter');
        seriesSelect.innerHTML = '<option value="">All Series</option>';
        Array.from(seriesSet).sort().forEach(s => {
            const option = document.createElement('option');
            option.value = s;
            option.textContent = s;
            seriesSelect.appendChild(option);
        });
        
        renderStoryTable();
        
        if (currentMonth === 'all') {
            updateDashboardStats();
        }
        
    } catch (error) {
        console.error('Error loading stories:', error);
        showToast('Error loading stories', 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// RENDER STORY TABLE
// ============================================

function applyFilters() {
    renderStoryTable();
}

function clearFilters() {
    document.getElementById('statusFilter').value = 'All';
    document.getElementById('seriesFilter').value = '';
    document.getElementById('searchFilter').value = '';
    document.getElementById('bookmarkFilter').checked = false;
    document.getElementById('leaderboardFilter').checked = false;
    renderStoryTable();
}

function renderStoryTable() {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;
    
    const statusFilter = document.getElementById('statusFilter').value;
    const seriesFilter = document.getElementById('seriesFilter').value;
    const searchText = document.getElementById('searchFilter').value.toLowerCase();
    const bookmarkedOnly = document.getElementById('bookmarkFilter').checked;
    const leaderboardOnly = document.getElementById('leaderboardFilter').checked;
    
    let filtered = [...allStories];
    if (statusFilter !== 'All') filtered = filtered.filter(s => s.status === statusFilter);
    if (seriesFilter) filtered = filtered.filter(s => s.series === seriesFilter);
    if (searchText) filtered = filtered.filter(s => s.name.toLowerCase().includes(searchText));
    if (bookmarkedOnly) filtered = filtered.filter(s => s.bookmarked === true);
    if (leaderboardOnly) filtered = filtered.filter(s => s.leaderboard === true);
    
    filtered.sort((a, b) => {
        let aVal = a[currentSort.column];
        let bVal = b[currentSort.column];
        
        if (typeof aVal === 'boolean') {
            aVal = aVal ? 1 : 0;
            bVal = bVal ? 1 : 0;
        }
        
        if (typeof aVal === 'string') {
            aVal = (aVal || '').toLowerCase();
            bVal = (bVal || '').toLowerCase();
        }
        
        if (currentSort.direction === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
    
    document.getElementById('filterCountDisplay').textContent = `Showing ${filtered.length} of ${allStories.length} stories`;
    
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="text-center text-muted py-3">No stories found</td</tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    filtered.forEach(story => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        row.onclick = () => openEditModal(story.key);
        
        // Bookmark cell
        const bookmarkCell = row.insertCell(0);
        bookmarkCell.className = 'text-center';
        bookmarkCell.onclick = (e) => e.stopPropagation();
        const bookmarkIcon = document.createElement('i');
        bookmarkIcon.className = `bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}`;
        bookmarkIcon.onclick = () => toggleBookmark(story.key, !story.bookmarked);
        bookmarkCell.appendChild(bookmarkIcon);
        
        // Leaderboard cell
        const leaderboardCell = row.insertCell(1);
        leaderboardCell.className = 'text-center';
        leaderboardCell.onclick = (e) => e.stopPropagation();
        const trophyIcon = document.createElement('i');
        trophyIcon.className = `bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}`;
        trophyIcon.onclick = () => toggleLeaderboard(story.key, !story.leaderboard);
        leaderboardCell.appendChild(trophyIcon);
        
        // Status cell
        const statusCell = row.insertCell(2);
        const statusSpan = document.createElement('span');
        const statusClass = `status-${story.status?.toLowerCase() || 'draft'}`;
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = story.status || 'Draft';
        statusCell.appendChild(statusSpan);
        
        // Name cell
        const nameCell = row.insertCell(3);
        nameCell.textContent = story.name;
        
        // Series cell
        const seriesCell = row.insertCell(4);
        seriesCell.textContent = story.series || '—';
        
        // Published date cell
        const dateCell = row.insertCell(5);
        const publishDate = story.published_date ? story.published_date.split('T')[0] : (story.medium_first_published ? story.medium_first_published.split('T')[0] : '-');
        dateCell.textContent = publishDate;
        
        // Reads cell
        const readsCell = row.insertCell(6);
        readsCell.className = 'stats-tooltip';
        readsCell.title = `${story.member_reads} of ${story.reads} reads (${story.reads_percent}% members)`;
        readsCell.innerHTML = `${formatNumber(story.reads)}<br><small>${story.reads_percent}%</small>`;
        
        // Views cell
        const viewsCell = row.insertCell(7);
        viewsCell.className = 'stats-tooltip';
        viewsCell.title = `${story.member_views} of ${story.views} views (${story.views_percent}% members)`;
        viewsCell.textContent = formatNumber(story.views);
        
        // Claps cell
        const clapsCell = row.insertCell(8);
        clapsCell.textContent = formatNumber(story.claps);
        
        // Impressions cell
        const impressionsCell = row.insertCell(9);
        impressionsCell.textContent = formatNumber(story.linkedin_impressions);
        
        // LinkedIn cell
        const linkedinCell = row.insertCell(10);
        const linkedinSpan = document.createElement('span');
        let linkedinText = 'Not Posted';
        let linkedinClass = 'linkedin-not-posted';
        if (story.linkedin_status === 'scheduled') {
            linkedinText = '📅 Scheduled';
            linkedinClass = 'linkedin-scheduled';
        } else if (story.linkedin_status === 'posted') {
            linkedinText = '✅ Posted';
            linkedinClass = 'linkedin-posted';
        }
        linkedinSpan.className = `linkedin-badge ${linkedinClass}`;
        linkedinSpan.textContent = linkedinText;
        linkedinCell.appendChild(linkedinSpan);
        
        // Lifetime cell
        const lifetimeCell = row.insertCell(11);
        lifetimeCell.className = 'stats-tooltip';
        lifetimeCell.title = 'Lifetime Reads/Views/Claps';
        lifetimeCell.innerHTML = `${formatNumber(story.lifetime_reads)}/${formatNumber(story.lifetime_views)}/${formatNumber(story.lifetime_claps)}`;
        
        // Actions cell
        const actionsCell = row.insertCell(12);
        actionsCell.className = 'action-buttons';
        actionsCell.onclick = (e) => e.stopPropagation();
        
        const statsBtn = document.createElement('button');
        statsBtn.className = 'btn btn-sm btn-outline-info';
        statsBtn.title = 'Stats';
        statsBtn.innerHTML = '<i class="bi bi-graph-up"></i>';
        statsBtn.onclick = () => openStatsModal(story.key);
        actionsCell.appendChild(statsBtn);
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary ms-1';
        editBtn.title = 'Edit';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.onclick = () => openEditModal(story.key);
        actionsCell.appendChild(editBtn);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger ms-1';
        deleteBtn.title = 'Delete';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.onclick = () => deleteStory(story.key);
        actionsCell.appendChild(deleteBtn);
    });
}

// ============================================
// DASHBOARD STATS
// ============================================

function updateDashboardStats() {
    const totalCountEl = document.getElementById('totalCount');
    if (!totalCountEl) return;
    
    const total = allStories.length;
    const published = allStories.filter(s => s.status === 'Published').length;
    const ready = allStories.filter(s => s.status === 'Ready').length;
    const draft = allStories.filter(s => s.status === 'Draft').length;
    const done = allStories.filter(s => s.status === 'Done').length;
    const bookmarked = allStories.filter(s => s.bookmarked === true).length;
    const leaderboard = allStories.filter(s => s.leaderboard === true).length;
    
    const totalReads = allStories.reduce((sum, s) => sum + s.reads, 0);
    const totalViews = allStories.reduce((sum, s) => sum + s.views, 0);
    const totalClaps = allStories.reduce((sum, s) => sum + s.claps, 0);
    const memberReads = allStories.reduce((sum, s) => sum + s.member_reads, 0);
    const memberViews = allStories.reduce((sum, s) => sum + s.member_views, 0);
    const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
    const memberReadPercent = totalReads > 0 ? Math.round((memberReads / totalReads) * 100) : 0;
    const memberViewPercent = totalViews > 0 ? Math.round((memberViews / totalViews) * 100) : 0;
    
    document.getElementById('totalCount').textContent = total;
    document.getElementById('publishedCount').textContent = published;
    document.getElementById('readyCount').textContent = ready;
    document.getElementById('draftCount').textContent = draft;
    document.getElementById('doneCount').textContent = done;
    document.getElementById('bookmarkedCount').textContent = bookmarked;
    document.getElementById('leaderboardStoryCount').textContent = leaderboard;
    document.getElementById('totalReads').innerHTML = `${formatNumber(memberReads)}/${formatNumber(totalReads)}`;
    document.getElementById('memberReadPercent').textContent = `${memberReadPercent}% members`;
    document.getElementById('totalViews').innerHTML = `${formatNumber(memberViews)}/${formatNumber(totalViews)}`;
    document.getElementById('memberViewPercent').textContent = `${memberViewPercent}% members`;
    document.getElementById('readRatio').textContent = `${readRatio}%`;
    document.getElementById('totalClaps').textContent = formatNumber(totalClaps);
}

// ============================================
// TOGGLE ACTIONS
// ============================================

async function toggleBookmark(storyKey, newState) {
    try {
        await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookmarked: newState })
        });
        await loadStories();
    } catch (error) {
        console.error('Error toggling bookmark:', error);
        showToast('Error updating bookmark', 'error');
    }
}

async function toggleLeaderboard(storyKey, newState) {
    let yearmonth;
    if (currentMonth === 'all') {
        const now = new Date();
        yearmonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    } else {
        yearmonth = currentMonth;
    }
    
    try {
        await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats/${yearmonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ leaderboard: newState })
        });
        await loadStories();
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
        showToast('Error updating leaderboard', 'error');
    }
}

// ============================================
// DELETE STORY
// ============================================

async function deleteStory(storyKey) {
    if (!confirm('Delete this story?')) return;
    
    try {
        await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`, {
            method: 'DELETE'
        });
        await loadStories();
        showToast('Story deleted', 'success');
    } catch (error) {
        console.error('Error deleting story:', error);
        showToast('Error deleting story', 'error');
    }
}

// ============================================
// ADD STORY MODAL
// ============================================

async function openAddStoryModal() {
    try {
        const seriesResponse = await fetch(`${API_BASE}/series/`);
        const seriesList = await seriesResponse.json();
        
        const seriesSelect = document.getElementById('addStorySeries');
        seriesSelect.innerHTML = '<option value="">None</option>';
        if (Array.isArray(seriesList)) {
            seriesList.forEach(s => {
                const option = document.createElement('option');
                option.value = s.name;
                option.textContent = s.name;
                seriesSelect.appendChild(option);
            });
        }
        
        document.getElementById('addStoryCreatedDate').value = getTodayDate();
        document.getElementById('addStoryName').value = '';
        document.getElementById('addStoryTags').value = '';
        document.getElementById('addStoryReadTime').value = '';
        
        const modal = new bootstrap.Modal(document.getElementById('addStoryModal'));
        modal.show();
    } catch (error) {
        console.error('Error opening add modal:', error);
        showToast('Error loading series', 'error');
    }
}

async function createStory() {
    const name = document.getElementById('addStoryName').value.trim();
    if (!name) {
        showToast('Story name is required', 'error');
        return;
    }
    
    const data = {
        name: name,
        series: document.getElementById('addStorySeries').value || null,
        tags: document.getElementById('addStoryTags').value.split(',').map(t => t.trim()).filter(t => t),
        read_time: parseInt(document.getElementById('addStoryReadTime').value) || null,
        created_date: document.getElementById('addStoryCreatedDate').value || getTodayDate()
    };
    
    showLoading();
    try {
        await fetch(`${API_BASE}/stories/story`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('addStoryModal'));
        if (modal) modal.hide();
        
        await loadStories();
        showToast('Story created', 'success');
        
    } catch (error) {
        console.error('Error creating story:', error);
        showToast('Error creating story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// STATS MODAL
// ============================================

async function openStatsModal(storyKey) {
    currentStatsStoryKey = storyKey;
    showLoading();
    try {
        const storyResponse = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`);
        const story = await storyResponse.json();
        
        const statsResponse = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats`);
        const statsData = await statsResponse.json();
        
        document.getElementById('statsStoryName').textContent = story.name;
        
        const now = new Date();
        const currentYearMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        const currentMonthStats = (statsData.months || []).find(m => m.yearmonth === currentYearMonth) || 
                                  (statsData.months && statsData.months.length > 0 ? statsData.months[0] : {});
        
        document.getElementById('statsReads').textContent = formatNumber(currentMonthStats.reads || 0);
        document.getElementById('statsViews').textContent = formatNumber(currentMonthStats.views || 0);
        document.getElementById('statsClaps').textContent = formatNumber(currentMonthStats.claps || 0);
        document.getElementById('statsMemberReads').textContent = formatNumber(currentMonthStats.member_reads || 0);
        document.getElementById('statsMemberViews').textContent = formatNumber(currentMonthStats.member_views || 0);
        document.getElementById('statsLifetimeReads').textContent = formatNumber(story.lifetime_reads || 0);
        document.getElementById('statsLifetimeViews').textContent = formatNumber(story.lifetime_views || 0);
        document.getElementById('statsLifetimeClaps').textContent = formatNumber(story.lifetime_claps || 0);
        
        const modal = new bootstrap.Modal(document.getElementById('statsModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Error loading stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// LEADERBOARD UPDATE
// ============================================

async function updateLeaderboardStats() {
    let yearmonth;
    if (currentMonth === 'all') {
        const now = new Date();
        yearmonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    } else {
        yearmonth = currentMonth;
    }
    
    if (!yearmonth) {
        showToast('No month selected', 'error');
        return;
    }
    
    if (!confirm(`Fetch leaderboard stats for ${yearmonth}?`)) return;
    
    showLoading();
    try {
        await fetch(`${API_BASE}/stories/fetch-leaderboard-stats/${yearmonth}`, { method: 'POST' });
        await loadStories();
        showToast('Leaderboard stats updated', 'success');
        
    } catch (error) {
        console.error('Error updating leaderboard:', error);
        showToast('Error updating leaderboard stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', async () => {
    await loadMonths();
});