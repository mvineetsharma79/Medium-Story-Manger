// ============================================
// NOTIFICATIONS.JS - Full Working Version
// ============================================

let notificationsCurrentSort = { column: 'date', direction: 'desc' };
let notificationsWithSerial = [];

// Initialize page
async function initNotificationsPage() {
    // Initialize stats widget
    if (typeof MonthlyStatsWidget !== 'undefined') {
        if (!window.monthlyStatsWidget) {
            window.monthlyStatsWidget = new MonthlyStatsWidget('storyStatsWidget', { apiBase: '/api' });
        }
    }
    
    await loadNotifications();
    
    const refreshBtn = document.getElementById('refreshNotificationsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshNotifications);
    }
    
    attachSortListeners();
}

// Load notifications from API
async function loadNotifications() {
    const tbody = document.getElementById('notificationsTableBody');
    const noDataMsg = document.getElementById('noNotificationsMsg');
    
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm me-2"></div>Loading...</td></tr>';
    }
    
    try {
        const response = await fetch('/api/stories/notification');
        const data = await response.json();
        
        const rawNotifications = data.notifications || [];
        
        // Sort by date descending (most recent first)
        const sortedByDate = [...rawNotifications].sort(function(a, b) {
            return (b.occurredAt || 0) - (a.occurredAt || 0);
        });
        
        // Attach serial number to each notification
        notificationsWithSerial = sortedByDate.map(function(notif, index) {
            return {
                ...notif,
                serialNumber: index + 1
            };
        });
        
        if (notificationsWithSerial.length === 0) {
            if (tbody) tbody.innerHTML = '';
            if (noDataMsg) noDataMsg.style.display = 'block';
            return;
        }
        
        if (noDataMsg) noDataMsg.style.display = 'none';
        
        // Initial render (date order, descending)
        renderTable(notificationsWithSerial);
        
    } catch (error) {
        console.error('Error loading notifications:', error);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">Error loading notifications</td></tr>';
        }
    }
}

// Refresh from Medium
async function refreshNotifications() {
    const refreshBtn = document.getElementById('refreshNotificationsBtn');
    
    if (refreshBtn) {
        refreshBtn.classList.add('btn-loading');
        refreshBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Refreshing...';
        refreshBtn.disabled = true;
    }
    
    try {
        const response = await fetch('/api/stories/notification_medium?limit=25');
        const data = await response.json();
        
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
        showToast('Error refreshing notifications', 'error');
    } finally {
        if (refreshBtn) {
            refreshBtn.classList.remove('btn-loading');
            refreshBtn.innerHTML = '<i class="bi bi-arrow-repeat"></i> Refresh';
            refreshBtn.disabled = false;
        }
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
    let sorted = [...notificationsWithSerial];
    
    // Sort based on selected column
    sorted.sort(function(a, b) {
        let aVal, bVal;
        
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
        
        var serialNo = notif.serialNumber;
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
        html += '<td class="text-center" style="width: 50px; color: #6c757d; font-weight: 500;">' + serialNo + '</td>';
        html += '<td><div class="notification-name-cell">';
        
        if (avatarUrl) {
            html += '<img src="' + avatarUrl + '" class="notification-avatar" alt="' + escapeHtml(actorName) + '" onerror="this.onerror=null;this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">';
            html += '<div class="notification-avatar-placeholder" style="display: none;"><i class="bi bi-person"></i></div>';
        } else {
            html += '<div class="notification-avatar-placeholder"><i class="bi bi-person"></i></div>';
        }
        
        html += '<a href="' + actorUrl + '" class="notification-name-link" target="_blank">' + escapeHtml(actorName) + '</a>';
        html += '</div></td>';
        html += '<td class="text-nowrap">' + date + '</td>';
        html += '<td><strong>' + actionIcon + actionText + '</strong></td>';
        html += '<td>';
        
        if (storyTitle) {
            var displayTitle = storyTitle.length > 60 ? storyTitle.substring(0, 60) + '...' : storyTitle;
            html += '<a href="' + storyUrl + '" class="story-link" target="_blank">' + escapeHtml(displayTitle) + '</a>';
        } else {
            html += '<span class="story-empty">—</span>';
        }
        
        html += '</td>';
        
        if (isMemberUser) {
            html += '<td><span class="member-badge"><i class="bi bi-star-fill"></i> Member</span></td>';
        } else {
            html += '<td><span class="non-member-badge">Non Member</span></td>';
        }
        
        if (isAuthor) {
            html += '<td class="text-center"><i class="bi bi-patch-check-fill author-badge" title="Verified Author"></i></td>';
        } else {
            html += '<td class="text-center">—</td>';
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