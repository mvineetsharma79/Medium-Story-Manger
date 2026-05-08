// ============================================
// STORIES.JS - Complete with Month/Year Selector & Caching
// ============================================

let allStories = [];
let allSeriesNames = [];
let currentSort = { column: 'name', direction: 'asc' };
let currentSelectedYear = null;
let currentSelectedMonth = null;
let isLoadingMonthStats = false;
let currentEditStoryKey = null;
let currentEditStoryYear = null;
let currentEditStoryMonth = null;

// Cache for monthly stats (in-memory for page lifespan)
let monthlyStatsCache = {};

// ============================================
// MONTH/YEAR SELECTOR - Load historical stats
// ============================================

async function loadMonthStats() {
    const yearSelect = document.getElementById('yearSelect');
    const monthSelect = document.getElementById('monthSelect');
    
    if (!yearSelect || !monthSelect) return;
    
    const year = parseInt(yearSelect.value);
    const month = parseInt(monthSelect.value);
    
    if (isNaN(year) || isNaN(month)) return;
    
    currentSelectedYear = year;
    currentSelectedMonth = month;
    
    isLoadingMonthStats = true;
    showLoading();
    
    try {
        const cacheKey = `${year}-${month}`;
        
        // Clear cache for this month to force fresh load
        delete monthlyStatsCache[cacheKey];
        
        console.log(`Fetching stats for ${cacheKey}`);
        const response = await fetch(`${API_BASE}/stories/monthly-stats/${year}/${month}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`✅ Received ${data.total_stories} stories, ${data.stories_with_earnings} with earnings`);
        
        // Store in cache
        monthlyStatsCache[cacheKey] = data.stats_map;
        
        // Apply stats to allStories
        applyMonthlyStats(cacheKey, data.stats_map);
        
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const displaySpan = document.getElementById('currentDisplayMonth');
        if (displaySpan) {
            displaySpan.textContent = `${monthNames[month-1]} ${year}`;
            displaySpan.style.fontWeight = 'bold';
            displaySpan.style.color = '#0d6efd';
        }
        
        // Count final leaderboard stories
        const finalLeaderboardCount = allStories.filter(s => s.leaderboard === true).length;
        showToast(`Loaded stats for ${monthNames[month-1]} ${year}: ${finalLeaderboardCount} stories on leaderboard`, 'success');
        
    } catch (error) {
        console.error('Error loading month stats:', error);
        showToast('Error loading month stats: ' + error.message, 'error');
    } finally {
        isLoadingMonthStats = false;
        hideLoading();
    }
}

function applyMonthlyStats(cacheKey, statsMap) {
    console.log(`🔄 Applying stats for ${cacheKey}`);
    console.log(`📊 Stats map has ${Object.keys(statsMap).length} entries`);
    
    // Count earnings in statsMap for debugging
    let earningsCount = 0;
    let totalEarnings = 0;
    
    const updatedStories = allStories.map(story => {
        const stats = statsMap[story.uniqueSlug];
        
        if (stats) {
            const earnings = stats.earnings || 0;
            const isPublished = story.status === 'Published';
            const shouldHaveLeaderboard = isPublished && earnings > 0;
            
            if (shouldHaveLeaderboard) {
                earningsCount++;
                totalEarnings += earnings;
            }
            
            // Debug for ASP.NET story
            if (story.uniqueSlug.includes('asp-net-core-filters')) {
                console.log(`🎯 ASP.NET Story:`, {
                    uniqueSlug: story.uniqueSlug,
                    status: story.status,
                    earnings: earnings,
                    leaderboard: shouldHaveLeaderboard
                });
            }
            
            return {
                ...story,
                reads: stats.reads || 0,
                view_count: stats.views || 0,
                views: stats.views || 0,
                claps: stats.claps || 0,
                responses: stats.responses || 0,
                medium_earnings: earnings,
                leaderboard: shouldHaveLeaderboard,
                monthly_stats: stats
            };
        }
        
        return {
            ...story,
            reads: 0,
            view_count: 0,
            views: 0,
            claps: 0,
            responses: 0,
            medium_earnings: 0,
            leaderboard: false,
            monthly_stats: null
        };
    });
    
    // Replace the entire array
    allStories = updatedStories;
    
    console.log(`💰 Updated ${earningsCount} stories with leaderboard=true, total earnings: $${(totalEarnings / 1000000000).toFixed(2)}`);
    
    // Re-render the table
    renderStoryTable();
    updateFilterCount();
    updateLeaderboardTotal();
}

async function loadCurrentMonth() {
    const now = new Date();
    const currentYear = now.getFullYear();
    const currentMonth = now.getMonth() + 1;
    
    const yearSelect = document.getElementById('yearSelect');
    const monthSelect = document.getElementById('monthSelect');
    
    if (yearSelect) yearSelect.value = currentYear;
    if (monthSelect) monthSelect.value = currentMonth;
    
    // Clear selected month to indicate we're back to current month
    currentSelectedYear = null;
    currentSelectedMonth = null;
    
    const displaySpan = document.getElementById('currentDisplayMonth');
    if (displaySpan) {
        displaySpan.textContent = 'Current Month';
        displaySpan.style.fontWeight = 'normal';
        displaySpan.style.color = '';
    }
    
    // Clear monthly stats cache for current month to force fresh load
    const currentKey = `${currentYear}-${currentMonth}`;
    delete monthlyStatsCache[currentKey];
    
    await loadStories();
}

// ============================================
// LOAD STORIES
// ============================================

async function loadStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/list`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        
        // Process stories
        const processedStories = (data.stories || []).map(story => {
            const hasEarnings = (story.medium_earnings || 0) > 0;
            return {
                ...story,
                leaderboard: hasEarnings,
                leaderboard_nanos: story.medium_earnings || 0
            };
        });
        
        allStories = processedStories;
        
        // Build series dropdown
        const seriesSet = new Set();
        allStories.forEach(story => {
            if (story.series && story.series !== 'null' && story.series !== '') {
                seriesSet.add(story.series);
            }
        });
        allSeriesNames = Array.from(seriesSet).sort();
        updateSeriesDropdown();
        
        // Render table
        renderStoryTable();
        updateFilterCount();
        
        // Load monthly stats
        await loadMonthStats();
        
        // Restore series filter if coming from series page
        restoreSeriesFilter();
        
        if (window.updateLeaderboardTotal) {
            window.updateLeaderboardTotal();
        }
        
        console.log(`Loaded ${allStories.length} stories`);
        
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
        filterCountDisplay.innerHTML = `Showing <strong>${filtered.length}</strong> of <strong>${allStories.length}</strong> stories`;    
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

// ============================================
// SORTING
// ============================================

function sortStories(column) {
    const columnMap = {
        'published_due_date': 'publishedDueDate',
        'performance': 'performance',
        'engagement': 'engagement',
        'earnings': 'earnings', 
        'read_time': 'read_time',
        'bookmarked': 'bookmarked',
        'leaderboard': 'leaderboard',
        'status': 'status',
        'name': 'name',
        'series': 'series',
        'created_date': 'created_date',
        'published_date': 'published_date',
        'claps': 'claps',
        'medium_earnings': 'medium_earnings',
        'reads': 'reads',
        'views': 'views',
        'reading_time': 'reading_time',
        'linkedin_status': 'linkedin_status'
    };
    
    const sortColumn = columnMap[column] || column;
    
    if (currentSort.column === sortColumn) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = sortColumn;
        currentSort.direction = 'asc';
    }
    
    renderStoryTable();
    updateSortIcons(column, currentSort.direction);
}

function getSortedStories() {
    const filtered = getFilteredStories();
    
    filtered.sort((a, b) => {
        let aVal, bVal;
        
        switch (currentSort.column) {
            case 'performance':
                // Sum of Presentations + Views + Reads for sorting
                const aTotalStats = a.medium?.totalStats || {};
                const bTotalStats = b.medium?.totalStats || {};
                const aPresentations = aTotalStats.presentations || 0;
                const aViews = aTotalStats.views || 0;
                const aReads = aTotalStats.reads || 0;
                const bPresentations = bTotalStats.presentations || 0;
                const bViews = bTotalStats.views || 0;
                const bReads = bTotalStats.reads || 0;
                aVal = aPresentations + aViews + aReads;
                bVal = bPresentations + bViews + bReads;
                break;
                
            case 'engagement':
                aVal = (a.claps || a.medium?.clapCount || 0) + (a.responses || a.medium?.responsesCount || 0);
                bVal = (b.claps || b.medium?.clapCount || 0) + (b.responses || b.medium?.responsesCount || 0);
                break;
                
            case 'earnings':
                const year = currentSelectedYear || new Date().getFullYear();
                const month = String(currentSelectedMonth || new Date().getMonth() + 1).padStart(2, '0');
                //const monthlyEarnings = story.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || 0;

                const aTotalEarning = a.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || {};
                const bTotalEarning = b.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || {};

                aVal = aTotalEarning || 0;
                bVal = bTotalEarning || 0;
                break;
                
            case 'published_due_date':
                aVal = a.publishedDueDate || a.published_due_date || '';
                bVal = b.publishedDueDate || b.published_due_date || '';
                break;
                
            case 'read_time':
                aVal = a.medium?.readingTime || a.medium_reading_time || a.read_time || 0;
                bVal = b.medium?.readingTime || b.medium_reading_time || b.read_time || 0;
                break;
                
            case 'bookmarked':
                aVal = a.bookmarked ? 1 : 0;
                bVal = b.bookmarked ? 1 : 0;
                break;
                
            case 'leaderboard':
                aVal = a.leaderboard ? 1 : 0;
                bVal = b.leaderboard ? 1 : 0;
                break;
                
            case 'status':
                const statusOrder = { 'Published': 1, 'Published Due': 2, 'Ready': 3, 'Draft': 4, 'Done': 5 };
                aVal = statusOrder[a.status] || 99;
                bVal = statusOrder[b.status] || 99;
                break;
                
            case 'name':
                aVal = (a.title || a.name || '').toLowerCase();
                bVal = (b.title || b.name || '').toLowerCase();
                break;
                
            case 'series':
                aVal = (a.series || '').toLowerCase();
                bVal = (b.series || '').toLowerCase();
                break;
                
            case 'created_date':
                aVal = a.created_date || a.createdDate || '';
                bVal = b.created_date || b.createdDate || '';
                break;
                
            case 'published_date':
                aVal = a.published_date || a.publishedDate || '';
                bVal = b.published_date || b.publishedDate || '';
                break;
                
            case 'linkedin_status':
                const linkedinOrder = { 'posted': 1, 'scheduled': 2, '': 3, null: 3 };
                aVal = linkedinOrder[a.linkedin_status] || 3;
                bVal = linkedinOrder[b.linkedin_status] || 3;
                break;
                
            default:
                aVal = a[currentSort.column] || '';
                bVal = b[currentSort.column] || '';
        }
        
        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        
        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();
        return currentSort.direction === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });
    
    return filtered;
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
    // Reset switches
    const bookmarkFilter = document.getElementById('bookmarkFilter');
    const leaderboardFilter = document.getElementById('leaderboardFilter');
    const statusFilter = document.getElementById('statusFilter');
    const seriesFilter = document.getElementById('seriesFilter');
    const searchFilter = document.getElementById('searchFilter');
    
    if (bookmarkFilter) bookmarkFilter.checked = false;
    if (leaderboardFilter) leaderboardFilter.checked = false;
    if (statusFilter) statusFilter.value = 'All';
    if (seriesFilter) seriesFilter.value = '';
    if (searchFilter) searchFilter.value = '';
    
    applyFilters();
    updateEarningsSummary();
}

function filterBySeries(seriesName) {
    if (!seriesName) return;
    
    // Set the series filter dropdown
    const seriesFilter = document.getElementById('seriesFilter');
    if (seriesFilter) {
        seriesFilter.value = seriesName;
    }
    
    // Apply filters
    applyFilters();
}

// ============================================
// RENDER TABLE
// ============================================

function renderStoryTable() {
    const tbody = document.getElementById('storiesTableBody');
    if (!tbody) return;
    
    const sortedStories = getSortedStories();
    tbody.innerHTML = '';
    
    if (sortedStories.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 15;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No stories found';
        return;
    }
    
    sortedStories.forEach((story, index) => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        
        const medium = story.medium || {};
        const totalStats = medium.totalStats || {};
        
        const serialCell = row.insertCell(0);
        serialCell.className = 'text-center';
        serialCell.textContent = index + 1;
        serialCell.style.fontSize = '1.2rem';
        serialCell.style.fontWeight = 'bold';
        serialCell.style.color = '#6c757d';
        serialCell.style.backgroundColor = '#f8f9fa';

        // Column 0: Bookmark ⭐
        const bookmarkCell = row.insertCell(1);
        bookmarkCell.className = 'text-center';
        const bookmarkIcon = document.createElement('i');
        bookmarkIcon.className = `bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}`;
        bookmarkIcon.style.cursor = 'pointer';
        bookmarkIcon.onclick = (e) => { e.stopPropagation(); toggleBookmark(story.uniqueSlug, e); };
        bookmarkCell.appendChild(bookmarkIcon);
        
        // Column 1: Leaderboard 🏆
        const leaderboardCell = row.insertCell(2);
        leaderboardCell.className = 'text-center';
        const leaderboardIcon = document.createElement('i');
        leaderboardIcon.className = `bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}`;
        leaderboardIcon.style.cursor = 'pointer';
        leaderboardIcon.onclick = (e) => { e.stopPropagation(); toggleLeaderboard(story.uniqueSlug, e); };
        leaderboardCell.appendChild(leaderboardIcon);
        
        // Column 2: Status 📋
        const statusCell = row.insertCell(3);
        const statusSpan = document.createElement('span');
        let statusClass = 'status-draft';
        switch(story.status) {
            case 'Published':
                statusClass = 'status-published';
                break;
            case 'Published Due':
                statusClass = 'status-published-due';
                break;
            case 'Ready':
                statusClass = 'status-ready';
                break;
            case 'Done':
                statusClass = 'status-done';
                break;
            default:
                statusClass = 'status-draft';
        }
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = story.status || 'Draft';
        statusCell.appendChild(statusSpan);
        
        // Column 3: Title 📄 with Preview Icon
        const titleCell = row.insertCell(4);
        const titleWrapper = document.createElement('div');
        titleWrapper.style.display = 'flex';
        titleWrapper.style.alignItems = 'center';
        titleWrapper.style.gap = '8px';

        // Preview Icon
        const previewIcon = document.createElement('span');
        previewIcon.textContent = '🔗';
        previewIcon.style.cursor = 'pointer';
        previewIcon.style.fontSize = '1.2rem';
        previewIcon.title = 'Preview Story';
        previewIcon.onclick = (e) => {
            e.stopPropagation();
            const previewUrl = `/story-preview/${encodeURIComponent(story.key)}`;
            window.open(previewUrl, '_blank', 'width=1200,height=800');
        };
        titleWrapper.appendChild(previewIcon);

        // Title text - Click to open edit modal
        const titleStrong = document.createElement('strong');
        titleStrong.style.cursor = 'pointer';
        titleStrong.textContent = story.title || story.name || 'Unknown';
        
        const encodedStoryKey = encodeURIComponent(story.name);
        titleStrong.onclick = function(e) {
            e.stopPropagation();
            openEditStory(encodedStoryKey);
        };

        titleWrapper.appendChild(titleStrong);
        titleCell.appendChild(titleWrapper);
        
        // Column 4: Series 📁 - Clickable to filter by series
        const seriesCell = row.insertCell(5);
        if (story.series) {
            const seriesLink = document.createElement('a');
            seriesLink.href = '#';
            seriesLink.textContent = story.series;
            seriesLink.style.textDecoration = 'none';
            seriesLink.style.cursor = 'pointer';
            seriesLink.style.color = '#0d6efd';
            seriesLink.style.fontWeight = '500';
            seriesLink.onclick = (e) => {
                e.stopPropagation();
                filterBySeries(story.series);
            };
            seriesCell.appendChild(seriesLink);
        } else {
            seriesCell.textContent = '—';
            seriesCell.className = 'text-muted';
        }
        
        // Column 5: Created Date 🆕
        const createdCell = row.insertCell(6);
        createdCell.textContent = story.created_date || story.createdDate ? (story.created_date || story.createdDate).split('T')[0] : '-';
        
        // Column 6: Published Date 📅
        const publishedCell = row.insertCell(7);
        publishedCell.textContent = story.published_date || story.publishedDate ? (story.published_date || story.publishedDate).split('T')[0] : '-';
        
        // Column 7: Due Date ⏰
        const dueCell = row.insertCell(8);
        const dueDate = story.publishedDueDate || story.published_due_date;
        if (dueDate) {
            dueCell.textContent = dueDate.split('T')[0];
            dueCell.className = 'text-warning fw-bold';
        } else {
            dueCell.textContent = '—';
            dueCell.className = 'text-muted';
        }
        
        // Column 8: Performance 📊
        const performanceCell = row.insertCell(9);
        const performanceDiv = document.createElement('div');
        performanceDiv.style.fontSize = '0.7rem';
        performanceDiv.style.whiteSpace = 'nowrap';
        const presentations = totalStats.presentations || 0;
        const views = totalStats.views || 0;
        const reads = totalStats.reads || 0;
        performanceDiv.innerHTML = `📊 ${formatNumber(presentations)}<br>👁️ ${formatNumber(views)}<br>📖 ${formatNumber(reads)}`;
        performanceCell.appendChild(performanceDiv);
        
        // Column 9: Engagement 💚
        const engagementCell = row.insertCell(10);
        const engagementDiv = document.createElement('div');
        engagementDiv.style.fontSize = '0.7rem';
        engagementDiv.style.whiteSpace = 'nowrap';
        const claps = story.claps || medium.clapCount || 0;
        const responses = story.responses || medium.responsesCount || 0;
        engagementDiv.innerHTML = `💚 ${formatNumber(claps)}<br>💬 ${formatNumber(responses)}`;
        engagementCell.appendChild(engagementDiv);
        
        // Column 10: Earnings 💰
        const earningsCell = row.insertCell(11);
        const earningsDiv = document.createElement('div');
        earningsDiv.style.fontSize = '0.7rem';
        // const monthlyEarnings = story.medium?.monthlyEarnings[0].amount || 0 //story.medium_earnings || 0;

        const year = currentSelectedYear || new Date().getFullYear();
        const month = String(currentSelectedMonth || new Date().getMonth() + 1).padStart(2, '0');
        const monthlyEarnings = story.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || 0;
        
        const totalEarnings = story.medium?.totalEarnings?.amount || story.lifetime_earnings || 0;
        earningsDiv.innerHTML = `🏦${monthlyEarnings} / ${totalEarnings}`;
        earningsCell.appendChild(earningsDiv);

        // Column 11: Read Time ⏱️
        const readTimeCell = row.insertCell(12);
        const readTimeDiv = document.createElement('div');
        readTimeDiv.style.fontSize = '0.7rem';
        let readingTime = medium.readingTime || story.medium_reading_time || story.read_time || 0;
        
        readTimeDiv.innerHTML = `⏱️ ${minutesToHoursMinutes(readingTime)}`;
        readTimeCell.appendChild(readTimeDiv);

        // Column 12: LinkedIn 🔗
        const linkedinCell = row.insertCell(13);
        const linkedinSpan = document.createElement('span');
        const linkedinStatus = story.linkedin?.status || story.linkedin_status;
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
        
        // Column 13: Actions ⚙️
        const actionsCell = row.insertCell(14);
        actionsCell.className = 'action-buttons';
        
        const statsBtn = document.createElement('button');
        statsBtn.className = 'btn btn-sm btn-outline-info';
        statsBtn.title = 'Stats Dashboard';
        statsBtn.onclick = (e) => { e.stopPropagation(); showStatsDashboard(story.uniqueSlug); };
        statsBtn.innerHTML = '<i class="bi bi-graph-up"></i>';
        actionsCell.appendChild(statsBtn);
        
        const externalBtn = document.createElement('button');
        externalBtn.className = 'btn btn-sm btn-outline-secondary ms-1';
        externalBtn.title = 'Open on Medium';
        const mediumUrl = 'https://medium.com/me/stats/post/' + medium.id;
        if (mediumUrl && medium.id) {
            externalBtn.onclick = (e) => { e.stopPropagation(); window.open(mediumUrl, '_blank'); };
        } else {
            externalBtn.disabled = true;
        }
        externalBtn.innerHTML = '<i class="bi bi-box-arrow-up-right"></i>';
        actionsCell.appendChild(externalBtn);
    });
    
    updateLeaderboardTotal();
}

// ============================================
// TOGGLE BOOKMARK & LEADERBOARD
// ============================================

async function toggleBookmark(uniqueSlug, event) {
    if (event) event.stopPropagation();
    
    const story = allStories.find(s => s.uniqueSlug === uniqueSlug);
    
    if (!story) {
        console.error('Story not found for uniqueSlug:', uniqueSlug);
        showToast('Story not found', 'error');
        return;
    }
    
    const newState = !story.bookmarked;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookmarked: newState })
        });
        
        if (response.ok) {
            story.bookmarked = newState;
            renderStoryTable();
            showToast(newState ? 'Story bookmarked' : 'Bookmark removed', 'success');
        } else {
            const error = await response.json();
            showToast('Error updating bookmark: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling bookmark:', error);
        showToast('Error updating bookmark: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function toggleLeaderboard(uniqueSlug, event) {
    if (event) event.stopPropagation();
    
    const story = allStories.find(s => s.uniqueSlug === uniqueSlug);
    
    if (!story) {
        console.error('Story not found for uniqueSlug:', uniqueSlug);
        showToast('Story not found', 'error');
        return;
    }
    
    const newState = !story.leaderboard;
    
    // If we're in month selector mode, just update client-side (no API call)
    if (currentSelectedYear && currentSelectedMonth) {
        story.leaderboard = newState;
        if (newState && !story.leaderboard_nanos) {
            story.leaderboard_nanos = story.medium_earnings || 10000000;
        }
        renderStoryTable();
        updateLeaderboardTotal();
        showToast(newState ? 'Added to leaderboard (client-side)' : 'Removed from leaderboard (client-side)', 'success');
        return;
    }
    
    // In dashboard mode, persist to API
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ leaderboard: newState })
        });
        
        if (response.ok) {
            story.leaderboard = newState;
            if (newState && !story.leaderboard_nanos) {
                story.leaderboard_nanos = story.medium_earnings || 10000000;
            }
            renderStoryTable();
            updateLeaderboardTotal();
            showToast(newState ? 'Added to leaderboard' : 'Removed from leaderboard', 'success');
        } else {
            const error = await response.json();
            showToast('Error updating leaderboard: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
        showToast('Error updating leaderboard: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// EDIT STORY - Using modal
// ============================================

function openEditStory(encodedStoryKey) {
    if (window.EditStoryModal && window.EditStoryModal.open) {
        window.EditStoryModal.open(encodedStoryKey);
    } else {
        console.error('EditStoryModal not available');
        showToast('Edit functionality not available. Please refresh.', 'error');
    }
}

async function showStatsDashboard(uniqueSlug) {
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    
    contentDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Loading stats...</p></div>';
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`);
        const storyData = await response.json();
        
        const medium = storyData.medium || {};
        const totalStats = medium.totalStats || {};
        const totalEarnings = medium.totalEarnings || {};
        
        contentDiv.innerHTML = `
            <div class="compact-stats">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <strong>${escapeHtml(storyData.title || storyData.name)}</strong>
                    <a href="${escapeHtml(medium.mediumUrl || storyData.medium_url || '#')}" target="_blank" class="btn btn-sm btn-outline-primary">
                        <i class="bi bi-box-arrow-up-right"></i> View on Medium
                    </a>
                </div>
                <div class="row g-2 mb-3">
                    <div class="col-12"><strong>📊 Lifetime Stats</strong></div>
                    <div class="col-4"><div class="card bg-info text-white p-2 text-center"><small>Reads</small><h5>${formatNumber(totalStats.reads || 0)}</h5></div></div>
                    <div class="col-4"><div class="card bg-primary text-white p-2 text-center"><small>Views</small><h5>${formatNumber(totalStats.views || 0)}</h5></div></div>
                    <div class="col-4"><div class="card bg-success text-white p-2 text-center"><small>Claps</small><h5>${formatNumber(medium.clapCount || 0)}</h5></div></div>
                </div>
                <div class="row g-2">
                    <div class="col-12"><strong>💰 Earnings</strong></div>
                    <div class="col-6"><div class="card bg-warning p-2 text-center"><small>Total Earnings</small><h5>${formatCurrency(totalEarnings.nanos || 0)}</h5></div></div>
                    <div class="col-6"><div class="card bg-secondary text-white p-2 text-center"><small>Responses</small><h5>${formatNumber(medium.responsesCount || 0)}</h5></div></div>
                </div>
            </div>
        `;
    } catch (error) {
        contentDiv.innerHTML = `<div class="alert alert-danger">Error loading stats: ${error.message}</div>`;
    }
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

async function updateCurrentStories() {
    
    const sortedStories = getSortedStories().filter(story => story.status === 'Published');
    const year = currentSelectedYear || new Date().getFullYear();
    const month = String(currentSelectedMonth || new Date().getMonth() + 1).padStart(2, '0');
    //const monthlyEarnings = story.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || 0;

    if (!confirm('Update current stories with latest data from Medium? This will update performance, engagement, earnings, and other stats for existing stories.')) return;
    var postId = '';
    var btn = document.querySelector('[data-action="sync-current-stats"]');
    var originalText = btn ? btn.innerHTML : 'Syncing...';
    var storyCount = sortedStories.length || 0;
    var currentStoryIndex = 1;
    // showLoading();
    try {
        for (const story of sortedStories) {
            if (!story.medium || !story.medium.id) continue;
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sync (' + currentStoryIndex + ' of ' + storyCount + ')';
            }
            var response = await fetch(API_BASE + '/stories/refresh-story/' + story.medium.id + '/' + year + '-' + month  
                , {
                    method: 'POST'
                });

            if (!response.ok)
                console.log('Failed to sync stats for story:', story.title, 'Response:', response);
                //throw new Error('Failed to sync stats');
            // else {
            //     //currentStoryIndex++;
            //     // btn.disabled = false;
            //     // btn.innerHTML = '<i class="bi bi-trophy"></i> SYNC';
            //     //loadStoryForEdit(encodeURIComponent(currentStoryKey))
            // }
            currentStoryIndex++;


            //Rate limit protection - 1 request per second
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-trophy"></i> SYNC';

    } catch (error) {
        showToast('Error updating stories: ' + error.message, 'error');
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
// DELETE STORY
// ============================================

async function deleteStory(uniqueSlug) {
    if (!confirm('Delete this story?')) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`, { method: 'DELETE' });
        if (response.ok) {
            await loadStories();
            showToast('Story deleted', 'success');
        } else {
            showToast('Error deleting story', 'error');
        }
    } catch (error) {
        showToast('Error deleting story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function minutesToHoursMinutes(minutes) {
    if (!minutes && minutes !== 0) return '00:00';
    
    // Round UP to nearest second (ceil)
    var totalSeconds = Math.ceil(minutes * 60);
    var mins = Math.floor(totalSeconds / 60);
    var secs = totalSeconds % 60;
    
    return mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
}

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

function getTodayDate() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function getCurrentYearMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

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

function updateLeaderboardTotal() {
    if (!allStories || !Array.isArray(allStories)) {
        const countEl = document.getElementById('leaderboardCount');
        const amountEl = document.getElementById('leaderboardAmount');
        if (countEl) countEl.textContent = '0';
        if (amountEl) amountEl.textContent = '0.00';
        return;
    }
    
    const storiesWithLeaderboard = allStories.filter(s => s.leaderboard === true);
    const totalEarnings = storiesWithLeaderboard.reduce((sum, s) => sum + (s.medium_earnings || 0), 0);
    
    const countEl = document.getElementById('leaderboardCount');
    const amountEl = document.getElementById('leaderboardAmount');
    if (countEl) countEl.textContent = storiesWithLeaderboard.length;
    if (amountEl) amountEl.textContent = (totalEarnings / 1000000000).toFixed(2);
}

function debugStatsMapping() {
    console.log('=== DEBUG STATS MAPPING ===');
    console.log('Available cached months:', Object.keys(monthlyStatsCache));
    
    if (currentSelectedYear && currentSelectedMonth) {
        const cacheKey = `${currentSelectedYear}-${currentSelectedMonth}`;
        const statsMap = monthlyStatsCache[cacheKey];
        if (statsMap) {
            console.log(`Stats keys for ${cacheKey}:`, Object.keys(statsMap).slice(0, 10));
            const sampleStory = allStories[0];
            if (sampleStory) {
                console.log(`Sample story uniqueSlug: "${sampleStory.uniqueSlug}"`);
                console.log(`Stats found:`, statsMap[sampleStory.uniqueSlug] || 'NOT FOUND');
            }
        }
    }
    console.log('========================');
}

function restoreSeriesFilter() {
    const seriesFilter = sessionStorage.getItem('storiesFilterSeries');
    if (seriesFilter) {
        setTimeout(() => {
            const seriesSelect = document.getElementById('seriesFilter');
            if (seriesSelect) {
                seriesSelect.value = seriesFilter;
                applyFilters();
            }
            sessionStorage.removeItem('storiesFilterSeries');
        }, 500);
    }
}

function updateEarningsSummary() {
    const filtered = getFilteredStories();
    
    let totalMonthlyEarnings = 0;
    let totalAllEarnings = 0;
    
    const year = currentSelectedYear || new Date().getFullYear();
    const month = String(currentSelectedMonth || new Date().getMonth() + 1).padStart(2, '0');
    //const monthlyEarnings = story.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || 0;

    filtered.forEach(story => {
        //totalMonthlyEarnings += story.medium_earnings || 0;
        totalMonthlyEarnings += story.medium?.monthlyEarnings?.find(entry => entry.period === `${year}-${month}`)?.amount || 0;
        const totalEarnings = story.medium?.totalEarnings?.amount || story.lifetime_earnings || 0;
        totalAllEarnings += totalEarnings;
    });
    
    const monthlyEl = document.getElementById('totalMonthlyEarnings');
    const totalEl = document.getElementById('totalEarningsAll');
    
    // if (monthlyEl) {
    //     monthlyEl.textContent = (totalMonthlyEarnings);
    // }
    // if (totalEl) {
    //     totalEl.textContent = (totalAllEarnings);
    // }

    if (monthlyEl) {
        monthlyEl.textContent = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(totalMonthlyEarnings);
    }
    if (totalEl) {
        totalEl.textContent = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(totalAllEarnings);
    }
}

// Override applyFilters to update earnings summary
const originalApplyFilters = applyFilters;
applyFilters = function() {
    originalApplyFilters();
    updateEarningsSummary();
};

// Override renderStoryTable to update earnings summary
const originalRenderStoryTable = renderStoryTable;
renderStoryTable = function() {
    originalRenderStoryTable();
    updateEarningsSummary();
};

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('yearSelect');
    if (yearSelect) {
        const currentYear = new Date().getFullYear();
        for (let y = currentYear; y >= 2024; y--) {
            const option = document.createElement('option');
            option.value = y;
            option.textContent = y;
            if (y === currentYear) option.selected = true;
            yearSelect.appendChild(option);
        }
    }
    
    const monthSelect = document.getElementById('monthSelect');
    if (monthSelect) {
        const currentMonth = new Date().getMonth() + 1;
        monthSelect.value = currentMonth;
    }
    
    loadStories();
    
    document.getElementById('statusFilter')?.addEventListener('change', applyFilters);
    document.getElementById('seriesFilter')?.addEventListener('change', applyFilters);
    document.getElementById('searchFilter')?.addEventListener('keyup', applyFilters);
    document.getElementById('bookmarkFilter')?.addEventListener('change', applyFilters);
    document.getElementById('leaderboardFilter')?.addEventListener('change', applyFilters);
    
    document.getElementById('addStoryCreateBtn')?.addEventListener('click', createStory);
});

// Make functions globally available
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
window.deleteStory = deleteStory;
window.loadMonthStats = loadMonthStats;
window.loadCurrentMonth = loadCurrentMonth;
window.loadStories = loadStories;