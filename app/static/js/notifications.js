// ============================================
// NOTIFICATIONS.JS - Two Serial Number Columns
// ============================================

var notificationsCurrentSort = { column: 'date', direction: 'desc' };
var notificationsWithSerial = [];
var isLoadingOlder = false;
var hasMoreNotifications = true;

// Initialize page
async function initNotificationsPage() {
    // Initialize stats widget
    if (typeof MonthlyStatsWidget !== 'undefined') {
        if (!window.monthlyStatsWidget) {
            window.monthlyStatsWidget = new MonthlyStatsWidget('storyStatsWidget', { apiBase: '/api' });
        }
    }
    
    await loadNotifications();
    
    var refreshBtn = document.getElementById('refreshNotificationsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshNotifications);
    }
    
    attachSortListeners();
    addLoadOlderButton();
}

// Load notifications from API
async function loadNotifications() {
    var tbody = document.getElementById('notificationsTableBody');
    var noDataMsg = document.getElementById('noNotificationsMsg');
    
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm me-2"></div>Loading...</td</tr>';
    }
    
    try {
        var response = await fetch('/api/stories/notification');
        var data = await response.json();
        
        var rawNotifications = data.notifications || [];
        
        // Sort by date descending (most recent first)
        var sortedByDate = [...rawNotifications].sort(function(a, b) {
            return (b.occurredAt || 0) - (a.occurredAt || 0);
        });
        
        // Attach fixed serial number to each notification (based on date order)
        notificationsWithSerial = sortedByDate.map(function(notif, index) {
            return {
                ...notif,
                fixedSerial: index + 1
            };
        });
        
        if (notificationsWithSerial.length === 0) {
            if (tbody) tbody.innerHTML = '';
            if (noDataMsg) noDataMsg.style.display = 'block';
            hasMoreNotifications = false;
            return;
        }
        
        if (noDataMsg) noDataMsg.style.display = 'none';
        hasMoreNotifications = true;
        
        // Reset load older button state
        var loadBtn = document.getElementById('loadOlderBtn');
        if (loadBtn) {
            loadBtn.disabled = false;
            loadBtn.innerHTML = 'Load Older';
        }
        
        // Initial render
        renderTable(notificationsWithSerial);
        
    } catch (error) {
        console.error('Error loading notifications:', error);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger py-4">Error loading notifications</td</tr>';
        }
    }
}

// Refresh from Medium
async function refreshNotifications() {
    var refreshBtn = document.getElementById('refreshNotificationsBtn');
    
    if (refreshBtn) {
        refreshBtn.classList.add('btn-loading');
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Refreshing...';
        refreshBtn.disabled = true;
    }
    
    try {
        var response = await fetch('/api/stories/notification_medium?limit=25');
        var data = await response.json();
        
        if (data.success) {
            if (data.new_added > 0) {
                showToast(data.new_added + ' new notification' + (data.new_added > 1 ? 's' : '') + ' added', 'success');
                await loadNotifications();
            } else {
                showToast('No new notifications', 'info');
            }
        } else {
            showToast(data.message || 'Error refreshing notifications', 'error');
        }
    } catch (error) {
        console.error('Error refreshing:', error);
        showToast('Error refreshing notifications', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.classList.remove('btn-loading');
            refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Refresh';
            refreshBtn.disabled = false;
        }
    }
}

// Get oldest timestamp from current notifications
function getOldestTimestamp() {
    if (notificationsWithSerial.length === 0) return null;
    
    var oldest = notificationsWithSerial[0].occurredAt;
    for (var i = 1; i < notificationsWithSerial.length; i++) {
        var currentTime = notificationsWithSerial[i].occurredAt;
        if (currentTime && currentTime < oldest) {
            oldest = currentTime;
        }
    }
    return oldest;
}

// Load older notifications
async function loadOlderNotifications() {
    if (isLoadingOlder) return;
    if (!hasMoreNotifications) {
        showToast('No more notifications to load', 'info');
        return;
    }
    
    var oldestTimestamp = getOldestTimestamp();
    if (!oldestTimestamp) {
        showToast('No notifications to load from', 'info');
        return;
    }
    
    isLoadingOlder = true;
    var loadBtn = document.getElementById('loadOlderBtn');
    if (loadBtn) {
        loadBtn.disabled = true;
        loadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Loading...';
    }
    
    try {
        var url = '/api/stories/notification_medium?limit=25&to=' + oldestTimestamp;
        var response = await fetch(url);
        var data = await response.json();
        
        if (data.success && data.new_notifications && data.new_notifications.length > 0) {
            // Add fixed serial numbers to new notifications (continue from existing count)
            var currentMaxSerial = notificationsWithSerial.length;
            var newWithSerial = data.new_notifications.map(function(notif, idx) {
                return {
                    ...notif,
                    fixedSerial: currentMaxSerial + idx + 1
                };
            });
            
            // Append to existing array
            notificationsWithSerial = notificationsWithSerial.concat(newWithSerial);
            
            // Re-render with current sort
            var sorted = [...notificationsWithSerial];
            sorted.sort(function(a, b) {
                var aVal, bVal;
                
                switch (notificationsCurrentSort.column) {
                    case 'name':
                        aVal = (a.actor && a.actor.name || '').toLowerCase();
                        bVal = (b.actor && b.actor.name || '').toLowerCase();
                        break;
                    case 'date':
                        aVal = a.occurredAt || 0;
                        bVal = b.occurredAt || 0;
                        break;
                    case 'action':
                        aVal = getActionDisplay(a.notificationType);
                        bVal = getActionDisplay(b.notificationType);
                        break;
                    case 'story':
                        aVal = (a.post && a.post.title || '').toLowerCase();
                        bVal = (b.post && b.post.title || '').toLowerCase();
                        break;
                    case 'member':
                        aVal = isMember(a.actor && a.actor.membership && a.actor.membership.tier) ? 1 : 0;
                        bVal = isMember(b.actor && b.actor.membership && b.actor.membership.tier) ? 1 : 0;
                        break;
                    case 'author':
                        aVal = (a.actor && a.actor.verifications && a.actor.verifications.isBookAuthor) ? 1 : 0;
                        bVal = (b.actor && b.actor.verifications && b.actor.verifications.isBookAuthor) ? 1 : 0;
                        break;
                    default:
                        return 0;
                }
                
                if (typeof aVal === 'number' && typeof bVal === 'number') {
                    return notificationsCurrentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
                }
                
                var comparison = String(aVal).localeCompare(String(bVal));
                return notificationsCurrentSort.direction === 'asc' ? comparison : -comparison;
            });
            
            renderTable(sorted);
            showToast('Loaded ' + data.new_added + ' older notifications', 'success');
            
            if (data.new_added === 0) {
                hasMoreNotifications = false;
                if (loadBtn) {
                    loadBtn.disabled = true;
                    loadBtn.innerHTML = 'No More Notifications';
                }
            } else {
                hasMoreNotifications = true;
            }
            
        } else if (data.new_added === 0) {
            hasMoreNotifications = false;
            showToast('No more notifications to load', 'info');
            if (loadBtn) {
                loadBtn.disabled = true;
                loadBtn.innerHTML = 'No More Notifications';
            }
        }
        
    } catch (error) {
        console.error('Error loading older notifications:', error);
        showToast('Error loading older notifications', 'error');
    } finally {
        isLoadingOlder = false;
        var loadBtnFinal = document.getElementById('loadOlderBtn');
        if (loadBtnFinal && hasMoreNotifications && loadBtnFinal.innerHTML !== 'No More Notifications') {
            loadBtnFinal.disabled = false;
            loadBtnFinal.innerHTML = 'Load Older';
        }
    }
}

// Add Load Older button
function addLoadOlderButton() {
    var tableContainer = document.querySelector('.notifications-page .table-responsive');
    if (!tableContainer) return;
    
    if (document.getElementById('loadOlderBtn')) return;
    
    var div = document.createElement('div');
    div.className = 'text-center mt-3';
    div.id = 'loadOlderContainer';
    div.innerHTML = '<button id="loadOlderBtn" class="btn btn-outline-secondary btn-sm">Load Older</button>';
    tableContainer.parentNode.insertBefore(div, tableContainer.nextSibling);
    
    var btn = document.getElementById('loadOlderBtn');
    if (btn) {
        btn.addEventListener('click', loadOlderNotifications);
    }
}

// Sort table
function sortTable(column) {
    if (notificationsCurrentSort.column === column) {
        notificationsCurrentSort.direction = notificationsCurrentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        notificationsCurrentSort.column = column;
        notificationsCurrentSort.direction = 'desc';
    }
    
    // Create a copy for sorting
    var sorted = [...notificationsWithSerial];
    
    // Sort based on selected column
    sorted.sort(function(a, b) {
        var aVal, bVal;
        
        switch (column) {
            case 'name':
                aVal = (a.actor && a.actor.name || '').toLowerCase();
                bVal = (b.actor && b.actor.name || '').toLowerCase();
                break;
            case 'date':
                aVal = a.occurredAt || 0;
                bVal = b.occurredAt || 0;
                break;
            case 'action':
                aVal = getActionDisplay(a.notificationType);
                bVal = getActionDisplay(b.notificationType);
                break;
            case 'story':
                aVal = (a.post && a.post.title || '').toLowerCase();
                bVal = (b.post && b.post.title || '').toLowerCase();
                break;
            case 'member':
                aVal = isMember(a.actor && a.actor.membership && a.actor.membership.tier) ? 1 : 0;
                bVal = isMember(b.actor && b.actor.membership && b.actor.membership.tier) ? 1 : 0;
                break;
            case 'author':
                aVal = (a.actor && a.actor.verifications && a.actor.verifications.isBookAuthor) ? 1 : 0;
                bVal = (b.actor && b.actor.verifications && b.actor.verifications.isBookAuthor) ? 1 : 0;
                break;
            default:
                return 0;
        }
        
        if (typeof aVal === 'number' && typeof bVal === 'number') {
            return notificationsCurrentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
        }
        
        var comparison = String(aVal).localeCompare(String(bVal));
        return notificationsCurrentSort.direction === 'asc' ? comparison : -comparison;
    });
    
    renderTable(sorted);
    updateSortIcons(column);
}

function updateSortIcons(column) {
    var headers = document.querySelectorAll('#notificationsTable .sortable');
    for (var i = 0; i < headers.length; i++) {
        var header = headers[i];
        header.classList.remove('active');
        var icon = header.querySelector('i');
        if (icon) icon.className = 'bi bi-arrow-down-up';
    }
    
    var activeHeader = document.querySelector('#notificationsTable .sortable[data-sort="' + column + '"]');
    if (activeHeader) {
        activeHeader.classList.add('active');
        var icon = activeHeader.querySelector('i');
        if (icon) {
            icon.className = notificationsCurrentSort.direction === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';
        }
    }
}

function renderTable(notificationsToRender) {
    var tbody = document.getElementById('notificationsTableBody');
    if (!tbody) return;
    
    if (!notificationsToRender || notificationsToRender.length === 0) {
        tbody.innerHTML = '';
        return;
    }
    
    var html = '';
    
    for (var i = 0; i < notificationsToRender.length; i++) {
        var notif = notificationsToRender[i];
        var actor = notif.actor || {};
        var post = notif.post || {};
        
        // Index column (changes with sort) - current position + 1
        var currentIndex = i + 1;
        // Fixed serial number (stays with date order)
        var fixedSerial = notif.fixedSerial;
        
        var avatarUrl = actor.imageId ? 'https://miro.medium.com/v2/resize:fill:36:36/' + actor.imageId : null;
        var actorUrl = actor.username ? 'https://medium.com/@' + actor.username : '#';
        var actorName = actor.name || 'Unknown User';
        var date = notif.occurredAt ? formatDate(notif.occurredAt) : '-';
        var storyTitle = post.title || '';
        var storyUrl = post.mediumUrl || '#';
        var isMemberUser = isMember(actor.membership && actor.membership.tier);
        var isAuthor = (actor.verifications && actor.verifications.isBookAuthor) || false;
        
        // Action with emoji icons
        var actionIcon = '';
        var actionText = '';
        
        switch (notif.notificationType) {
            case 'users_following_you_rollup':
            case 'users_following_you':
                actionIcon = '👤+ ';
                actionText = 'Follow';
                break;
            case 'post_added_to_catalog':
                actionIcon = '📚+ ';
                actionText = 'Added To List';
                break;
            case 'post_recommended':
                actionIcon = '👏 ';
                actionText = 'Clap';
                break;
            case 'users_email_subscribed':
                actionIcon = '✉️ ';
                actionText = 'Subscribed';
                break;
            default:
                actionIcon = '🔔 ';
                actionText = getActionDisplay(notif.notificationType);
        }
        
        html += '<tr>';
        // Column 1: Current Index (changes with sort)
        html += '<td class="text-center" style="width: 50px; color: #6c757d; font-weight: 500;">' + currentIndex + '</td>';
        // Column 2: Fixed Serial Number (stays with date order)
        html += '<td class="text-center" style="width: 60px; color: #17a2b8; font-weight: 500;">' + fixedSerial + '</td>';
        // Column 3: Name with Avatar
        html += '<td><div class="notification-name-cell">';
        
        if (avatarUrl) {
            html += '<img src="' + avatarUrl + '" class="notification-avatar" alt="' + escapeHtml(actorName) + '" onerror="this.onerror=null;this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">';
            html += '<div class="notification-avatar-placeholder" style="display: none;"><i class="bi bi-person"></i></div>';
        } else {
            html += '<div class="notification-avatar-placeholder"><i class="bi bi-person"></i></div>';
        }
        
        html += '<a href="' + actorUrl + '" class="notification-name-link" target="_blank">' + escapeHtml(actorName) + '</a>';
        html += '</div></td>';
        // Column 4: Date
        html += '<td class="text-nowrap">' + date + '</td>';
        // Column 5: Action
        html += '<td><strong>' + actionIcon + actionText + '</strong></td>';
        // Column 6: Story
        html += '<td>';
        
        if (storyTitle) {
            var displayTitle = storyTitle.length > 60 ? storyTitle.substring(0, 60) + '...' : storyTitle;
            html += '<a href="' + storyUrl + '" class="story-link" target="_blank">' + escapeHtml(displayTitle) + '</a>';
        } else {
            html += '<span class="story-empty">—</span>';
        }
        
        html += '</td>';
        // Column 7: Member
        if (isMemberUser) {
            html += '<td><span class="member-badge"><i class="bi bi-star-fill"></i> Member</span></td>';
        } else {
            html += '<td><span class="non-member-badge">Non Member</span></td>';
        }
        // Column 8: Author
        if (isAuthor) {
            html += '<td class="text-center"><i class="bi bi-patch-check-fill author-badge" title="Verified Author"></i></td>';
        } else {
            html += '<td class="text-center">—</td';
        }
        
        html += '</tr>';
    }
    
    tbody.innerHTML = html;
}

function attachSortListeners() {
    var headers = document.querySelectorAll('#notificationsTable .sortable');
    for (var i = 0; i < headers.length; i++) {
        var header = headers[i];
        var newHeader = header.cloneNode(true);
        header.parentNode.replaceChild(newHeader, header);
        
        newHeader.addEventListener('click', function() {
            var column = this.getAttribute('data-sort');
            if (column) sortTable(column);
        });
    }
}

function getActionDisplay(notificationType) {
    var map = {
        'users_following_you_rollup': 'Follow',
        'users_following_you': 'Follow',
        'post_added_to_catalog': 'Added To List',
        'post_recommended': 'Clap',
        'users_email_subscribed': 'Subscribed'
    };
    return map[notificationType] || notificationType || '—';
}

function isMember(tier) {
    return tier === 'MEMBER' || (tier && tier !== null);
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

function formatDate(timestamp) {
    var date = new Date(timestamp);
    var day = date.getDate();
    var monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var month = monthNames[date.getMonth()];
    var year = date.getFullYear();
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    
    return day + '-' + month + '-' + year + ' ' + hours + ':' + minutes + ' ' + ampm;
}

function showToast(message, type) {
    type = type || 'info';
    var toast = document.createElement('div');
    toast.className = 'alert alert-' + (type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info') + ' position-fixed bottom-0 end-0 m-3';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.style.animation = 'slideIn 0.3s ease';
    
    var icon = 'bi-info-circle';
    if (type === 'success') icon = 'bi-check-circle';
    if (type === 'error') icon = 'bi-exclamation-triangle';
    
    toast.innerHTML = '<div class="d-flex align-items-center"><i class="bi ' + icon + ' me-2"></i><span>' + message + '</span></div>';
    document.body.appendChild(toast);
    
    setTimeout(function() {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(function() { toast.remove(); }, 300);
    }, 3000);
}

// Add animation styles if not present
if (!document.getElementById('notification-toast-styles')) {
    var style = document.createElement('style');
    style.id = 'notification-toast-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}