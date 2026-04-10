// ============================================
// STORY PREVIEW PAGE - Separate JavaScript
// ============================================

const API_BASE = '/api';
let storyKey = null;
let originalContent = '';

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Get story key from data attribute
    const container = document.getElementById('storyPreviewContainer');
    if (container) {
        storyKey = container.dataset.storyKey;
    }
    
    if (!storyKey) {
        showError('No story specified');
        return;
    }
    
    loadStoryContent();
    
    // Setup event listeners
    const sourceTextarea = document.getElementById('sourceContent');
    if (sourceTextarea) {
        sourceTextarea.addEventListener('input', onSourceChange);
    }
    
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();
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
            
            // Set source content
            const sourceTextarea = document.getElementById('sourceContent');
            if (sourceTextarea) {
                sourceTextarea.value = data.content;
            }
            
            // Update header info
            updateHeaderInfo(data);
            
            // Render preview
            renderMarkdown(data.content);
            
            // Update status
            updateStatus('Loaded successfully', 'success');
        } else {
            showError('Failed to load story content');
        }
    } catch (error) {
        console.error('Error loading story:', error);
        showError('Error loading story: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ============================================
// UPDATE HEADER INFO
// ============================================

function updateHeaderInfo(data) {
    // Title
    const titleEl = document.getElementById('storyTitle');
    if (titleEl) titleEl.textContent = data.title || data.name || 'Untitled';
    
    // Created Date
    const createdEl = document.getElementById('storyCreatedDate');
    if (createdEl) createdEl.textContent = data.createdDate || '-';
    
    // Series
    const seriesEl = document.getElementById('storySeries');
    if (seriesEl) seriesEl.textContent = data.series || 'Standalone';
    
    // Published Date
    const publishedEl = document.getElementById('storyPublishedDate');
    if (publishedEl) publishedEl.textContent = data.publishedDate || '-';
    
    // Due Date
    const dueEl = document.getElementById('storyDueDate');
    if (dueEl) {
        if (data.publishedDueDate) {
            dueEl.textContent = data.publishedDueDate;
            dueEl.className = 'fw-bold text-warning';
        } else {
            dueEl.textContent = '-';
            dueEl.className = 'text-muted';
        }
    }
    
    // Status
    const statusEl = document.getElementById('storyStatus');
    if (statusEl) {
        statusEl.textContent = data.status || 'Draft';
        let statusClass = 'status-draft';
        switch(data.status) {
            case 'Published': statusClass = 'status-published'; break;
            case 'Published Due': statusClass = 'status-published-due'; break;
            case 'Ready': statusClass = 'status-ready'; break;
            case 'Done': statusClass = 'status-done'; break;
        }
        statusEl.className = `status-badge ${statusClass}`;
    }
    
    // File Path
    const pathEl = document.getElementById('storyFilePath');
    if (pathEl) pathEl.textContent = data.raw_path || '-';
    
    // Notes
    const notesEl = document.getElementById('storyNotes');
    if (notesEl) notesEl.textContent = data.notes || 'No notes';
    
    // Tags
    const tagsEl = document.getElementById('storyTags');
    if (tagsEl && data.tags && data.tags.length > 0) {
        tagsEl.innerHTML = data.tags.map(tag => 
            `<span class="badge bg-secondary me-1">${escapeHtml(tag)}</span>`
        ).join('');
    } else if (tagsEl) {
        tagsEl.innerHTML = '<span class="text-muted">No tags</span>';
    }
}

// ============================================
// MARKDOWN RENDERING
// ============================================

function renderMarkdown(content) {
    const previewDiv = document.getElementById('previewContent');
    if (!previewDiv) return;
    
    try {
        // Configure marked options
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                highlight: function(code, lang) {
                    return code;
                },
                breaks: true,
                gfm: true
            });
            
            const html = marked.parse(content);
            previewDiv.innerHTML = html;
        } else {
            // Fallback if marked is not loaded
            previewDiv.innerHTML = `<pre style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(content)}</pre>`;
        }
    } catch (error) {
        previewDiv.innerHTML = `<div class="alert alert-danger">Error rendering markdown: ${error.message}</div>`;
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
    
    if (!confirm('Save changes to this story?')) {
        return;
    }
    
    showLoading();
    updateStatus('Saving...', 'info');
    
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
            updateStatus('Saved successfully', 'success');
            showToast('Story saved successfully', 'success');
            
            // Dispatch event for parent window if needed
            if (window.opener) {
                window.opener.postMessage({ type: 'story-saved', key: storyKey }, '*');
            }
        } else {
            updateStatus('Save failed: ' + (data.detail || 'Unknown error'), 'error');
            showToast('Error saving story', 'error');
        }
    } catch (error) {
        console.error('Error saving story:', error);
        updateStatus('Save error: ' + error.message, 'error');
        showToast('Error saving story: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// TAB MANAGEMENT
// ============================================

function switchToPreview() {
    const previewTab = document.getElementById('preview-tab');
    if (previewTab) {
        const tab = new bootstrap.Tab(previewTab);
        tab.show();
    }
}

function switchToSource() {
    const sourceTab = document.getElementById('source-tab');
    if (sourceTab) {
        const tab = new bootstrap.Tab(sourceTab);
        tab.show();
    }
}

function toggleViewMode() {
    const previewTab = document.getElementById('preview-tab');
    const isPreviewActive = previewTab && previewTab.classList.contains('active');
    
    if (isPreviewActive) {
        switchToSource();
    } else {
        switchToPreview();
    }
}

// ============================================
// AUTO-PREVIEW ON SOURCE CHANGE
// ============================================

let previewTimeout;

function onSourceChange() {
    if (previewTimeout) clearTimeout(previewTimeout);
    previewTimeout = setTimeout(() => {
        const sourceContent = document.getElementById('sourceContent').value;
        renderMarkdown(sourceContent);
        updateStatus('Auto-refreshed', 'info');
    }, 500);
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + S = Save
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveStory();
        }
        
        // Ctrl/Cmd + Shift + P = Preview
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'P') {
            e.preventDefault();
            switchToPreview();
        }
        
        // Ctrl/Cmd + Shift + S = Source
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
            e.preventDefault();
            switchToSource();
        }
        
        // Escape = Close
        if (e.key === 'Escape') {
            window.close();
        }
    });
}

// ============================================
// UI HELPERS
// ============================================

function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('saveStatus');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = 'ms-2';
    
    if (type === 'success') {
        statusEl.classList.add('text-success');
        setTimeout(() => {
            if (statusEl.textContent === message) {
                statusEl.textContent = '';
            }
        }, 3000);
    } else if (type === 'error') {
        statusEl.classList.add('text-danger');
    } else {
        statusEl.classList.add('text-muted');
    }
}

function showError(message) {
    const previewDiv = document.getElementById('previewContent');
    if (previewDiv) {
        previewDiv.innerHTML = `<div class="alert alert-danger m-3">${escapeHtml(message)}</div>`;
    }
    updateStatus(message, 'error');
    showToast(message, 'error');
}

function showLoading() {
    const loadingEl = document.getElementById('loadingOverlay');
    if (loadingEl) loadingEl.style.display = 'flex';
}

function hideLoading() {
    const loadingEl = document.getElementById('loadingOverlay');
    if (loadingEl) loadingEl.style.display = 'none';
}

function showToast(message, type = 'info') {
    // Create toast element if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.position = 'fixed';
        toastContainer.style.bottom = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-info');
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 mb-2" role="alert" data-bs-autohide="true" data-bs-delay="3000">
            <div class="d-flex">
                <div class="toast-body">
                    ${type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️')} ${escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: 3000 });
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    return dateStr.split('T')[0];
}

// ============================================
// WINDOW COMMUNICATION
// ============================================

// Listen for messages from parent window
window.addEventListener('message', (event) => {
    if (event.data.type === 'reload') {
        loadStoryContent();
    }
});

// Notify parent that we're ready
if (window.opener) {
    window.opener.postMessage({ type: 'preview-ready', key: storyKey }, '*');
}

// ============================================
// EXPORT FUNCTIONS FOR GLOBAL ACCESS
// ============================================

window.saveStory = saveStory;
window.toggleViewMode = toggleViewMode;
window.switchToPreview = switchToPreview;
window.switchToSource = switchToSource;