// ============================================
// STORY PREVIEW PAGE - Complete Version
// ============================================

const API_BASE = '/api';
let storyKey = null;
let originalContent = '';

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('storyPreviewContainer');
    if (container) storyKey = container.dataset.storyKey;
    if (!storyKey) { showError('No story specified'); return; }
    loadStoryContent();
    
    document.getElementById('sourceContent')?.addEventListener('input', () => {
        clearTimeout(window.previewTimeout);
        window.previewTimeout = setTimeout(() => {
            renderMarkdown(document.getElementById('sourceContent').value);
        }, 500);
    });
    
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); saveStory(); }
        if (e.key === 'Escape') window.close();
    });
});

// ============================================
// LOAD STORY CONTENT
// ============================================

async function loadStoryContent() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`);
        const data = await response.json();
        
        if (data.success) {
            originalContent = data.content;
            document.getElementById('sourceContent').value = data.content;
            
            // Update header
            document.getElementById('storyTitle').textContent = data.title || data.name || 'Untitled';
            document.getElementById('storySeries').textContent = data.series || 'Standalone';
            document.getElementById('storyCreatedDate').textContent = data.createdDate || '-';
            document.getElementById('storyPublishedDate').textContent = data.publishedDate || '-';
            document.getElementById('storyDueDate').textContent = data.publishedDueDate || '-';
            document.getElementById('storyNotes').textContent = data.notes || 'No notes';
            
            // Status Badge
            const statusEl = document.getElementById('storyStatusBadge');
            let statusClass = 'status-draft';
            let statusText = data.status || 'Draft';
            if (data.status === 'Published') statusClass = 'status-published';
            else if (data.status === 'Published Due') statusClass = 'status-published-due';
            else if (data.status === 'Ready') statusClass = 'status-ready';
            else if (data.status === 'Done') statusClass = 'status-done';
            statusEl.className = `status-badge ${statusClass}`;
            statusEl.textContent = statusText;
            
            // Due Badge
            const dueBadge = document.getElementById('storyDueBadge');
            if (data.publishedDueDate) {
                dueBadge.textContent = `⏰ ${data.publishedDueDate}`;
                dueBadge.style.display = 'inline-block';
            } else {
                dueBadge.style.display = 'none';
            }
            
            // Tags as bullet list
            const tagsList = document.getElementById('storyTagsList');
            if (data.tags && data.tags.length > 0) {
                tagsList.innerHTML = data.tags.map(tag => `<li>${escapeHtml(tag)}</li>`).join('');
            } else {
                tagsList.innerHTML = '<li>No tags</li>';
            }
            
            renderMarkdown(data.content);
            
            // Ensure details section starts hidden
            const detailsSection = document.getElementById('detailsSection');
            if (detailsSection) {
                detailsSection.style.display = 'none';
            }
            
            // Ensure toggle button shows correct text
            const toggleBtn = document.getElementById('toggleDetailsBtn');
            if (toggleBtn) {
                toggleBtn.innerHTML = '▼ Show Details';
            }
        } else {
            showError('Failed to load story');
        }
    } catch (error) {
        showError('Error: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ============================================
// MARKDOWN RENDERING
// ============================================

function renderMarkdown(content) {
    const previewDiv = document.getElementById('previewContent');
    if (!previewDiv) return;
    try {
        if (typeof marked !== 'undefined') {
            previewDiv.innerHTML = marked.parse(content);
        } else {
            previewDiv.innerHTML = `<pre>${escapeHtml(content)}</pre>`;
        }
    } catch (error) {
        previewDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
    }
}

// ============================================
// SAVE STORY
// ============================================

async function saveStory() {
    const sourceContent = document.getElementById('sourceContent').value;
    if (sourceContent === originalContent) {
        showToast('No changes to save', 'info');
        return;
    }
    if (!confirm('Save changes?')) return;
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: sourceContent })
        });
        const data = await response.json();
        if (data.success) {
            originalContent = sourceContent;
            renderMarkdown(sourceContent);
            showToast('Saved successfully', 'success');
        } else {
            showToast('Error: ' + (data.detail || 'Unknown'), 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// TAB SWITCHING
// ============================================

function toggleViewMode() {
    const previewTab = document.getElementById('preview-tab');
    const sourceTab = document.getElementById('source-tab');
    const isPreviewActive = previewTab && previewTab.classList.contains('active');
    
    if (isPreviewActive) {
        sourceTab.click();
    } else {
        previewTab.click();
    }
}

// ============================================
// COPY TITLE TO CLIPBOARD
// ============================================

function copyTitleToClipboard() {
    const titleElement = document.getElementById('storyTitle');
    if (!titleElement) return;
    
    const title = titleElement.textContent;
    
    navigator.clipboard.writeText(title).then(() => {
        const originalText = titleElement.innerHTML;
        titleElement.innerHTML = '✅ Copied!';
        setTimeout(() => {
            titleElement.innerHTML = originalText;
        }, 1500);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy title', 'error');
    });
}

// ============================================
// TOGGLE EXPAND/COLLAPSE - COMPLETELY REWRITTEN
// ============================================

function toggleDetails() {
    console.log('toggleDetails called'); // Debug log
    
    const detailsSection = document.getElementById('detailsSection');
    const toggleBtn = document.getElementById('toggleDetailsBtn');
    
    if (!detailsSection) {
        console.error('detailsSection not found!');
        return;
    }
    
    if (!toggleBtn) {
        console.error('toggleBtn not found!');
        return;
    }
    
    // Get current computed style
    const currentDisplay = window.getComputedStyle(detailsSection).display;
    console.log('Current display:', currentDisplay);
    
    if (currentDisplay === 'none') {
        detailsSection.style.display = 'block';
        toggleBtn.innerHTML = '▲ Hide Details';
        console.log('Expanded - display set to block');
    } else {
        detailsSection.style.display = 'none';
        toggleBtn.innerHTML = '▼ Show Details';
        console.log('Collapsed - display set to none');
    }
}

// ============================================
// UI HELPER FUNCTIONS
// ============================================

function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.style.display = 'none';
}

function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = 'toast-custom';
    if (type === 'error') toast.classList.add('error');
    toast.textContent = type === 'success' ? '✅ ' + message : (type === 'error' ? '❌ ' + message : 'ℹ️ ' + message);
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 1500);
}

function showError(message) {
    const previewDiv = document.getElementById('previewContent');
    if (previewDiv) {
        previewDiv.innerHTML = `<div class="alert alert-danger m-3">${escapeHtml(message)}</div>`;
    }
    showToast(message, 'error');
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

// Make functions globally available
window.saveStory = saveStory;
window.toggleViewMode = toggleViewMode;
window.copyTitleToClipboard = copyTitleToClipboard;
window.toggleDetails = toggleDetails;