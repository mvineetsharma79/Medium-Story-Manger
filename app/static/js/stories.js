// app/static/js/stories.js

let allStories = [];
let allSeriesNames = [];
let currentSort = { column: 'title', direction: 'asc' };

// ============================================
// LOAD STORIES
// ============================================

async function loadStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/list`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        allStories = data.stories || [];
        
        // Extract unique series names
        const seriesSet = new Set();
        allStories.forEach(story => {
            if (story.series && story.series !== 'null' && story.series !== '') {
                seriesSet.add(story.series);
            }
        });
        allSeriesNames = Array.from(seriesSet).sort();
        
        updateSeriesDropdown();
        renderStoryTable();
        updateFilterCount();
    } catch (error) {
        console.error('Error loading stories:', error);
        showToast('Error loading stories: ' + error.message, 'error');
    } finally {
        hideLoading();
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

function updateFilterCount() {
    const filtered = getFilteredStories();
    const filterCountDisplay = document.getElementById('filterCountDisplay');
    if (filterCountDisplay) {
        filterCountDisplay.textContent = `Showing ${filtered.length} of ${allStories.length} stories`;
    }
}

function getFilteredStories() {
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkedOnly = document.getElementById('bookmarkFilter');
    const leaderboardOnly = document.getElementById('leaderboardFilter');
    
    let filtered = [...allStories];
    
    if (statusFilter && statusFilter.value !== 'All') {
        filtered = filtered.filter(s => s.status === statusFilter.value);
    }
    if (seriesFilter && seriesFilter.value) {
        filtered = filtered.filter(s => s.series === seriesFilter.value);
    }
    if (searchFilter && searchFilter.value) {
        const searchTerm = searchFilter.value.toLowerCase();
        filtered = filtered.filter(s => {
            return (s.title && s.title.toLowerCase().includes(searchTerm)) ||
                   (s.name && s.name.toLowerCase().includes(searchTerm));
        });
    }
    if (bookmarkedOnly && bookmarkedOnly.checked) {
        filtered = filtered.filter(s => s.bookmarked === true);
    }
    if (leaderboardOnly && leaderboardOnly.checked) {
        filtered = filtered.filter(s => s.leaderboard === true);
    }
    
    return filtered;
}

function getSortedStories() {
    const filtered = getFilteredStories();
    
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
        if (typeof aVal === 'number') {
            aVal = aVal || 0;
            bVal = bVal || 0;
        }
        
        return currentSort.direction === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
    });
    
    return filtered;
}

function renderStoryTable() {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;
    
    const sortedStories = getSortedStories();
    tbody.innerHTML = '';
    
    if (sortedStories.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 13;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No stories found';
        return;
    }
    
    sortedStories.forEach(story => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        
        const uniqueSlug = story.uniqueSlug || story.key?.split('/').pop();
        const encodedSlug = encodeURIComponent(uniqueSlug);
        
        // Get medium data (nested object)
        const medium = story.medium || {};
        const totalStats = medium.totalStats || {};
        const monthlyStats = medium.monthlyStats || [];
        const currentMonthStats = monthlyStats.length > 0 ? monthlyStats[monthlyStats.length - 1] : {};
        const totalEarnings = medium.totalEarnings || {};
        const monthlyEarnings = medium.monthlyEarnings || [];
        const currentMonthEarnings = monthlyEarnings.length > 0 ? monthlyEarnings[monthlyEarnings.length - 1] : {};
        
        // Get LinkedIn data
        const linkedin = story.linkedin || {};
        
        // 1. Bookmark
        const bookmarkCell = row.insertCell(0);
        bookmarkCell.className = 'text-center';
        const bookmarkIcon = document.createElement('i');
        bookmarkIcon.className = `bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}`;
        bookmarkIcon.style.cursor = 'pointer';
        bookmarkIcon.onclick = (e) => { e.stopPropagation(); toggleBookmark(encodedSlug); };
        bookmarkCell.appendChild(bookmarkIcon);
        
        // 2. Leaderboard
        const leaderboardCell = row.insertCell(1);
        leaderboardCell.className = 'text-center';
        const leaderboardIcon = document.createElement('i');
        leaderboardIcon.className = `bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}`;
        leaderboardIcon.style.cursor = 'pointer';
        leaderboardIcon.onclick = (e) => { e.stopPropagation(); toggleLeaderboard(encodedSlug); };
        leaderboardCell.appendChild(leaderboardIcon);
        
        // 3. Status
        const statusCell = row.insertCell(2);
        const statusSpan = document.createElement('span');
        const statusClass = story.status === 'Published' ? 'status-published' : 
                           story.status === 'Ready' ? 'status-ready' : 
                           story.status === 'Done' ? 'status-done' : 'status-draft';
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = story.status || 'Draft';
        statusCell.appendChild(statusSpan);
        
        // 4. Title (click = edit modal)
        const titleCell = row.insertCell(3);
        const titleStrong = document.createElement('strong');
        titleStrong.style.cursor = 'pointer';
        titleStrong.textContent = story.title || story.name || 'Unknown';
        titleStrong.onclick = () => openEditStory(encodedSlug);
        titleCell.appendChild(titleStrong);
        
        // 5. Series
        const seriesCell = row.insertCell(4);
        if (story.series) {
            const seriesSpan = document.createElement('span');
            seriesSpan.className = 'series-badge';
            seriesSpan.style.cursor = 'pointer';
            seriesSpan.textContent = story.series;
            seriesSpan.onclick = (e) => { e.stopPropagation(); filterBySeries(story.series); };
            seriesCell.appendChild(seriesSpan);
        } else {
            seriesCell.textContent = '—';
            seriesCell.className = 'text-muted';
        }
        
        // 6. Created Date (from story root)
        const createdCell = row.insertCell(5);
        createdCell.textContent = story.createdDate ? story.createdDate.split('T')[0] : '-';
        
        // 7. Published Date (from story root)
        const publishedCell = row.insertCell(6);
        publishedCell.textContent = story.publishedDate ? story.publishedDate.split('T')[0] : '-';
        
        // 8. Engagement (claps / voters / followers from medium)
        const engagementCell = row.insertCell(7);
        const engagementSmall = document.createElement('small');
        const claps = medium.clapCount || 0;
        const voters = medium.voterCount || 0;
        const followers = medium.followerCount || 0;
        engagementSmall.innerHTML = `💚 ${formatNumber(claps)}<br>👥 ${formatNumber(voters)}<br>📢 ${formatNumber(followers)}`;
        engagementCell.appendChild(engagementSmall);
        
        // 9. Earnings (Monthly / Total from medium)
        const earningsCell = row.insertCell(8);
        const earningsSmall = document.createElement('small');
        const monthlyEarnNanos = currentMonthEarnings.nanos || 0;
        const totalEarnNanos = totalEarnings.nanos || 0;
        earningsSmall.innerHTML = `💰 $${(monthlyEarnNanos / 1000000000).toFixed(2)}<br>🏦 $${(totalEarnNanos / 1000000000).toFixed(2)}`;
        earningsCell.appendChild(earningsSmall);
        
        // 10. Impression (reads / views / responses from medium totalStats)
        const impressionCell = row.insertCell(9);
        const impressionSmall = document.createElement('small');
        const reads = totalStats.reads || 0;
        const views = totalStats.views || 0;
        const responses = medium.responsesCount || 0;
        impressionSmall.innerHTML = `📖 ${formatNumber(reads)}<br>👁️ ${formatNumber(views)}<br>💬 ${formatNumber(responses)}`;
        impressionCell.appendChild(impressionSmall);
        
        // 11. Read Time (from medium)
        const readTimeCell = row.insertCell(10);
        const readTimeSmall = document.createElement('small');
        const readingTime = medium.readingTime || 0;
        const hours = Math.floor(readingTime / 60);
        const minutes = readingTime % 60;
        const timeStr = hours > 0 ? `${hours}:${minutes.toString().padStart(2, '0')}` : `${minutes}:00`;
        const wordCount = medium.wordCount || 0;
        readTimeSmall.innerHTML = `⏱️ ${timeStr}<br>📝 ${formatNumber(wordCount)}`;
        readTimeCell.appendChild(readTimeSmall);
        
        // 12. LinkedIn (from linkedin object)
        const linkedinCell = row.insertCell(11);
        const linkedinSpan = document.createElement('span');
        const linkedinStatus = linkedin.status || story.linkedin_status;
        if (linkedinStatus === 'scheduled') {
            linkedinSpan.className = 'linkedin-badge linkedin-scheduled';
            linkedinSpan.textContent = '📅 Scheduled';
        } else if (linkedinStatus === 'posted') {
            linkedinSpan.className = 'linkedin-badge linkedin-posted';
            linkedinSpan.textContent = '✅ Posted';
        } else {
            linkedinSpan.className = 'linkedin-badge linkedin-not-posted';
            linkedinSpan.textContent = 'Not Posted';
        }
        linkedinCell.appendChild(linkedinSpan);
        
        // 13. Actions
        const actionsCell = row.insertCell(12);
        actionsCell.className = 'action-buttons';
        
        const statsBtn = document.createElement('button');
        statsBtn.className = 'btn btn-sm btn-outline-info';
        statsBtn.title = 'Stats Dashboard';
        statsBtn.onclick = (e) => { e.stopPropagation(); showStatsDashboard(encodedSlug); };
        const statsIcon = document.createElement('i');
        statsIcon.className = 'bi bi-graph-up';
        statsBtn.appendChild(statsIcon);
        actionsCell.appendChild(statsBtn);
        
        const externalBtn = document.createElement('button');
        externalBtn.className = 'btn btn-sm btn-outline-secondary ms-1';
        externalBtn.title = 'Open on Medium';
        const mediumUrl = medium.mediumUrl || story.medium_url;
        if (mediumUrl) {
            externalBtn.onclick = (e) => { e.stopPropagation(); window.open(mediumUrl, '_blank'); };
        } else {
            externalBtn.disabled = true;
        }
        const externalIcon = document.createElement('i');
        externalIcon.className = 'bi bi-box-arrow-up-right';
        externalBtn.appendChild(externalIcon);
        actionsCell.appendChild(externalBtn);
    });
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
// FILTERS
// ============================================

function applyFilters() {
    renderStoryTable();
    updateFilterCount();
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
    
    renderStoryTable();
    updateFilterCount();
}

function filterBySeries(seriesName) {
    if (!seriesName) return;
    const seriesFilter = document.getElementById('seriesFilter');
    if (seriesFilter) {
        seriesFilter.value = seriesName;
        renderStoryTable();
        updateFilterCount();
    }
}

// ============================================
// TOGGLE BOOKMARK & LEADERBOARD
// ============================================

async function toggleBookmark(encodedSlug) {
    const uniqueSlug = decodeURIComponent(encodedSlug);
    const story = allStories.find(s => (s.uniqueSlug || s.key?.split('/').pop()) === uniqueSlug);
    if (!story) return;
    
    const newState = !story.bookmarked;
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedSlug}`, {
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
        showToast('Error updating bookmark', 'error');
    }
}

async function toggleLeaderboard(encodedSlug) {
    const uniqueSlug = decodeURIComponent(encodedSlug);
    const story = allStories.find(s => (s.uniqueSlug || s.key?.split('/').pop()) === uniqueSlug);
    if (!story) return;
    
    const newState = !story.leaderboard;
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedSlug}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ leaderboard: newState })
        });
        
        if (response.ok) {
            story.leaderboard = newState;
            renderStoryTable();
            if (window.updateLeaderboardTotal) window.updateLeaderboardTotal();
            showToast('Leaderboard updated', 'success');
        }
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
        showToast('Error updating leaderboard', 'error');
    }
}

// ============================================
// MODAL FUNCTIONS
// ============================================

async function openEditStory(encodedSlug) {
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedSlug}`);
        const storyData = await response.json();
        
        const medium = storyData.medium || {};
        
        document.getElementById('editStoryUniqueSlug').value = storyData.uniqueSlug;
        document.getElementById('editStoryTitle').value = storyData.title || '';
        document.getElementById('editStoryStatus').value = storyData.status || 'Draft';
        document.getElementById('editStorySeries').value = storyData.series || '';
        document.getElementById('editStoryCreatedDate').value = storyData.createdDate?.split('T')[0] || '';
        document.getElementById('editStoryPublishedDate').value = storyData.publishedDate?.split('T')[0] || '';
        document.getElementById('editStoryNotes').value = storyData.notes || '';
        document.getElementById('editStoryTags').value = (medium.tags || []).join(', ');
        document.getElementById('editStoryMediumUrl').value = medium.mediumUrl || storyData.medium_url || '';
        
        const linkedin = storyData.linkedin || {};
        document.getElementById('editStoryLinkedinStatus').value = linkedin.status || storyData.linkedin_status || '';
        document.getElementById('editStoryLinkedinTimestamp').value = linkedin.timestamp || storyData.linkedin_timestamp || '';
        document.getElementById('editStoryLinkedinImpressions').value = linkedin.impressions || storyData.linkedin_impressions || 0;
        document.getElementById('editStoryLinkedinUrl').value = linkedin.url || storyData.linkedin_url || '';
        
        const modalEl = document.getElementById('editStoryModal');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    } catch (error) {
        console.error('Error loading story for edit:', error);
        showToast('Error loading story: ' + error.message, 'error');
    }
}

async function saveStoryEdit() {
    const uniqueSlug = document.getElementById('editStoryUniqueSlug')?.value;
    if (!uniqueSlug) return;
    
    const updateData = {
        title: document.getElementById('editStoryTitle')?.value,
        status: document.getElementById('editStoryStatus')?.value,
        series: document.getElementById('editStorySeries')?.value || null,
        createdDate: document.getElementById('editStoryCreatedDate')?.value || null,
        publishedDate: document.getElementById('editStoryPublishedDate')?.value || null,
        notes: document.getElementById('editStoryNotes')?.value || '',
        tags: document.getElementById('editStoryTags')?.value.split(',').map(t => t.trim()).filter(t => t),
        medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions')?.value) || 0,
        linkedin_url: document.getElementById('editStoryLinkedinUrl')?.value || null
    };
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });
        
        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
            if (modal) modal.hide();
            await loadStories();
            showToast('Story saved successfully', 'success');
        } else {
            const error = await response.json();
            showToast('Error saving story: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error saving story:', error);
        showToast('Error saving story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function showStatsDashboard(encodedSlug) {
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    
    while (contentDiv.firstChild) {
        contentDiv.removeChild(contentDiv.firstChild);
    }
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'text-center py-3';
    loadingDiv.innerHTML = '<div class="spinner-border text-primary"></div><p>Loading stats...</p>';
    contentDiv.appendChild(loadingDiv);
    
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedSlug}`);
        const storyData = await response.json();
        
        while (contentDiv.firstChild) {
            contentDiv.removeChild(contentDiv.firstChild);
        }
        
        const medium = storyData.medium || {};
        const totalStats = medium.totalStats || {};
        const totalEarnings = medium.totalEarnings || {};
        
        const container = document.createElement('div');
        container.className = 'compact-stats';
        
        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between align-items-center mb-3';
        const titleStrong = document.createElement('strong');
        titleStrong.textContent = storyData.title;
        header.appendChild(titleStrong);
        const viewLink = document.createElement('a');
        viewLink.href = medium.mediumUrl || storyData.medium_url || '#';
        viewLink.target = '_blank';
        viewLink.className = 'btn btn-sm btn-outline-primary';
        viewLink.innerHTML = '<i class="bi bi-box-arrow-up-right"></i> View on Medium';
        header.appendChild(viewLink);
        container.appendChild(header);
        
        const lifetimeSection = document.createElement('div');
        lifetimeSection.className = 'row g-2 mb-3';
        const lifetimeTitle = document.createElement('div');
        lifetimeTitle.className = 'col-12';
        lifetimeTitle.innerHTML = '<strong>📊 Lifetime Stats</strong>';
        lifetimeSection.appendChild(lifetimeTitle);
        
        const readsCard = createStatCard('Reads', formatNumber(totalStats.reads || 0), 'bg-info');
        const viewsCard = createStatCard('Views', formatNumber(totalStats.views || 0), 'bg-primary');
        const clapsCard = createStatCard('Claps', formatNumber(medium.clapCount || 0), 'bg-success');
        
        lifetimeSection.appendChild(readsCard);
        lifetimeSection.appendChild(viewsCard);
        lifetimeSection.appendChild(clapsCard);
        container.appendChild(lifetimeSection);
        
        const earningsSection = document.createElement('div');
        earningsSection.className = 'row g-2';
        const earningsTitle = document.createElement('div');
        earningsTitle.className = 'col-12';
        earningsTitle.innerHTML = '<strong>💰 Earnings</strong>';
        earningsSection.appendChild(earningsTitle);
        
        const totalEarningsCard = createStatCard('Total Earnings', `$${(totalEarnings.nanos / 1000000000).toFixed(2)}`, 'bg-warning', 'text-dark');
        const responsesCard = createStatCard('Responses', formatNumber(medium.responsesCount || 0), 'bg-secondary');
        
        earningsSection.appendChild(totalEarningsCard);
        earningsSection.appendChild(responsesCard);
        container.appendChild(earningsSection);
        
        contentDiv.appendChild(container);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        while (contentDiv.firstChild) {
            contentDiv.removeChild(contentDiv.firstChild);
        }
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.textContent = 'Error loading stats: ' + error.message;
        contentDiv.appendChild(errorDiv);
    }
}

function createStatCard(label, value, bgClass, textClass = 'text-white') {
    const col = document.createElement('div');
    col.className = 'col-4';
    
    const card = document.createElement('div');
    card.className = `card ${bgClass} ${textClass} p-2 text-center`;
    
    const small = document.createElement('small');
    small.textContent = label;
    
    const h5 = document.createElement('h5');
    h5.textContent = value;
    
    card.appendChild(small);
    card.appendChild(h5);
    col.appendChild(card);
    
    return col;
}

// ============================================
// REFRESH STATS & SYNC
// ============================================

async function refreshStats() {
    const period = getCurrentYearMonth();
    if (!confirm(`Refresh stats from Medium for ${period}?`)) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/refresh-stats/${period}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            await loadStories();
            showToast(`Stats refreshed: ${data.new_stories} new, ${data.updated_stories} updated`, 'success');
        } else {
            showToast('Error: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function syncStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            await loadStories();
            showToast(`Sync completed: ${data.added || 0} added, ${data.updated || 0} updated`, 'success');
        } else {
            showToast('Error syncing stories', 'error');
        }
    } catch (error) {
        showToast('Error syncing stories: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// ADD STORY
// ============================================

async function openAddStoryModal() {
    try {
        const response = await fetch(`${API_BASE}/series/`);
        const seriesList = await response.json();
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect && Array.isArray(seriesList)) {
            seriesSelect.innerHTML = '<option value="">None</option>';
            seriesList.forEach(s => {
                const option = document.createElement('option');
                option.value = s.name;
                option.textContent = s.name;
                seriesSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading series:', error);
    }
    
    document.getElementById('addStoryTitle').value = '';
    document.getElementById('addStoryCreatedDate').value = getTodayDate();
    document.getElementById('addStoryMediumUrl').value = '';
    
    const modalEl = document.getElementById('addStoryModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

async function createStory() {
    const title = document.getElementById('addStoryTitle')?.value.trim();
    if (!title) {
        showToast('Story title is required', 'error');
        return;
    }
    
    const uniqueSlug = title.toLowerCase().replace(/[^\w\s-]/g, '').replace(/[\s]+/g, '-').replace(/-+/g, '-').substring(0, 100);
    
    const data = {
        uniqueSlug: uniqueSlug,
        title: title,
        folder: document.getElementById('addStorySeries')?.value || null,
        series: document.getElementById('addStorySeries')?.value || null,
        createdDate: document.getElementById('addStoryCreatedDate')?.value || getTodayDate(),
        medium_url: document.getElementById('addStoryMediumUrl')?.value || null
    };
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('addStoryModal'));
            if (modal) modal.hide();
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
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    loadStories();
    
    document.getElementById('statusFilter')?.addEventListener('change', applyFilters);
    document.getElementById('seriesFilter')?.addEventListener('change', applyFilters);
    document.getElementById('searchFilter')?.addEventListener('keyup', applyFilters);
    document.getElementById('bookmarkFilter')?.addEventListener('change', applyFilters);
    document.getElementById('leaderboardFilter')?.addEventListener('change', applyFilters);
    
    document.getElementById('addStoryCreateBtn')?.addEventListener('click', createStory);
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
});

window.sortStories = sortStories;
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;
window.filterBySeries = filterBySeries;
window.toggleBookmark = toggleBookmark;
window.toggleLeaderboard = toggleLeaderboard;
window.openEditStory = openEditStory;
window.showStatsDashboard = showStatsDashboard;
window.refreshStats = refreshStats;
window.syncStories = syncStories;
window.openAddStoryModal = openAddStoryModal;