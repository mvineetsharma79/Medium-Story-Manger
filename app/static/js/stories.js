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

// ============================================
// SORTING
// ============================================

function sortStories(column) {
    const columnMap = {
        'engagement': 'engagement',
        'earnings': 'earnings', 
        'impression': 'impression',
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
        'medium_publication': 'medium_publication',
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
            case 'engagement':
                aVal = a.claps || a.medium?.clapCount || 0;
                bVal = b.claps || b.medium?.clapCount || 0;
                break;
                
            case 'earnings':
                aVal = a.medium_earnings || a.medium?.monthlyEarnings?.[0]?.nanos || 0;
                bVal = b.medium_earnings || b.medium?.monthlyEarnings?.[0]?.nanos || 0;
                break;
                
            case 'impression':
                aVal = a.views || a.view_count || a.medium?.totalStats?.views || a.lifetime_views || 0;
                bVal = b.views || b.view_count || b.medium?.totalStats?.views || b.lifetime_views || 0;
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
                const statusOrder = { 'Published': 1, 'Ready': 2, 'Draft': 3, 'Done': 4 };
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
                
            case 'claps':
                aVal = a.claps || a.medium?.clapCount || 0;
                bVal = b.claps || b.medium?.clapCount || 0;
                break;
                
            case 'medium_earnings':
                aVal = a.medium_earnings || a.medium?.monthlyEarnings?.[0]?.nanos || 0;
                bVal = b.medium_earnings || b.medium?.monthlyEarnings?.[0]?.nanos || 0;
                break;
                
            case 'reads':
                aVal = a.reads || a.medium?.totalStats?.reads || a.lifetime_reads || 0;
                bVal = b.reads || b.medium?.totalStats?.reads || b.lifetime_reads || 0;
                break;
                
            case 'views':
                aVal = a.views || a.view_count || a.medium?.totalStats?.views || a.lifetime_views || 0;
                bVal = b.views || b.view_count || b.medium?.totalStats?.views || b.lifetime_views || 0;
                break;
                
            case 'reading_time':
                aVal = a.medium?.readingTime || a.medium_reading_time || a.read_time || 0;
                bVal = b.medium?.readingTime || b.medium_reading_time || b.read_time || 0;
                break;
                
            case 'medium_publication':
                aVal = (a.medium?.collection?.name || a.medium_publication || '').toLowerCase();
                bVal = (b.medium?.collection?.name || b.medium_publication || '').toLowerCase();
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
        cell.colSpan = 13;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No stories found';
        return;
    }
    
    sortedStories.forEach(story => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        
        const uniqueSlug = story.uniqueSlug;
        const encodedSlug = encodeURIComponent(uniqueSlug);
        
        const medium = story.medium || {};
        
        // Column 0: Bookmark
        const bookmarkCell = row.insertCell(0);
        bookmarkCell.className = 'text-center';
        const bookmarkIcon = document.createElement('i');
        bookmarkIcon.className = `bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}`;
        bookmarkIcon.style.cursor = 'pointer';
        bookmarkIcon.onclick = (e) => { e.stopPropagation(); toggleBookmark(encodedSlug, e); };
        bookmarkCell.appendChild(bookmarkIcon);
        
        // Column 1: Leaderboard (based on earnings > 0 for selected month)
        const leaderboardCell = row.insertCell(1);
        leaderboardCell.className = 'text-center';
        const leaderboardIcon = document.createElement('i');
        // leaderboard is already set in applyMonthlyStats based on earnings > 0
        leaderboardIcon.className = `bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}`;
        leaderboardIcon.style.cursor = 'pointer';
        leaderboardIcon.onclick = (e) => { e.stopPropagation(); toggleLeaderboard(encodedSlug, e); };
        leaderboardCell.appendChild(leaderboardIcon);
        
        // Column 2: Status
        const statusCell = row.insertCell(2);
        const statusSpan = document.createElement('span');
        const statusClass = story.status === 'Published' ? 'status-published' : 
                           story.status === 'Ready' ? 'status-ready' : 
                           story.status === 'Done' ? 'status-done' : 'status-draft';
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = story.status || 'Draft';
        statusCell.appendChild(statusSpan);
        
        // Column 3: Title
        const titleCell = row.insertCell(3);
        const titleStrong = document.createElement('strong');
        titleStrong.style.cursor = 'pointer';
        titleStrong.textContent = story.title || story.name || 'Unknown';
        titleStrong.onclick = () => openEditStory(encodedSlug);
        titleCell.appendChild(titleStrong);
        
        // Column 4: Series
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
        
        // Column 5: Created Date
        const createdCell = row.insertCell(5);
        createdCell.textContent = story.created_date || story.createdDate ? (story.created_date || story.createdDate).split('T')[0] : '-';
        
        // Column 6: Published Date
        const publishedCell = row.insertCell(6);
        publishedCell.textContent = story.published_date || story.publishedDate ? (story.published_date || story.publishedDate).split('T')[0] : '-';
        
        // Column 7: Engagement (Claps / Voters / Followers)
        const engagementCell = row.insertCell(7);
        const engagementSmall = document.createElement('small');
        const claps = story.claps || medium.clapCount || 0;
        const voters = medium.voterCount || 0;
        const followers = story.medium_new_followers || 0;
        engagementSmall.innerHTML = `💚 ${formatNumber(claps)}<br>👥 ${formatNumber(voters)}<br>📢 ${formatNumber(followers)}`;
        engagementCell.appendChild(engagementSmall);
        
        // Column 8: Earnings (Monthly Earnings for selected month)
        const earningsCell = row.insertCell(8);
        const earningsSmall = document.createElement('small');
        const monthlyEarnings = story.medium_earnings || 0;
        const totalEarnings = medium.totalEarnings?.nanos || 0;
        earningsSmall.innerHTML = `💰 ${formatCurrency(monthlyEarnings)}<br>🏦 ${formatCurrency(totalEarnings)}`;
        earningsCell.appendChild(earningsSmall);
        
        // Column 9: Impression (Reads / Views / Responses)
        const impressionCell = row.insertCell(9);
        const impressionSmall = document.createElement('small');
        const reads = story.reads || 0;
        const views = story.views || story.view_count || 0;
        const responses = story.responses || 0;
        // const impression = story.medium || story.medium.totalStats || story.medium.totalStats.impression || 0;
        impressionSmall.innerHTML = `📖 ${formatNumber(reads)}<br>👁️ ${formatNumber(views)}<br>💬 ${formatNumber(responses)}`;
        impressionCell.appendChild(impressionSmall);
        
        // Column 10: Read Time / Word Count
        const readTimeCell = row.insertCell(10);
        const readTimeSmall = document.createElement('small');
        const readingTime = medium.readingTime || story.medium_reading_time || story.read_time || 0;
        const wordCount = medium.wordCount || story.word_count || 0;
        const hours = Math.floor(readingTime / 60);
        const minutes = readingTime % 60;
        const timeStr = hours > 0 ? `${hours}:${minutes.toString().padStart(2, '0')}` : `${minutes}:00`;
        readTimeSmall.innerHTML = `⏱️ ${timeStr}<br>📝 ${formatNumber(wordCount)}`;
        readTimeCell.appendChild(readTimeSmall);
        
        // Column 11: LinkedIn Status
        const linkedinCell = row.insertCell(11);
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
        
        // Column 12: Actions
        const actionsCell = row.insertCell(12);
        actionsCell.className = 'action-buttons';
        
        const statsBtn = document.createElement('button');
        statsBtn.className = 'btn btn-sm btn-outline-info';
        statsBtn.title = 'Stats Dashboard';
        statsBtn.onclick = (e) => { e.stopPropagation(); showStatsDashboard(encodedSlug); };
        statsBtn.innerHTML = '<i class="bi bi-graph-up"></i>';
        actionsCell.appendChild(statsBtn);
        
        const externalBtn = document.createElement('button');
        externalBtn.className = 'btn btn-sm btn-outline-secondary ms-1';
        externalBtn.title = 'Open on Medium';
        // const mediumUrl = medium.mediumUrl || story.medium_url; //6a63927f9b83
        const mediumUrl = 'https://medium.com/me/stats/post/' + medium.id || story.medium_id; //6a63927f9b83
        if (mediumUrl) {
            externalBtn.onclick = (e) => { e.stopPropagation(); window.open(mediumUrl, '_blank'); };
        } else {
            externalBtn.disabled = true;
        }
        externalBtn.innerHTML = '<i class="bi bi-box-arrow-up-right"></i>';
        actionsCell.appendChild(externalBtn);
    });
    
    // Update leaderboard total in sidebar
    updateLeaderboardTotal();
}

// ============================================
// TOGGLE BOOKMARK & LEADERBOARD
// ============================================

async function toggleBookmark(encodedUniqueSlug, event) {
    if (event) event.stopPropagation();
    
    const uniqueSlug = decodeURIComponent(encodedUniqueSlug);
    const story = allStories.find(s => s.uniqueSlug === uniqueSlug);
    
    if (!story) {
        console.error('Story not found for uniqueSlug:', uniqueSlug);
        showToast('Story not found', 'error');
        return;
    }
    
    const newState = !story.bookmarked;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedUniqueSlug}`, {
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

async function toggleLeaderboard(encodedUniqueSlug, event) {
    if (event) event.stopPropagation();
    
    const uniqueSlug = decodeURIComponent(encodedUniqueSlug);
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
        // If setting leaderboard true, set a default nanos value
        if (newState && !story.leaderboard_nanos) {
            story.leaderboard_nanos = story.medium_earnings || 10000000; // Default $0.01 if no earnings
        }
        renderStoryTable();
        updateLeaderboardTotal();
        showToast(newState ? 'Added to leaderboard (client-side)' : 'Removed from leaderboard (client-side)', 'success');
        return;
    }
    
    // In dashboard mode, persist to API
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedUniqueSlug}`, {
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
// MODAL FUNCTIONS
// ============================================

async function openEditStory(encodedUniqueSlug) {
    const uniqueSlug = decodeURIComponent(encodedUniqueSlug);
    const story = allStories.find(s => s.uniqueSlug === uniqueSlug);
    
    if (!story) {
        showToast('Story not found', 'error');
        return;
    }
    
    currentEditStoryKey = story.uniqueSlug;
    
    const now = new Date();
    currentEditStoryYear = now.getFullYear();
    currentEditStoryMonth = now.getMonth() + 1;
    
    try { 
        const modeData = await fetch(`${API_BASE}/stories/mode`).then(r => r.json()); 
        if (modeData.current_month) { 
            currentEditStoryYear = modeData.current_month.year; 
            currentEditStoryMonth = modeData.current_month.month; 
        } 
    } catch(e) {}
    
    await loadStoryForEdit(story.uniqueSlug, currentEditStoryYear, currentEditStoryMonth);
    const modalEl = document.getElementById('editStoryModal');
    if (modalEl) new bootstrap.Modal(modalEl).show();
}

async function loadStoryForEdit(uniqueSlug, year, month) {
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(uniqueSlug)}`);
        const story = await response.json();
        
        document.getElementById('editStoryUniqueSlug').value = story.uniqueSlug;
        document.getElementById('editStoryTitle').value = story.title || '';
        document.getElementById('editStoryStatus').value = story.status || 'Draft';
        document.getElementById('editStorySeries').value = story.series || '';
        document.getElementById('editStoryCreatedDate').value = story.created_date?.split('T')[0] || '';
        document.getElementById('editStoryPublishedDate').value = story.published_date?.split('T')[0] || '';
        document.getElementById('editStoryNotes').value = story.notes || '';
        document.getElementById('editStoryTags').value = (story.tags || []).join(', ');
        document.getElementById('editStoryMediumUrl').value = story.medium_url || '';
        
        const linkedin = story.linkedin || {};
        document.getElementById('editStoryLinkedinStatus').value = linkedin.status || story.linkedin_status || '';
        document.getElementById('editStoryLinkedinTimestamp').value = linkedin.timestamp || story.linkedin_timestamp || '';
        document.getElementById('editStoryLinkedinImpressions').value = linkedin.impressions || story.linkedin_impressions || 0;
        document.getElementById('editStoryLinkedinUrl').value = linkedin.url || story.linkedin_url || '';
        
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

async function showStatsDashboard(encodedUniqueSlug) {
    const uniqueSlug = decodeURIComponent(encodedUniqueSlug);
    const modalEl = document.getElementById('statsDashboardModal');
    const contentDiv = document.getElementById('statsDashboardContent');
    if (!modalEl || !contentDiv) return;
    
    contentDiv.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-primary"></div><p>Loading stats...</p></div>';
    const modal = new bootstrap.Modal(modalEl);
    modal.show();
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedUniqueSlug}`);
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

async function deleteStory(encodedUniqueSlug) {
    if (!confirm('Delete this story?')) return;
    
    const uniqueSlug = decodeURIComponent(encodedUniqueSlug);
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodedUniqueSlug}`, { method: 'DELETE' });
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
            
            // Check a sample story
            const sampleStory = allStories[0];
            if (sampleStory) {
                console.log(`Sample story uniqueSlug: "${sampleStory.uniqueSlug}"`);
                console.log(`Stats found:`, statsMap[sampleStory.uniqueSlug] || 'NOT FOUND');
            }
        }
    }
    console.log('========================');
}

// Add this function to restore series filter from sessionStorage
function restoreSeriesFilter() {
    const seriesFilter = sessionStorage.getItem('storiesFilterSeries');
    if (seriesFilter) {
        // Wait for series dropdown to be populated
        setTimeout(() => {
            const seriesSelect = document.getElementById('seriesFilter');
            if (seriesSelect) {
                seriesSelect.value = seriesFilter;
                applyFilters();
            }
            // Clear after applying
            sessionStorage.removeItem('storiesFilterSeries');
        }, 500);
    }
}

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
    document.getElementById('saveStoryEditBtn')?.addEventListener('click', saveStoryEdit);
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