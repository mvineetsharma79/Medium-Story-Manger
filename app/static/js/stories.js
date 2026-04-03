// ============================================
// Stories CRUD Functions
// ============================================

let filterState = { status: 'All', series: '', search: '', bookmarked: false, leaderboard: false };
let sortState = { stories: { column: 'reads', direction: 'desc' } };

function saveFilterState() {
    filterState.status = document.getElementById('statusFilter')?.value || 'All';
    filterState.series = document.getElementById('seriesFilter')?.value || '';
    filterState.search = document.getElementById('searchFilter')?.value || '';
    filterState.bookmarked = document.getElementById('bookmarkFilter')?.checked || false;
    filterState.leaderboard = document.getElementById('leaderboardFilter')?.checked || false;
}

function restoreFilterState() {
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    const bookmarkFilter = document.getElementById('bookmarkFilter');
    const leaderboardFilter = document.getElementById('leaderboardFilter');
    
    if (statusFilter) statusFilter.value = filterState.status;
    if (seriesFilter) seriesFilter.value = filterState.series;
    if (searchFilter) searchFilter.value = filterState.search;
    if (bookmarkFilter) bookmarkFilter.checked = filterState.bookmarked;
    if (leaderboardFilter) leaderboardFilter.checked = filterState.leaderboard;
    if (typeof filterStories === 'function') filterStories();
}

function filterStories() {
    if (typeof renderStoryTable === 'function') renderStoryTable(window.allStories);
}

function clearFilters() {
    filterState = { status: 'All', series: '', search: '', bookmarked: false, leaderboard: false };
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
    filterStories();
}

function sortStories(column) {
    const direction = sortState.stories.column === column && sortState.stories.direction === 'asc' ? 'desc' : 'asc';
    sortState.stories = { column, direction };
    renderStoryTable(window.allStories);
    updateSortIcons('stories', column, direction);
}

function updateSortIcons(table, column, direction) {
    const headerId = table === 'stories' ? 'storiesTableHeader' : (table === 'series' ? 'seriesTableHeader' : 'calendarTableHeader');
    const header = document.getElementById(headerId);
    if (!header) return;
    
    header.querySelectorAll('.sortable').forEach(th => {
        th.classList.remove('active');
        const iconSpan = th.querySelector('.sort-icon');
        if (iconSpan) iconSpan.textContent = '↕';
    });
    
    const activeTh = header.querySelector(`.sortable[data-sort="${column}"]`);
    if (activeTh) {
        activeTh.classList.add('active');
        const iconSpan = activeTh.querySelector('.sort-icon');
        if (iconSpan) iconSpan.textContent = direction === 'asc' ? '↑' : '↓';
    }
}

async function loadStories() {
    const res = await fetch(`${API_BASE}/stories/`);
    const stories = await res.json();
    window.allStories = stories;
    const statuses = ['All', 'Draft', 'Done', 'Ready', 'Published'];
    
    document.getElementById('content').innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-3">
            <h1 class="h3 mb-0">Stories</h1>
            <div>
                <button class="btn btn-sm btn-primary" data-bs-toggle="modal" data-bs-target="#addStoryModal"><i class="bi bi-plus-lg"></i> Add Story</button>
                <button class="btn btn-sm btn-success ms-2" onclick="updateLeaderboardStats()"><i class="bi bi-trophy"></i> Update Leaderboard Stats</button>
            </div>
        </div>
        <div class="filter-bar d-flex gap-2 flex-wrap">
            <select id="statusFilter" class="form-select form-select-sm w-auto" onchange="saveFilterState(); filterStories()">
                ${statuses.map(s => `<option value="${s}" ${filterState.status === s ? 'selected' : ''}>${s}</option>`).join('')}
            </select>
            <select id="seriesFilter" class="form-select form-select-sm w-auto" onchange="saveFilterState(); filterStories()">
                <option value="">All Series</option>
                ${window.allSeries.map(s => `<option value="${s.name}" ${filterState.series === s.name ? 'selected' : ''}>${s.name}</option>`).join('')}
            </select>
            <input type="text" id="searchFilter" class="form-control form-control-sm w-auto" placeholder="Search..." onkeyup="saveFilterState(); filterStories()" value="${escapeHtml(filterState.search)}">
            <div class="form-check"><input class="form-check-input" type="checkbox" id="bookmarkFilter" onchange="saveFilterState(); filterStories()" ${filterState.bookmarked ? 'checked' : ''}><label class="form-check-label small">Bookmarked</label></div>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="leaderboardFilter" onchange="saveFilterState(); filterStories()" ${filterState.leaderboard ? 'checked' : ''}><label class="form-check-label small">Leaderboard</label></div>
            <button class="btn btn-sm btn-outline-secondary" onclick="clearFilters()">Clear</button>
        </div>
        <div class="mb-2 text-muted"><small id="filterCountDisplay">Showing all ${stories.length} stories</small></div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead id="storiesTableHeader" class="table-light">
                    <tr>
                        <th class="sortable text-center" data-sort="bookmarked" onclick="sortStories('bookmarked')" style="width:35px;"><i class="bi bi-bookmark"></i> <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable text-center" data-sort="leaderboard" onclick="sortStories('leaderboard')" style="width:35px;"><i class="bi bi-trophy"></i> <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="status" onclick="sortStories('status')" style="width:80px;">Status <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="name" onclick="sortStories('name')">Story Name <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="medium_first_published" onclick="sortStories('medium_first_published')" style="width:100px;">Publish Date <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="reads" onclick="sortStories('reads')" style="width:100px;">Reads <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="view_count" onclick="sortStories('view_count')" style="width:100px;">Views <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="claps" onclick="sortStories('claps')" style="width:60px;">Claps <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="linkedin_impressions" onclick="sortStories('linkedin_impressions')" style="width:90px;">Impressions <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th class="sortable" data-sort="lifetime_reads" onclick="sortStories('lifetime_reads')" style="width:100px;">Lifetime <i class="bi bi-arrow-down-up sort-icon"></i></th>
                        <th style="width:90px;">LinkedIn</th>
                        <th style="width:90px;">Publication</th>
                        <th style="width:80px;">Actions</th>
                    </tr>
                </thead>
                <tbody id="storiesTableBody"></tbody>
            </table>
        </div>
    `;
    renderStoryTable(stories);
    restoreFilterState();
    sortStories(sortState.stories.column);
}

function renderStoryTable(stories) {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;
    
    let filtered = [...stories];
    if (filterState.status !== 'All') filtered = filtered.filter(s => s.status === filterState.status);
    if (filterState.series) filtered = filtered.filter(s => s.series === filterState.series);
    if (filterState.search) filtered = filtered.filter(s => s.name.toLowerCase().includes(filterState.search.toLowerCase()));
    if (filterState.bookmarked) filtered = filtered.filter(s => s.bookmarked === true);
    if (filterState.leaderboard) filtered = filtered.filter(s => s.leaderboard === true);
    
    const filterCountDisplay = document.getElementById('filterCountDisplay');
    if (filterCountDisplay) {
        const filteredCount = filtered.length;
        filterCountDisplay.innerHTML = filteredCount === stories.length ? `Showing all ${stories.length} stories` : `Showing ${filteredCount} of ${stories.length} stories`;
    }
    
    const { column, direction } = sortState.stories;
    filtered.sort((a, b) => {
        let aVal = a[column] || '', bVal = b[column] || '';
        if (typeof aVal === 'number') return direction === 'asc' ? aVal - bVal : bVal - aVal;
        return direction === 'asc' ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
    });
    
    tbody.innerHTML = filtered.map(story => {
        let storyKey = story.key.replace('.md', '');
        const publishDate = story.medium_first_published ? story.medium_first_published.split('T')[0] : (story.published_date || '-');
        const memberReads = story.medium_member_reads || 0;
        const totalReads = story.reads || 0;
        const memberViews = story.medium_member_views || 0;
        const totalViews = story.view_count || 0;
        const memberReadPercent = calcMemberPercent(memberReads, totalReads);
        const memberViewPercent = calcMemberPercent(memberViews, totalViews);
        const lifetimeText = `${formatNumber(story.lifetime_reads || 0)}/${formatNumber(story.lifetime_views || 0)}/${formatNumber(story.presentation_count || 0)}`;
        
        let linkedinHtml = '<span class="linkedin-badge linkedin-not-posted">Not Posted</span>';
        if (story.linkedin_status === 'scheduled') linkedinHtml = `<span class="linkedin-badge linkedin-scheduled">📅 ${story.linkedin_timestamp ? formatTimestampForDisplay(story.linkedin_timestamp).substring(5,10) : ''}</span>`;
        else if (story.linkedin_status === 'posted') linkedinHtml = `<span class="linkedin-badge linkedin-posted">✅ ${story.linkedin_timestamp ? formatTimestampForDisplay(story.linkedin_timestamp).substring(5,10) : ''}</span>`;
        
        return `<tr class="table-row-clickable" onclick="editStory('${storyKey.replace(/'/g,"\\'")}')">
            <td class="text-center" onclick="event.stopPropagation()"><i class="bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}" onclick="toggleBookmark('${storyKey.replace(/'/g,"\\'")}', event)"></i></td>
            <td class="text-center" onclick="event.stopPropagation()"><i class="bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}" onclick="toggleLeaderboard('${storyKey.replace(/'/g,"\\'")}', event)"></i></td>
            <td><span class="status-badge ${story.status==='Published'?'status-published':story.status==='Ready'?'status-ready':story.status==='Done'?'status-done':'status-draft'}">${story.status}</span></td>
            <td><strong title="${escapeHtml(story.name)}">${escapeHtml(story.name.length>45?story.name.substring(0,45)+'...':story.name)}</strong></td>
            <td><small>${publishDate}</small></td>
            <td class="stats-tooltip" title="${memberReads} of ${totalReads} reads (${memberReadPercent}% from members)">${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%</td
            <td class="stats-tooltip" title="${memberViews} of ${totalViews} views (${memberViewPercent}% from members)">${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%</td
            <td>${formatNumber(story.claps || 0)}</td
            <td>${formatNumber(story.linkedin_impressions || 0)}</td
            <td><span class="lifetime-text">${lifetimeText}</span></td
            <td class="text-center">${linkedinHtml}</td
            <td><small>${story.medium_publication ? escapeHtml(story.medium_publication).substring(0,15) : '-'}</small></td
            <td class="action-buttons" onclick="event.stopPropagation()">
                <button class="btn btn-sm btn-outline-info" onclick="event.stopPropagation(); showStatsDashboard('${storyKey.replace(/'/g,"\\'")}')" title="Stats"><i class="bi bi-graph-up"></i></button>
                <button class="btn btn-sm btn-danger" onclick="deleteStory('${storyKey.replace(/'/g,"\\'")}')" title="Delete"><i class="bi bi-trash"></i></button>
            </td
         </tr`;
    }).join('');
}

async function toggleBookmark(storyKey, event) {
    event.stopPropagation();
    let cleanKey = storyKey.replace('.md', '');
    const story = window.allStories.find(s => s.key === cleanKey);
    if (!story) return;
    await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bookmarked: !story.bookmarked })
    });
    await loadView(window.currentView);
}

async function toggleLeaderboard(storyKey, event) {
    event.stopPropagation();
    let cleanKey = storyKey.replace('.md', '');
    const story = window.allStories.find(s => s.key === cleanKey);
    if (!story) return;
    await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ leaderboard: !story.leaderboard, leaderboard_nanos: story.leaderboard_nanos || 0 })
    });
    await loadView(window.currentView);
    updateLeaderboardTotal();
}

async function editStory(storyKey) {
    let cleanKey = storyKey.replace('.md', '');
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(cleanKey)}`);
    const story = await res.json();
    
    document.getElementById('editStoryKey').value = cleanKey;
    document.getElementById('editStoryNameDisplay').textContent = story.name;
    document.getElementById('editStoryPath').textContent = story.raw_path || story.rel_path;
    document.getElementById('editStorySeries').textContent = story.series || 'Standalone';
    document.getElementById('editStoryStatus').value = story.status || 'Draft';
    document.getElementById('editStoryPublication').value = story.medium_publication || '';
    document.getElementById('editStoryCreatedDate').value = story.created_date?.split('T')[0] || '';
    document.getElementById('editStoryTags').value = story.tags?.join(', ') || '';
    document.getElementById('editStoryMediumUrl').value = story.medium_url || '';
    document.getElementById('editStoryNotes').value = story.notes || '';
    document.getElementById('editStoryLeaderboard').value = story.leaderboard ? 'true' : 'false';
    document.getElementById('editStoryLeaderboardNanos').value = story.leaderboard_nanos || 0;
    document.getElementById('editStoryLeaderboardLifetimeNanos').value = story.leaderboard_lifetime_nanos || 0;
    
    document.getElementById('editStoryLifetimeReads').innerHTML = formatNumber(story.lifetime_reads || 0);
    document.getElementById('editStoryLifetimeViews').innerHTML = formatNumber(story.lifetime_views || 0);
    document.getElementById('editStoryPresentationCount').innerHTML = formatNumber(story.presentation_count || 0);
    
    const memberReads = story.medium_member_reads || 0;
    const totalReads = story.reads || 0;
    const memberViews = story.medium_member_views || 0;
    const totalViews = story.view_count || 0;
    const memberReadPercent = calcMemberPercent(memberReads, totalReads);
    const memberViewPercent = calcMemberPercent(memberViews, totalViews);
    const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
    
    document.getElementById('editStoryMemberReads').innerHTML = `${formatNumber(memberReads)}/${formatNumber(totalReads)} - ${memberReadPercent}%`;
    document.getElementById('editStoryMemberViews').innerHTML = `${formatNumber(memberViews)}/${formatNumber(totalViews)} - ${memberViewPercent}%`;
    document.getElementById('editStoryEngagement').innerHTML = `${formatNumber(story.claps || 0)}/${formatNumber(story.medium_new_followers || 0)}`;
    document.getElementById('editStoryReadRatio').innerHTML = `${readRatio}%`;
    document.getElementById('editStoryMemberPercent').innerHTML = `${memberReadPercent}%`;
    document.getElementById('editStoryReadTimeWordCount').innerHTML = `${story.medium_reading_time || story.read_time || 0} min / ${formatNumber(story.word_count || 0)} words`;
    document.getElementById('editStoryLastUpdated').textContent = story.last_updated || 'Never';
    
    document.getElementById('editStoryLinkedinStatus').value = story.linkedin_status || '';
    document.getElementById('editStoryLinkedinTimestamp').value = story.linkedin_timestamp || '';
    document.getElementById('editStoryLinkedinImpressions').value = story.linkedin_impressions || 0;
    document.getElementById('editStoryLinkedinUrl').value = story.linkedin_url || '';
    updateLinkedinDisplay();
    
    new bootstrap.Modal(document.getElementById('editStoryModal')).show();
}

async function saveStoryEdit() {
    let storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) return;
    storyKey = storyKey.replace('.md', '');
    
    const data = {
        status: document.getElementById('editStoryStatus')?.value || 'Draft',
        read_time: parseInt(document.getElementById('editStoryReadTime')?.value) || null,
        tags: document.getElementById('editStoryTags')?.value.split(',').map(t=>t.trim()).filter(t=>t) || [],
        medium_url: document.getElementById('editStoryMediumUrl')?.value || null,
        notes: document.getElementById('editStoryNotes')?.value || '',
        created_date: document.getElementById('editStoryCreatedDate')?.value || null,
        medium_publication: document.getElementById('editStoryPublication')?.value || null,
        linkedin_status: document.getElementById('editStoryLinkedinStatus')?.value || null,
        linkedin_timestamp: document.getElementById('editStoryLinkedinTimestamp')?.value || null,
        linkedin_impressions: parseInt(document.getElementById('editStoryLinkedinImpressions')?.value) || 0,
        linkedin_url: document.getElementById('editStoryLinkedinUrl')?.value || null,
        leaderboard: document.getElementById('editStoryLeaderboard')?.value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editStoryLeaderboardNanos')?.value) || 0,
        leaderboard_lifetime_nanos: parseInt(document.getElementById('editStoryLeaderboardLifetimeNanos')?.value) || 0
    };
    
    const res = await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey)}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
    if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById('editStoryModal')).hide();
        await loadView(window.currentView);
        updateLeaderboardTotal();
    } else {
        alert('Error saving story');
    }
}

async function createNewStory() {
    const name = document.getElementById('addStoryName')?.value;
    if (!name) { alert('Story name required'); return; }
    
    const data = {
        name: name,
        series: document.getElementById('addStorySeries')?.value || null,
        tags: document.getElementById('addStoryTags')?.value.split(',').map(t=>t.trim()).filter(t=>t) || [],
        read_time: parseInt(document.getElementById('addStoryReadTime')?.value) || null,
        created_date: document.getElementById('addStoryCreatedDate')?.value || getTodayDate()
    };
    
    const res = await fetch(`${API_BASE}/stories/`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data) });
    if (res.ok) {
        bootstrap.Modal.getInstance(document.getElementById('addStoryModal')).hide();
        await loadView('stories');
    } else {
        alert('Error creating story');
    }
}

async function deleteStory(storyKey) {
    if (confirm('Delete this story?')) {
        await fetch(`${API_BASE}/stories/${encodeURIComponent(storyKey.replace('.md',''))}`, { method:'DELETE' });
        await loadView(window.currentView);
    }
}

async function syncStories() {
    await fetch(`${API_BASE}/stories/sync`, { method:'POST' });
    await loadView(window.currentView);
}

async function updateLeaderboardStats() {
    if (!confirm('Fetch complete stats for stories marked as Leaderboard?')) return;
    const res = await fetch(`${API_BASE}/stories/update-leaderboard-stats`, { method: 'POST' });
    const data = await res.json();
    alert(`${data.message}\nUpdated: ${data.results?.updated || 0}\nFailed: ${data.results?.failed || 0}`);
    await loadView(window.currentView);
}