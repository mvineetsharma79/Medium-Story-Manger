// ============================================
// STORY PREVIEW PAGE - Complete Version
// WITH BRACKET PRESERVATION FOR IMAGE PATHS (LOAD + SAVE)
// ============================================

const API_BASE = '/api';
let storyKey = null;
let originalContent = '';
let vditor = null;
let currentMode = 0;
let storyData = null;

// Initialize Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true }
});

// ============================================
// BRACKET PRESERVATION HELPERS
// ============================================

/**
 * Restore brackets in image paths that were stripped by Vditor
 * Converts ![alt](path) → ![alt](<path>) when path contains spaces
 */
function restoreImageBrackets(content) {
    if (!content) return content;
    
    // Find all image patterns without brackets that need them
    // Match ![alt](path) where path has spaces but no brackets
    const imagePattern = /!\[(.*?)\]\(([^)<>\s][^)]*?)\)/g;
    
    return content.replace(imagePattern, (match, altText, path) => {
        // If path contains spaces or special characters, add brackets
        if ((path.includes(' ') || /[<>"{}|\\^`]/.test(path)) && !path.startsWith('<')) {
            return `![${altText}](<${path}>)`;
        }
        return match;
    });
}

/**
 * Preserve brackets when saving - ensures brackets aren't lost
 */
function preserveImageBrackets(content, originalContent) {
    if (!originalContent) return content;
    
    let fixedContent = content;
    
    // Find all image patterns in the original content that have brackets
    const originalBracketedImages = [];
    const bracketPattern = /!\[(.*?)\]\(<(.*?)>\)/g;
    let match;
    while ((match = bracketPattern.exec(originalContent)) !== null) {
        originalBracketedImages.push({
            fullMatch: match[0],
            altText: match[1],
            path: match[2]
        });
    }
    
    // For each bracketed image in original, check if current content has it without brackets
    for (const img of originalBracketedImages) {
        const withoutBrackets = `![${img.altText}](${img.path})`;
        const withBrackets = `![${img.altText}](<${img.path}>)`;
        
        // If current content has the version without brackets, replace it
        if (fixedContent.includes(withoutBrackets) && !fixedContent.includes(withBrackets)) {
            fixedContent = fixedContent.replace(new RegExp(escapeRegex(withoutBrackets), 'g'), withBrackets);
        }
    }
    
    // Also ensure any new image paths with spaces are properly wrapped
    const spaceInPathPattern = /!\[(.*?)\]\(([^)<>\s][^)]*?)\)/g;
    fixedContent = fixedContent.replace(spaceInPathPattern, (match, altText, path) => {
        if ((path.includes(' ') || /[<>"{}|\\^`]/.test(path)) && !path.startsWith('<')) {
            return `![${altText}](<${path}>)`;
        }
        return match;
    });
    
    return fixedContent;
}

function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============================================
// DOM EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('storyPreviewContainer');
    if (container) storyKey = container.dataset.storyKey;
    if (!storyKey) {
        showToast('No story specified', 'error');
        return;
    }
    loadStoryContent();
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveStory();
        }
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
            // Restore brackets in the loaded content before displaying
            let content = data.content || '';
            content = restoreImageBrackets(content);
            
            originalContent = content;
            storyData = data;
            
            // Expose story data globally for AI module
            window.storyData = storyData;
            
            document.getElementById('storyTitle').textContent = data.title || data.name || 'Untitled';
            document.getElementById('storySeries').textContent = data.series || 'Standalone';
            document.getElementById('storyCreatedDate').textContent = data.createdDate || '-';
            document.getElementById('storyPublishedDate').textContent = data.publishedDate || '-';
            document.getElementById('storyDueDate').textContent = data.publishedDueDate || '-';
            document.getElementById('storyNotes').textContent = data.notes || 'No notes';
            
            const statusEl = document.getElementById('storyStatusBadge');
            const statusClass = {
                'Published': 'status-published',
                'Published Due': 'status-published-due',
                'Ready': 'status-ready',
                'Done': 'status-done',
                'Draft': 'status-draft'
            }[data.status] || 'status-draft';
            statusEl.className = `status-badge ${statusClass}`;
            statusEl.textContent = data.status || 'Draft';
            
            if (data.publishedDueDate) {
                const dueBadge = document.getElementById('storyDueBadge');
                dueBadge.style.display = 'inline-block';
                dueBadge.textContent = `⏰ ${data.publishedDueDate}`;
            }
            
            const tagsList = document.getElementById('storyTagsList');
            if (data.tags && data.tags.length) {
                tagsList.innerHTML = data.tags.map(tag => `<li>${escapeHtml(tag)}</li>`).join('');
            }
            
            initVditor(originalContent);
            document.getElementById('detailsSection').style.display = 'none';
            
            const buildBtn = document.getElementById('buildStoryBtn');
            if (buildBtn) buildBtn.style.display = 'inline-block';
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error loading story', 'error');
        createFallbackEditor('');
    } finally {
        hideLoading();
    }
}

// ============================================
// VDITOR INITIALIZATION
// ============================================

function initVditor(content) {
    if (typeof Vditor === 'undefined') {
        createFallbackEditor(content);
        return;
    }
    
    try {
        vditor = new Vditor('vditor-editor', {
            height: Math.max(window.innerHeight - 420, 650),
            mode: 'ir',
            theme: 'classic',
            icon: 'material',
            value: content || '',
            toolbar: ['emoji', 'headings', 'bold', 'italic', 'strike', '|', 'list', 'ordered-list', '|', 'table', 'link', 'image', '|', 'code', 'inline-code', '|', 'undo', 'redo', '|', 'export', 'fullscreen', 'outline'],
            cache: { enable: false },
            preview: { mode: 'both', theme: { current: 'light' }, markdown: { mermaid: true } },
            after: () => {
                console.log('Vditor initialized');
                // Expose vditor instance globally for AI Content module
                window.vditorInstance = vditor;
                addExportDiagramsButton();
            }
        });
    } catch (error) {
        console.error('Vditor error:', error);
        createFallbackEditor(content);
    }
}

function createFallbackEditor(content) {
    const container = document.getElementById('vditor-editor');
    if (!container) return;
    container.innerHTML = `<textarea id="fallback-editor" style="width:100%; min-height:500px; padding:10px; font-family:monospace;">${escapeHtml(content || '')}</textarea>`;
    // Still expose a mock for AI module
    window.vditorInstance = {
        getValue: () => document.getElementById('fallback-editor')?.value || '',
        setValue: (val) => { const el = document.getElementById('fallback-editor'); if (el) el.value = val; }
    };
}

// ============================================
// EXPORT DIAGRAMS BUTTON
// ============================================

function addExportDiagramsButton() {
    const existing = document.getElementById('export-diagrams-panel');
    if (existing) existing.remove();
    
    const panel = document.createElement('div');
    panel.id = 'export-diagrams-panel';
    panel.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9998;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 40px;
        box-shadow: 0 2px 15px rgba(0,0,0,0.2);
        overflow: hidden;
    `;
    panel.innerHTML = `<button id="export-diagrams-btn" style="background: transparent; border: none; color: white; padding: 10px 20px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">📸 Export Diagrams</button>`;
    document.body.appendChild(panel);
    
    document.getElementById('export-diagrams-btn').onclick = showExportMenu;
    updateButtonCount();
    setInterval(updateButtonCount, 5000);
}

function updateButtonCount() {
    const content = vditor ? vditor.getValue() : originalContent;
    if (!content) return;
    
    const mermaidCount = (content.match(/```mermaid\n[\s\S]*?```/g) || []).length;
    const tableCount = countMarkdownTables(content);
    const total = mermaidCount + tableCount;
    
    const btn = document.getElementById('export-diagrams-btn');
    if (btn) {
        btn.innerHTML = total === 0 ? '📸 No diagrams/tables' : `📸 Export (${total})`;
    }
}

function countMarkdownTables(content) {
    let count = 0;
    const lines = content.split('\n');
    let inTable = false;
    let hasSeparator = false;
    
    for (const line of lines) {
        if (line.includes('|') && !line.trim().startsWith('```')) {
            if (!inTable) {
                inTable = true;
                hasSeparator = false;
            }
            if (line.includes('|-') || line.includes('-|')) {
                hasSeparator = true;
            }
        } else {
            if (inTable && hasSeparator) count++;
            inTable = false;
            hasSeparator = false;
        }
    }
    return count;
}

function showExportMenu() {
    const existingMenu = document.getElementById('export-menu');
    if (existingMenu) existingMenu.remove();
    
    const menu = document.createElement('div');
    menu.id = 'export-menu';
    menu.style.cssText = `
        position: fixed; bottom: 80px; right: 20px; background: white; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25); z-index: 10000; min-width: 280px;
        overflow: hidden;
    `;
    
    menu.innerHTML = `
        <div style="padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #eee; font-weight: bold;">📸 Export Options</div>
        <div style="padding: 12px 16px; background: #e8f5e9; cursor: pointer; border-bottom: 1px solid #eee;" onclick="buildStory(); this.closest('#export-menu').remove();">
            <strong>📦 Build Story</strong><br>
            <small style="color: #666;">Creates folder, renders diagrams/tables as PNG</small>
        </div>
        <div style="padding: 8px 16px; text-align: center; background: #f8f9fa; cursor: pointer; color: #6c757d;" onclick="this.parentElement.remove()">
            Close
        </div>
    `;
    
    document.body.appendChild(menu);
    
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (menu && !menu.contains(e.target) && e.target.id !== 'export-diagrams-btn') {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

// ============================================
// BUILD STORY FUNCTION - With bracket preservation
// ============================================

async function buildStory() {
    if (!storyData) {
        showToast('Story data not loaded', 'error');
        return;
    }
    
    const storyName = storyData.title || storyData.name || 'untitled';
    const safeStoryName = sanitizeFileName(storyName);
    let content = vditor ? await vditor.getValue() : originalContent;
    
    // Preserve brackets before building
    content = preserveImageBrackets(content, originalContent);
    
    const mermaidCount = (content.match(/```mermaid\n[\s\S]*?```/g) || []).length;
    const tableCount = countMarkdownTables(content);
    
    if (mermaidCount === 0 && tableCount === 0) {
        showToast('No diagrams or tables found', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const formData = new FormData();
        formData.append('storyKey', storyKey);
        formData.append('storyName', safeStoryName);
        formData.append('content', content);
        
        const response = await fetch(`${API_BASE}/stories/build-export-python`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ Build complete! Folder: ${result.folderPath}`, 'success');
            console.log('Build completed:', result);
        } else {
            showToast('Build failed: ' + (result.error || 'Unknown error'), 'error');
        }
        
    } catch (error) {
        console.error('Build error:', error);
        showToast('Build failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// SAVE STORY FUNCTIONS - WITH BRACKET PRESERVATION
// ============================================

async function saveStory() {
    const current = vditor ? await vditor.getValue() : document.getElementById('fallback-editor')?.value;
    if (!current) return;
    
    if (current === originalContent) {
        showToast('No changes', 'info');
        return;
    }
    
    // Preserve brackets from original content
    const contentToSave = preserveImageBrackets(current, originalContent);
    
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: contentToSave })
        });
        
        const data = await response.json();
        if (data.success) {
            originalContent = contentToSave;
            // Update Vditor with the bracket-preserved content to keep them in sync
            if (vditor) {
                vditor.setValue(contentToSave);
            }
            showToast('Saved!', 'success');
        } else {
            showToast('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Save error:', error);
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

async function exportAsHTML() {
    const content = vditor ? await vditor.getHTML() : '';
    if (!content) return;
    
    const fullHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${escapeHtml(document.getElementById('storyTitle').textContent)}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"><\/script>
    <script>mermaid.initialize({startOnLoad:true});<\/script></head><body>${content}</body></html>`;
    
    downloadFile(fullHtml, `${document.getElementById('storyTitle').textContent.replace(/[^a-z0-9]/gi, '_')}.html`, 'text/html');
    showToast('HTML exported', 'success');
}

function copyMarkdown() {
    if (vditor) {
        vditor.getValue().then(content => {
            navigator.clipboard.writeText(content);
            showToast('Copied!', 'success');
        });
    }
}

function toggleVditorMode() {
    if (!vditor) return;
    currentMode = (currentMode + 1) % 3;
    const modes = ['ir', 'sv', 'preview'];
    const modeNames = ['WYSIWYG Mode', 'Split View', 'Preview'];
    vditor.setMode(modes[currentMode]);
    showToast(modeNames[currentMode], 'info');
}

function toggleDetails() {
    const section = document.getElementById('detailsSection');
    const btn = document.getElementById('toggleDetailsBtn');
    const hidden = section.style.display === 'none';
    section.style.display = hidden ? 'block' : 'none';
    btn.innerHTML = hidden ? '▲ Hide Details' : '▼ Show Details';
}

function copyTitleToClipboard() {
    const title = document.getElementById('storyTitle').textContent;
    navigator.clipboard.writeText(title);
    showToast('Title copied!', 'success');
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function sanitizeFileName(name) {
    return name
        .replace(/[<>:"\/\\|?*]/g, '')
        .replace(/[\s]+/g, '-')
        .replace(/-+/g, '-')
        .substring(0, 100);
}

function downloadMarkdownFile(content, filename) {
    downloadFile(content, filename, 'text/markdown');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
}

function showLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.style.display = 'flex';
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.style.display = 'none';
}

function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast-custom';
    if (type === 'error') toast.classList.add('error');
    toast.textContent = msg;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'error' ? '#dc3545' : '#28a745'};
        color: white;
        padding: 10px 20px;
        border-radius: 8px;
        font-size: 14px;
        z-index: 10001;
        animation: fadeOut 3s ease-in-out forwards;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// GLOBAL EXPORTS (exposed for AI module and inline onclick)
// ============================================

window.saveStory = saveStory;
window.copyTitleToClipboard = copyTitleToClipboard;
window.toggleDetails = toggleDetails;
window.exportAsHTML = exportAsHTML;
window.copyMarkdown = copyMarkdown;
window.toggleVditorMode = toggleVditorMode;
window.buildStory = buildStory;

// Expose vditor instance for AI Content module
Object.defineProperty(window, 'vditorInstance', {
    get: function() { return vditor; },
    set: function(val) { vditor = val; }
});

// Expose storyData for AI module
Object.defineProperty(window, 'storyData', {
    get: function() { return storyData; },
    set: function(val) { storyData = val; }
});