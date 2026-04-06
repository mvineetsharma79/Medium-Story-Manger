// ============================================
// STORIES JS - Complete with fixes for stories.json loading
// ============================================

let allStories = [];
let currentEditStoryKey = null;
let currentStatsStoryKey = null;
let currentMonth = 'all';
let currentSort = { column: 'name', direction: 'asc' };
let totalEarnings = 0;
let monthlyEarnings = 0;


// ============================================
// HELPER FUNCTIONS
// ============================================

function formatNumber(num) {
    if (!num && num !== 0) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
}

function formatCurrency(amount) {
    if (!amount && amount !== 0) return '$0.00';
    const dollars = amount / 1000000000;
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

function getCurrentYearMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

function isValidYearMonth(value) {
    if (!value) return false;
    return /^\d{4}-\d{2}$/.test(value);
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

function getTodayDate() {
    const today = new Date();
    return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
}

function getNowTimestamp() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}T${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
}

function calcPercent(part, total) {
    if (!total || total === 0) return 0;
    return Math.round((part / total) * 100);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
        if (!response.ok) {
            console.error('Failed to load months:', response.status);
            return;
        }
        const data = await response.json();
        const selector = document.getElementById('monthSelector');
        if (selector) {
            selector.innerHTML = '';
            const allOption = document.createElement('option');
            allOption.value = 'all';
            allOption.textContent = 'All Time (Dashboard)';
            selector.appendChild(allOption);
            
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
    
    const selectedValue = selector.value;
    if (selectedValue === 'all') {
        currentMonth = 'all';
        localStorage.setItem('selectedMonth', 'all');
    } else if (isValidYearMonth(selectedValue)) {
        currentMonth = selectedValue;
        localStorage.setItem('selectedMonth', selectedValue);
    }
    await loadStories();
}

// ============================================
// LOAD STORIES - FIXED
// ============================================

async function loadStories() {
    showLoading();
    try {
        // Always use the list endpoint which combines stories.json and monthly data
        let url;
        if (currentMonth === 'all') {
            url = `${API_BASE}/stories/list`;
        } else {
            url = `${API_BASE}/stories/list/${currentMonth}`;
        }
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        allStories = data.stories || [];
        
        // Populate series filter dropdown
        const seriesSet = new Set();
        allStories.forEach(story => {
            if (story.series && story.series !== 'null' && story.series !== 'undefined') {
                seriesSet.add(story.series);
            }
        });
        
        const seriesFilter = document.getElementById('seriesFilter');
        if (seriesFilter) {
            seriesFilter.innerHTML = '<option value="">All Series</option>';
            Array.from(seriesSet).sort().forEach(series => {
                const option = document.createElement('option');
                option.value = series;
                option.textContent = series;
                seriesFilter.appendChild(option);
            });
        }
        
        // Calculate earnings
        if (currentMonth === 'all') {
            totalEarnings = allStories.reduce((sum, s) => sum + (s.medium_earnings || 0), 0);
            monthlyEarnings = 0;
        } else {
            monthlyEarnings = allStories.reduce((sum, s) => sum + (s.medium_earnings || 0), 0);
            totalEarnings = await fetchTotalEarnings();
        }
        
        // Update earnings banners
        const monthlyEarningsBanner = document.getElementById('monthlyEarningsBanner');
        const totalEarningsBanner = document.getElementById('totalEarningsBanner');
        
        if (monthlyEarningsBanner) {
            monthlyEarningsBanner.innerHTML = `<i class="bi bi-currency-dollar"></i> Monthly Earnings: ${formatCurrency(monthlyEarnings)}`;
        }
        if (totalEarningsBanner) {
            totalEarningsBanner.innerHTML = `<i class="bi bi-pie-chart"></i> All-Time Earnings: ${formatCurrency(totalEarnings)}`;
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
            tbody.innerHTML = '<tr><td colspan="16" class="text-center text-danger py-3">Error loading stories. Please try again.</td></tr>';
        }
    } finally {
        hideLoading();
    }
}

async function fetchTotalEarnings() {
    try {
        const response = await fetch(`${API_BASE}/stories/earnings/total`);
        if (!response.ok) return 0;
        const data = await response.json();
        return data.total_earnings || 0;
    } catch (error) {
        console.error('Error fetching total earnings:', error);
        return 0;
    }
}

// ============================================
// RENDER STORY TABLE - 16 COLUMNS
// ============================================

function applyFilters() { renderStoryTable(); }

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
        const searchText = searchFilter.value.toLowerCase();
        filtered = filtered.filter(s => s.name.toLowerCase().includes(searchText));
    }
    if (bookmarkedOnly && bookmarkedOnly.checked) filtered = filtered.filter(s => s.bookmarked === true);
    if (leaderboardOnly && leaderboardOnly.checked) filtered = filtered.filter(s => s.leaderboard === true);
    
    filtered.sort((a, b) => {
        let aVal = a[currentSort.column];
        let bVal = b[currentSort.column];
        if (typeof aVal === 'boolean') { aVal = aVal ? 1 : 0; bVal = bVal ? 1 : 0; }
        if (typeof aVal === 'string') { aVal = (aVal || '').toLowerCase(); bVal = (bVal || '').toLowerCase(); }
        return currentSort.direction === 'asc' ? (aVal > bVal ? 1 : -1) : (aVal < bVal ? 1 : -1);
    });
    
    const filterCountDisplay = document.getElementById('filterCountDisplay');
    if (filterCountDisplay) {
        filterCountDisplay.textContent = `Showing ${filtered.length} of ${allStories.length} stories`;
    }
    
    tbody.innerHTML = '';
    
    if (filtered.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell(0);
        cell.colSpan = 16;
        cell.className = 'text-center text-muted py-3';
        cell.textContent = 'No stories found. Click "Sync Files" to import stories from filesystem.';
        return;
    }
    
    filtered.forEach(story => {
        const row = tbody.insertRow();
        row.className = 'table-row-clickable';
        row.onclick = () => openEditModal(story);
        
        // 1. Bookmark
        const bookmarkCell = row.insertCell(0);
        bookmarkCell.className = 'text-center';
        bookmarkCell.onclick = (e) => e.stopPropagation();
        const bookmarkIcon = document.createElement('i');
        bookmarkIcon.className = `bi bi-bookmark${story.bookmarked ? '-fill' : ''} bookmark-icon ${story.bookmarked ? 'bookmarked' : ''}`;
        bookmarkIcon.onclick = () => toggleBookmark(story);
        bookmarkCell.appendChild(bookmarkIcon);
        
        // 2. Leaderboard
        const leaderboardCell = row.insertCell(1);
        leaderboardCell.className = 'text-center';
        leaderboardCell.onclick = (e) => e.stopPropagation();
        const trophyIcon = document.createElement('i');
        trophyIcon.className = `bi bi-trophy${story.leaderboard ? '-fill' : ''} leaderboard-icon ${story.leaderboard ? 'leaderboard' : ''}`;
        trophyIcon.onclick = () => toggleLeaderboard(story);
        leaderboardCell.appendChild(trophyIcon);
        
        // 3. Status
        const statusCell = row.insertCell(2);
        const statusSpan = document.createElement('span');
        const statusClass = `status-${story.status?.toLowerCase() || 'draft'}`;
        statusSpan.className = `status-badge ${statusClass}`;
        statusSpan.textContent = story.status || 'Draft';
        statusCell.appendChild(statusSpan);
        
        // 4. Title
        const nameCell = row.insertCell(3);
        nameCell.textContent = story.name;
        
        // 5. Created Date
        const createdDateCell = row.insertCell(4);
        createdDateCell.textContent = story.created_date ? story.created_date.split('T')[0] : '-';
        
        // 6. Published Date
        const publishedDateCell = row.insertCell(5);
        const publishDate = story.medium_first_published ? story.medium_first_published.split('T')[0] : (story.published_date ? story.published_date.split('T')[0] : '-');
        publishedDateCell.textContent = publishDate;
        
        // 7. Reads
        const readsCell = row.insertCell(6);
        readsCell.className = 'stats-tooltip';
        readsCell.title = `${story.member_reads} of ${story.reads} reads (${story.reads_percent}% members)`;
        readsCell.innerHTML = `${formatNumber(story.member_reads)}/${formatNumber(story.reads)}<br><small>${story.reads_percent}%</small>`;
        
        // 8. Views
        const viewsCell = row.insertCell(7);
        viewsCell.className = 'stats-tooltip';
        viewsCell.title = `${story.member_views} of ${story.views} views (${story.views_percent}% members)`;
        viewsCell.innerHTML = `${formatNumber(story.member_views)}/${formatNumber(story.views)}<br><small>${story.views_percent}%</small>`;
        
        // 9. Impression
        const impressionCell = row.insertCell(8);
        impressionCell.className = 'stats-tooltip';
        impressionCell.title = 'Lifetime Reads / Lifetime Views / Presentations';
        impressionCell.innerHTML = `${formatNumber(story.lifetime_reads)}/${formatNumber(story.lifetime_views)}/${formatNumber(story.presentation_count)}`;
        
        // 10. Claps
        const clapsCell = row.insertCell(9);
        clapsCell.className = 'stats-tooltip';
        clapsCell.title = 'Monthly Claps / Lifetime Claps';
        clapsCell.innerHTML = `${formatNumber(story.claps)}<br><small>${formatNumber(story.lifetime_claps)}</small>`;
        
        // 11. Earnings
        const earningsCell = row.insertCell(10);
        earningsCell.className = 'stats-tooltip';
        earningsCell.title = 'Monthly Earnings / All-Time Earnings';
        earningsCell.innerHTML = `${formatCurrency(story.medium_earnings)}<br><small>${formatCurrency(totalEarnings)}</small>`;
        
        // 12. Followers
        const followersCell = row.insertCell(11);
        followersCell.className = 'stats-tooltip';
        followersCell.title = 'New Followers (Month) / Total Followers';
        const followerPercent = calcPercent(story.medium_new_followers, story.total_followers);
        followersCell.innerHTML = `${formatNumber(story.medium_new_followers)}/${formatNumber(story.total_followers)}<br><small>${followerPercent}%</small>`;
        
        // 13. Read Time
        const readTimeCell = row.insertCell(12);
        const readingTime = story.medium_reading_time || story.read_time || 0;
        readTimeCell.textContent = `${formatReadTime(readingTime)} / ${formatNumber(story.word_count)}`;
        
        // 14. Publisher
        const publisherCell = row.insertCell(13);
        publisherCell.textContent = story.medium_publication || '—';
        
        // 15. LinkedIn Status
        const linkedinCell = row.insertCell(14);
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
        
        // 16. Actions
        const actionsCell = row.insertCell(15);
        actionsCell.className = 'action-buttons';
        actionsCell.onclick = (e) => e.stopPropagation();
        
        const statsBtn = document.createElement('button');
        statsBtn.className = 'btn btn-sm btn-outline-info';
        statsBtn.title = 'Stats';
        statsBtn.innerHTML = '<i class="bi bi-graph-up"></i>';
        statsBtn.onclick = () => openStatsModal(story);
        actionsCell.appendChild(statsBtn);
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-outline-primary ms-1';
        editBtn.title = 'Edit';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.onclick = () => openEditModal(story);
        actionsCell.appendChild(editBtn);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger ms-1';
        deleteBtn.title = 'Delete';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.onclick = () => deleteStory(story);
        actionsCell.appendChild(deleteBtn);
    });
}

// ============================================
// TOGGLE BOOKMARK
// ============================================

async function toggleBookmark(story) {
    let identifier = story.medium_url;
    if (!identifier) {
        identifier = story.name;
    }
    
    const newState = !story.bookmarked;
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/by-identifier/${encodeURIComponent(identifier)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bookmarked: newState })
        });
        
        if (response.ok) {
            await loadStories();
            showToast('Bookmark updated', 'success');
        } else {
            showToast('Error updating bookmark', 'error');
        }
    } catch (error) {
        console.error('Error toggling bookmark:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// TOGGLE LEADERBOARD
// ============================================

async function toggleLeaderboard(story) {
    let yearmonth = currentMonth === 'all' ? getCurrentYearMonth() : currentMonth;
    const newLeaderboardStatus = !story.leaderboard;
    
    const monthlyData = {
        leaderboard: newLeaderboardStatus,
        leaderboard_nanos: story.leaderboard_nanos || 0
    };
    
    let identifier = story.medium_url;
    if (!identifier) {
        identifier = story.name;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/stats/by-identifier?identifier=${encodeURIComponent(identifier)}&yearmonth=${yearmonth}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        if (response.ok) {
            await loadStories();
            showToast('Leaderboard status updated', 'success');
        } else {
            const error = await response.json();
            showToast('Failed to update leaderboard status: ' + (error.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error toggling leaderboard:', error);
        showToast('Error: ' + error.message, 'error');
    }
}

// ============================================
// DELETE STORY
// ============================================

async function deleteStory(story) {
    if (!confirm(`Delete story "${story.name}"? This action cannot be undone.`)) return;
    
    let identifier = story.medium_url;
    if (!identifier) {
        identifier = story.name;
    }
    
    try {
        const response = await fetch(`${API_BASE}/stories/story/by-identifier/${encodeURIComponent(identifier)}`, { 
            method: 'DELETE' 
        });
        
        if (response.ok) {
            showToast('Story deleted successfully', 'success');
            await loadStories();
        } else {
            let storyKey = story.key;
            if (storyKey && storyKey.startsWith('./')) {
                storyKey = storyKey.substring(2);
            }
            const fallbackResponse = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`, { 
                method: 'DELETE' 
            });
            
            if (fallbackResponse.ok) {
                showToast('Story deleted successfully', 'success');
                await loadStories();
            } else {
                const error = await response.json();
                showToast('Error deleting story: ' + (error.detail || 'Unknown error'), 'error');
            }
        }
    } catch (error) {
        console.error('Error deleting story:', error);
        showToast('Error deleting story: ' + error.message, 'error');
    }
}

// ============================================
// OPEN EDIT MODAL
// ============================================

async function openEditModal(story) {
    let identifier = story.medium_url;
    if (!identifier) {
        identifier = story.name;
    }
    
    currentEditStoryKey = story.key;
    const now = new Date();
    const targetYear = now.getFullYear();
    const targetMonth = now.getMonth() + 1;
    
    await loadStoryIntoEditModal(identifier, targetYear, targetMonth);
    const modalElement = document.getElementById('editStoryModal');
    if (modalElement) new bootstrap.Modal(modalElement).show();
}

async function loadStoryIntoEditModal(identifier, year, month) {
    try {
        const encodedIdentifier = encodeURIComponent(identifier);
        
        const storyRes = await fetch(`${API_BASE}/stories/story/by-identifier/${encodedIdentifier}`);
        if (!storyRes.ok) throw new Error('Story not found');
        const story = await storyRes.json();
        
        const monthlyRes = await fetch(`${API_BASE}/stories/stats/by-identifier?identifier=${encodedIdentifier}&yearmonth=${year}-${String(month).padStart(2, '0')}`);
        let monthlyStats = {};
        if (monthlyRes.ok) monthlyStats = await monthlyRes.json();
        
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
        
        setValue('editStoryKey', story.key);
        setValue('editStoryName', story.name);
        setValue('editStatus', story.status || 'Draft');
        setValue('editCreatedDate', story.created_date ? story.created_date.split('T')[0] : '');
        setValue('editPublishedDate', story.published_date ? story.published_date.split('T')[0] : '');
        setValue('editMediumUrl', story.medium_url || '');
        setValue('editPublication', story.medium_publication || '');
        setValue('editTags', (story.tags || []).join(', '));
        setValue('editNotes', story.notes || '');
        setSelectValue('editLinkedinStatus', story.linkedin_status || '');
        setValue('editLinkedinTimestamp', story.linkedin_timestamp || '');
        setValue('editLinkedinImpressions', story.linkedin_impressions || 0);
        setValue('editLinkedinUrl', story.linkedin_url || '');
        setSelectValue('editBookmarked', story.bookmarked ? 'true' : 'false');
        
        setText('lifetimeReads', formatNumber(story.lifetime_reads || 0));
        setText('lifetimeViews', formatNumber(story.lifetime_views || 0));
        setText('lifetimeClaps', formatNumber(story.lifetime_claps || 0));
        setText('presentationCount', formatNumber(story.presentation_count || 0));
        setText('wordCount', formatNumber(story.word_count || 0));
        setText('readingTime', story.medium_reading_time || story.read_time || 0);
        setText('totalFollowers', formatNumber(story.medium_new_followers || 0));
        
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
        setValue('editMediumEarnings', monthlyStats.medium_earnings || 0);
        
        const monthLabel = document.getElementById('currentMonthLabel');
        if (monthLabel) monthLabel.textContent = `${year}-${String(month).padStart(2, '0')}`;
        
        window.currentEditYear = year;
        window.currentEditMonth = month;
        
        await loadAllMonthsStats(story.key);
        
    } catch (error) {
        console.error('Error loading story for edit:', error);
        showToast('Error loading story: ' + error.message, 'error');
    }
}

async function loadAllMonthsStats(storyKey) {
    if (!storyKey) return;
    try {
        const response = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats`);
        const data = await response.json();
        const container = document.getElementById('allMonthsStatsList');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (!data.months || data.months.length === 0) {
            const div = document.createElement('div');
            div.className = 'text-center p-3 text-muted';
            div.textContent = 'No monthly data available';
            container.appendChild(div);
            return;
        }
        
        const listGroup = document.createElement('div');
        listGroup.className = 'list-group list-group-flush';
        
        for (const month of data.months) {
            const item = document.createElement('div');
            item.className = 'list-group-item list-group-item-action';
            
            const headerDiv = document.createElement('div');
            headerDiv.className = 'd-flex justify-content-between align-items-center';
            
            const strong = document.createElement('strong');
            strong.textContent = month.yearmonth;
            headerDiv.appendChild(strong);
            
            const badge = document.createElement('span');
            badge.className = `badge ${month.leaderboard ? 'bg-warning' : 'bg-secondary'}`;
            badge.textContent = month.leaderboard ? '🏆 Leaderboard' : 'Normal';
            headerDiv.appendChild(badge);
            
            const fetchBtn = document.createElement('button');
            fetchBtn.className = 'btn btn-sm btn-outline-primary';
            fetchBtn.innerHTML = '<i class="bi bi-cloud-download"></i> Fetch';
            fetchBtn.onclick = () => refreshStoryStatsForMonth(storyKey, month.yearmonth);
            headerDiv.appendChild(fetchBtn);
            
            item.appendChild(headerDiv);
            
            const statsDiv = document.createElement('div');
            statsDiv.className = 'row small mt-1';
            
            const readsCol = document.createElement('div');
            readsCol.className = 'col-3';
            readsCol.textContent = `Reads: ${formatNumber(month.reads)}`;
            statsDiv.appendChild(readsCol);
            
            const viewsCol = document.createElement('div');
            viewsCol.className = 'col-3';
            viewsCol.textContent = `Views: ${formatNumber(month.views)}`;
            statsDiv.appendChild(viewsCol);
            
            const clapsCol = document.createElement('div');
            clapsCol.className = 'col-3';
            clapsCol.textContent = `Claps: ${formatNumber(month.claps)}`;
            statsDiv.appendChild(clapsCol);
            
            const responsesCol = document.createElement('div');
            responsesCol.className = 'col-3';
            responsesCol.textContent = `Responses: ${formatNumber(month.responses)}`;
            statsDiv.appendChild(responsesCol);
            
            item.appendChild(statsDiv);
            
            const memberDiv = document.createElement('div');
            memberDiv.className = 'row small';
            
            const memberReadsCol = document.createElement('div');
            memberReadsCol.className = 'col-6';
            memberReadsCol.textContent = `Member Reads: ${formatNumber(month.member_reads)}`;
            memberDiv.appendChild(memberReadsCol);
            
            const memberViewsCol = document.createElement('div');
            memberViewsCol.className = 'col-6';
            memberViewsCol.textContent = `Member Views: ${formatNumber(month.member_views)}`;
            memberDiv.appendChild(memberViewsCol);
            
            item.appendChild(memberDiv);
            
            const earningsDiv = document.createElement('div');
            earningsDiv.className = 'row small';
            
            const earningsCol = document.createElement('div');
            earningsCol.className = 'col-12';
            earningsCol.textContent = `Earnings: ${formatCurrency(month.medium_earnings || 0)}`;
            earningsDiv.appendChild(earningsCol);
            
            item.appendChild(earningsDiv);
            
            listGroup.appendChild(item);
        }
        
        container.appendChild(listGroup);
    } catch (error) {
        console.error('Error loading all months stats:', error);
    }
}

async function saveStoryEdit() {
    const storyKey = document.getElementById('editStoryKey')?.value;
    if (!storyKey) return;
    
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
        bookmarked: document.getElementById('editBookmarked')?.value === 'true'
    };
    
    const monthlyData = {
        member_reads: parseInt(document.getElementById('editMemberReads')?.value) || 0,
        nonmember_reads: parseInt(document.getElementById('editNonMemberReads')?.value) || 0,
        member_views: parseInt(document.getElementById('editMemberViews')?.value) || 0,
        nonmember_views: parseInt(document.getElementById('editNonMemberViews')?.value) || 0,
        claps: parseInt(document.getElementById('editClaps')?.value) || 0,
        responses: parseInt(document.getElementById('editResponses')?.value) || 0,
        medium_new_followers: parseInt(document.getElementById('editNewFollowers')?.value) || 0,
        medium_highlights: parseInt(document.getElementById('editHighlights')?.value) || 0,
        leaderboard: document.getElementById('editLeaderboard')?.value === 'true',
        leaderboard_nanos: parseInt(document.getElementById('editLeaderboardNanos')?.value) || 0,
        medium_earnings: parseFloat(document.getElementById('editMediumEarnings')?.value) || 0
    };
    
    const year = window.currentEditYear || new Date().getFullYear();
    const month = window.currentEditMonth || new Date().getMonth() + 1;
    
    showLoading();
    try {
        const permRes = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(storyData)
        });
        
        if (!permRes.ok) {
            throw new Error('Failed to update story metadata');
        }
        
        const monthlyRes = await fetch(`${API_BASE}/stories/story/${encodeURIComponent(storyKey)}/stats/${year}-${String(month).padStart(2, '0')}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(monthlyData)
        });
        
        if (!monthlyRes.ok) {
            console.warn('Failed to update monthly stats');
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('editStoryModal'));
        if (modal) modal.hide();
        
        await loadStories();
        showToast('Story saved successfully', 'success');
        
    } catch (error) {
        console.error('Error saving story:', error);
        showToast('Error saving story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function refreshCurrentStoryStats() {
    const mediumUrl = document.getElementById('editMediumUrl')?.value;
    if (!mediumUrl) { showToast('No Medium URL found', 'error'); return; }
    
    const postId = extractPostIdFromUrl(mediumUrl);
    if (!postId) { showToast('Could not extract post ID', 'error'); return; }
    
    let yearmonth = window.currentEditMonth ? `${window.currentEditYear}-${String(window.currentEditMonth).padStart(2, '0')}` : getCurrentYearMonth();
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-story-stats/${postId}/${yearmonth}`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            const identifier = mediumUrl;
            const statsResponse = await fetch(`${API_BASE}/stories/stats/by-identifier?identifier=${encodeURIComponent(identifier)}&yearmonth=${yearmonth}`);
            
            if (statsResponse.ok) {
                const monthlyStats = await statsResponse.json();
                
                document.getElementById('editMemberReads').value = monthlyStats.member_reads || 0;
                document.getElementById('editNonMemberReads').value = monthlyStats.nonmember_reads || 0;
                document.getElementById('editMemberViews').value = monthlyStats.member_views || 0;
                document.getElementById('editNonMemberViews').value = monthlyStats.nonmember_views || 0;
                document.getElementById('editClaps').value = monthlyStats.claps || 0;
                document.getElementById('editResponses').value = monthlyStats.responses || 0;
                document.getElementById('editNewFollowers').value = monthlyStats.medium_new_followers || 0;
                document.getElementById('editHighlights').value = monthlyStats.medium_highlights || 0;
                document.getElementById('editLeaderboard').value = monthlyStats.leaderboard ? 'true' : 'false';
                document.getElementById('editLeaderboardNanos').value = monthlyStats.leaderboard_nanos || 0;
                document.getElementById('editMediumEarnings').value = (monthlyStats.medium_earnings || 0) / 1000000000;
                
                showToast(`Stats refreshed for ${yearmonth}`, 'success');
                await loadStories();
            } else {
                showToast('Stats fetched but failed to load story data', 'warning');
            }
        } else {
            showToast('Error refreshing stats: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
        showToast('Error refreshing stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function refreshStoryStatsForMonth(storyKey, yearmonth) {
    const story = allStories.find(s => s.key === storyKey);
    if (!story || !story.medium_url) { showToast('Story has no Medium URL', 'error'); return; }
    
    const postId = extractPostIdFromUrl(story.medium_url);
    if (!postId) { showToast('Could not extract post ID', 'error'); return; }
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-story-stats/${postId}/${yearmonth}`, { method: 'POST' });
        const data = await response.json();
        if (response.ok && data.success) {
            showToast(`Stats refreshed for ${yearmonth}`, 'success');
            const [year, month] = yearmonth.split('-');
            await loadStoryIntoEditModal(story.medium_url || story.name, parseInt(year), parseInt(month));
            await loadStories();
        } else {
            showToast('Error refreshing stats: ' + (data.detail || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error refreshing stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

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
    
    const totalMemberReads = allStories.reduce((sum, s) => sum + (s.member_reads || 0), 0);
    const totalReads = allStories.reduce((sum, s) => sum + (s.reads || 0), 0);
    const totalMemberViews = allStories.reduce((sum, s) => sum + (s.member_views || 0), 0);
    const totalViews = allStories.reduce((sum, s) => sum + (s.views || 0), 0);
    const totalClaps = allStories.reduce((sum, s) => sum + (s.claps || 0), 0);
    
    const totalMemberReadPercent = calcPercent(totalMemberReads, totalReads);
    const totalMemberViewPercent = calcPercent(totalMemberViews, totalViews);
    const readRatio = totalViews > 0 ? Math.round((totalReads / totalViews) * 100) : 0;
    
    const elements = {
        totalCount: total,
        publishedCount: published,
        readyCount: ready,
        draftCount: draft,
        doneCount: done,
        bookmarkedCount: bookmarked,
        leaderboardStoryCount: leaderboard,
        totalReads: `${formatNumber(totalMemberReads)}/${formatNumber(totalReads)}`,
        memberReadPercent: `${totalMemberReadPercent}% members`,
        totalViews: `${formatNumber(totalMemberViews)}/${formatNumber(totalViews)}`,
        memberViewPercent: `${totalMemberViewPercent}% members`,
        readRatio: `${readRatio}%`,
        totalClaps: formatNumber(totalClaps)
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
}

// ============================================
// OPEN STATS MODAL
// ============================================

async function openStatsModal(story) {
    currentStatsStoryKey = story.key;
    showLoading();
    try {
        const storyNameEl = document.getElementById('statsStoryName');
        if (storyNameEl) storyNameEl.textContent = story.name;
        
        const statsReads = document.getElementById('statsReads');
        const statsViews = document.getElementById('statsViews');
        const statsClaps = document.getElementById('statsClaps');
        const statsReadPercent = document.getElementById('statsReadPercent');
        const statsViewPercent = document.getElementById('statsViewPercent');
        const statsLifetimeReads = document.getElementById('statsLifetimeReads');
        const statsLifetimeViews = document.getElementById('statsLifetimeViews');
        const statsLifetimeClaps = document.getElementById('statsLifetimeClaps');
        const statsPresentationCount = document.getElementById('statsPresentationCount');
        
        if (statsReads) statsReads.textContent = formatNumber(story.reads || 0);
        if (statsViews) statsViews.textContent = formatNumber(story.views || 0);
        if (statsClaps) statsClaps.textContent = formatNumber(story.claps || 0);
        if (statsReadPercent) statsReadPercent.textContent = `${calcPercent(story.member_reads, story.reads)}% members`;
        if (statsViewPercent) statsViewPercent.textContent = `${calcPercent(story.member_views, story.views)}% members`;
        if (statsLifetimeReads) statsLifetimeReads.textContent = formatNumber(story.lifetime_reads || 0);
        if (statsLifetimeViews) statsLifetimeViews.textContent = formatNumber(story.lifetime_views || 0);
        if (statsLifetimeClaps) statsLifetimeClaps.textContent = formatNumber(story.lifetime_claps || 0);
        if (statsPresentationCount) statsPresentationCount.textContent = formatNumber(story.presentation_count || 0);
        
        const modalElement = document.getElementById('statsModal');
        if (modalElement) new bootstrap.Modal(modalElement).show();
    } catch (error) {
        showToast('Error loading stats: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// ADD STORY MODAL
// ============================================

async function openAddStoryModal() {
    try {
        const seriesRes = await fetch(`${API_BASE}/series/`);
        const seriesList = await seriesRes.json();
        const seriesSelect = document.getElementById('addStorySeries');
        if (seriesSelect) {
            seriesSelect.innerHTML = '';
            const noneOption = document.createElement('option');
            noneOption.value = '';
            noneOption.textContent = 'None';
            seriesSelect.appendChild(noneOption);
            
            if (Array.isArray(seriesList)) {
                seriesList.forEach(s => {
                    const option = document.createElement('option');
                    option.value = s.name;
                    option.textContent = s.name;
                    seriesSelect.appendChild(option);
                });
            }
        }
        const today = getTodayDate();
        const createdDateInput = document.getElementById('addStoryCreatedDate');
        if (createdDateInput) createdDateInput.value = today;
        
        const nameInput = document.getElementById('addStoryName');
        const tagsInput = document.getElementById('addStoryTags');
        const readTimeInput = document.getElementById('addStoryReadTime');
        const publishedDateInput = document.getElementById('addStoryPublishedDate');
        const mediumUrlInput = document.getElementById('addStoryMediumUrl');
        const publicationInput = document.getElementById('addStoryPublication');
        
        if (nameInput) nameInput.value = '';
        if (tagsInput) tagsInput.value = '';
        if (readTimeInput) readTimeInput.value = '';
        if (publishedDateInput) publishedDateInput.value = '';
        if (mediumUrlInput) mediumUrlInput.value = '';
        if (publicationInput) publicationInput.value = '';
        
        const modalElement = document.getElementById('addStoryModal');
        if (modalElement) new bootstrap.Modal(modalElement).show();
    } catch (error) {
        showToast('Error loading series', 'error');
    }
}

async function createStory() {
    const nameInput = document.getElementById('addStoryName');
    const name = nameInput?.value.trim();
    if (!name) { showToast('Story name is required', 'error'); return; }
    
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
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create story');
        }
        
        const modal = bootstrap.Modal.getInstance(document.getElementById('addStoryModal'));
        if (modal) modal.hide();
        await loadStories();
        showToast('Story created successfully', 'success');
    } catch (error) {
        console.error('Error creating story:', error);
        showToast('Error creating story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// SYNC STORIES
// ============================================

async function syncStories() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/sync`, { method: 'POST' });
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Sync completed: ${data.added || 0} added, ${data.updated || 0} updated, ${data.total_stories || 0} total`, 'success');
            await loadStories();
        } else {
            showToast('Error syncing stories', 'error');
        }
    } catch (error) {
        console.error('Error syncing stories:', error);
        showToast('Error syncing stories: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// LEADERBOARD UPDATE
// ============================================

async function updateLeaderboardStats() {
    let yearmonth = currentMonth === 'all' ? getCurrentYearMonth() : currentMonth;
    if (!yearmonth) { showToast('No month selected', 'error'); return; }
    if (!confirm(`Fetch leaderboard stats for ${yearmonth}?`)) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/fetch-leaderboard-stats/${yearmonth}`, { method: 'POST' });
        const data = await response.json();
        if (response.ok && data.success) {
            showToast(`Leaderboard stats updated: ${data.updated} updated, ${data.added} added`, 'success');
            await loadStories();
        } else {
            showToast('Error updating leaderboard stats', 'error');
        }
    } catch (error) {
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
    
    const addStoryBtn = document.getElementById('addStoryCreateBtn');
    if (addStoryBtn) addStoryBtn.addEventListener('click', createStory);
    
    const saveStoryBtn = document.getElementById('saveStoryEditBtn');
    if (saveStoryBtn) saveStoryBtn.addEventListener('click', saveStoryEdit);
    
    const syncBtn = document.getElementById('syncStoriesBtn');
    if (syncBtn) syncBtn.addEventListener('click', syncStories);
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