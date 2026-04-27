// ============================================
// STORY PREVIEW PAGE - Export Diagrams from Preview
// ============================================

// ========== CONFIGURATION CONSTANTS ==========
const AUTO_SAVE_ENABLED = false;
const AUTO_SAVE_DELAY = 1000;
// ============================================

const API_BASE = '/api';
let storyKey = null;
let originalContent = '';
let vditor = null;
let saveTimeout = null;
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
// DOM EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('storyPreviewContainer');
    if (container) storyKey = container.dataset.storyKey;
    if (!storyKey) { showError('No story specified'); return; }
    loadStoryContent();
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
            originalContent = data.content || '';
            storyData = data;
            
            document.getElementById('storyTitle').textContent = data.title || data.name || 'Untitled';
            document.getElementById('storySeries').textContent = data.series || 'Standalone';
            document.getElementById('storyCreatedDate').textContent = data.createdDate || '-';
            document.getElementById('storyPublishedDate').textContent = data.publishedDate || '-';
            document.getElementById('storyDueDate').textContent = data.publishedDueDate || '-';
            document.getElementById('storyNotes').textContent = data.notes || 'No notes';
            
            const statusEl = document.getElementById('storyStatusBadge');
            let statusClass = 'status-draft';
            if (data.status === 'Published') statusClass = 'status-published';
            else if (data.status === 'Published Due') statusClass = 'status-published-due';
            else if (data.status === 'Ready') statusClass = 'status-ready';
            else if (data.status === 'Done') statusClass = 'status-done';
            statusEl.className = `status-badge ${statusClass}`;
            statusEl.textContent = data.status || 'Draft';
            
            if (data.publishedDueDate) {
                document.getElementById('storyDueBadge').style.display = 'inline-block';
                document.getElementById('storyDueBadge').textContent = `⏰ ${data.publishedDueDate}`;
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
        showError('Error: ' + error.message);
        createFallbackEditor('');
    } finally {
        hideLoading();
    }
}

// ============================================
// VDITOR INITIALIZATION
// ============================================

function initVditor(content) {
    if (typeof Vditor === 'undefined') { createFallbackEditor(content); return; }
    
    try {
        vditor = new Vditor('vditor-editor', {
            height: Math.max(window.innerHeight - 420, 500),
            mode: 'ir',
            theme: 'classic',
            icon: 'material',
            value: content || '',
            toolbar: ['emoji', 'headings', 'bold', 'italic', 'strike', '|', 'list', 'ordered-list', '|', 'table', 'link', 'image', '|', 'code', 'inline-code', '|', 'undo', 'redo', '|', 'export', 'fullscreen', 'outline'],
            cache: { enable: false },
            preview: { mode: 'both', theme: { current: 'light' }, markdown: { mermaid: true } },
            after: () => {
                console.log('Vditor initialized');
                addExportDiagramsButton();
                
                if (AUTO_SAVE_ENABLED) {
                    console.log(`✅ Auto-save enabled`);
                }
            },
            input: () => {
                if (AUTO_SAVE_ENABLED) {
                    if (saveTimeout) clearTimeout(saveTimeout);
                    saveTimeout = setTimeout(() => autoSave(), AUTO_SAVE_DELAY);
                }
                setTimeout(() => updateButtonCount(), 2000);
            }
        });
    } catch (error) {
        createFallbackEditor(content);
    }
}

function createFallbackEditor(content) {
    const container = document.getElementById('vditor-editor');
    if (!container) return;
    container.innerHTML = `<textarea id="fallback-editor" style="width:100%; min-height:500px; padding:10px; font-family:monospace;">${escapeHtml(content || '')}</textarea>`;
    const textarea = document.getElementById('fallback-editor');
    if (textarea) {
        textarea.addEventListener('input', () => {
            if (AUTO_SAVE_ENABLED) {
                if (saveTimeout) clearTimeout(saveTimeout);
                saveTimeout = setTimeout(async () => {
                    if (textarea.value !== originalContent) await saveContent(textarea.value);
                }, AUTO_SAVE_DELAY);
            }
        });
    }
}

// ============================================
// EXPORT DIAGRAMS BUTTON (Individual Save)
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
    panel.innerHTML = `<button id="export-diagrams-btn" style="background: transparent; border: none; color: white; padding: 10px 20px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">📸 Scanning...</button>`;
    document.body.appendChild(panel);
    
    document.getElementById('export-diagrams-btn').onclick = () => showExportMenu();
    updateButtonCount();
    setInterval(() => updateButtonCount(), 5000);
}

function updateButtonCount() {
    const content = vditor ? vditor.getValue() : originalContent;
    if (!content) return 0;
    
    const mermaidCount = countMermaidBlocks(content);
    const tableCount = countMarkdownTables(content);
    const total = mermaidCount + tableCount;
    
    const btn = document.getElementById('export-diagrams-btn');
    if (btn) {
        if (total === 0) {
            btn.innerHTML = `📸 No diagrams/tables found`;
        } else {
            btn.innerHTML = `📸 Export (${total})`;
        }
    }
    return total;
}

function countMermaidBlocks(content) {
    const regex = /```mermaid\n[\s\S]*?```/g;
    const matches = content.match(regex);
    return matches ? matches.length : 0;
}

function countMarkdownTables(content) {
    let count = 0;
    const lines = content.split('\n');
    let inTable = false;
    let hasSeparator = false;
    
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes('|') && !line.trim().startsWith('```')) {
            if (!inTable) {
                inTable = true;
                hasSeparator = false;
            }
            if (line.includes('|-') || line.includes('-|')) {
                hasSeparator = true;
            }
        } else {
            if (inTable && hasSeparator) {
                count++;
            }
            inTable = false;
            hasSeparator = false;
        }
    }
    return count;
}

function showExportMenu() {
    const content = vditor ? vditor.getValue() : originalContent;
    const mermaidCount = countMermaidBlocks(content);
    const tableCount = countMarkdownTables(content);
    
    if (mermaidCount === 0 && tableCount === 0) {
        showToast('No diagrams or tables found in the content', 'error');
        return;
    }
    
    const existingMenu = document.getElementById('export-menu');
    if (existingMenu) existingMenu.remove();
    
    const menu = document.createElement('div');
    menu.id = 'export-menu';
    menu.style.cssText = `
        position: fixed; bottom: 80px; right: 20px; background: white; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25); z-index: 10000; min-width: 280px;
        max-height: auto;
        overflow-y: auto;
    `;
    
    const header = document.createElement('div');
    header.style.cssText = 'padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #eee; font-weight: bold;';
    header.innerHTML = `📸 Export Options`;
    menu.appendChild(header);
    
    // Individual Save Options
    const individualHeader = document.createElement('div');
    individualHeader.style.cssText = 'padding: 8px 16px; background: #e3f2fd; font-weight: bold; font-size: 12px;';
    individualHeader.innerHTML = '💾 Individual Save (Downloads locally)';
    menu.appendChild(individualHeader);
    
    if (mermaidCount > 0) {
        const mermaidItem = document.createElement('div');
        mermaidItem.style.cssText = 'padding: 8px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee;';
        mermaidItem.innerHTML = `<span>📊 Diagrams (${mermaidCount})</span>
            <button id="save-diagrams-btn" class="btn btn-sm btn-success" style="padding: 2px 12px;">Save All Diagrams</button>`;
        menu.appendChild(mermaidItem);
        
        document.getElementById('save-diagrams-btn').onclick = async () => {
            menu.remove();
            await saveAllDiagrams();
        };
    }
    
    if (tableCount > 0) {
        const tableItem = document.createElement('div');
        tableItem.style.cssText = 'padding: 8px 16px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #eee;';
        tableItem.innerHTML = `<span>📋 Tables (${tableCount})</span>
            <button id="save-tables-btn" class="btn btn-sm btn-success" style="padding: 2px 12px;">Save All Tables</button>`;
        menu.appendChild(tableItem);
        
        document.getElementById('save-tables-btn').onclick = async () => {
            menu.remove();
            await saveAllTables();
        };
    }
    
    // Separator
    const separator = document.createElement('div');
    separator.style.cssText = 'height: 1px; background: #dee2e6; margin: 8px 0;';
    menu.appendChild(separator);
    
    // Build Option (Server-side rendering)
    const buildHeader = document.createElement('div');
    buildHeader.style.cssText = 'padding: 8px 16px; background: #fff3e0; font-weight: bold; font-size: 12px;';
    buildHeader.innerHTML = '🚀 Server-Side Build (Creates folders & files)';
    menu.appendChild(buildHeader);
    
    const buildItem = document.createElement('div');
    buildItem.style.cssText = 'padding: 12px 16px; background: #e8f5e9; cursor: pointer; border-radius: 8px; margin: 8px;';
    buildItem.innerHTML = '<strong>📦 Build Story</strong><br><small style="color: #666;">Creates folder, renders diagrams/tables as PNG via Python backend, saves new .md file</small>';
    buildItem.onclick = async () => {
        menu.remove();
        await buildStory();
    };
    menu.appendChild(buildItem);
    
    const closeBtn = document.createElement('div');
    closeBtn.style.cssText = 'padding: 8px 16px; text-align: center; background: #f8f9fa; cursor: pointer; color: #6c757d; font-size: 12px; margin-top: 8px; border-radius: 8px;';
    closeBtn.textContent = 'Close';
    closeBtn.onclick = () => menu.remove();
    menu.appendChild(closeBtn);
    
    document.body.appendChild(menu);
    
    setTimeout(() => {
        const handler = (e) => {
            if (!menu.contains(e.target) && e.target.id !== 'export-diagrams-btn') {
                menu.remove();
                document.removeEventListener('click', handler);
            }
        };
        document.addEventListener('click', handler);
    }, 100);
}

// ============================================
// INDIVIDUAL SAVE FUNCTIONS (Client-side)
// ============================================

async function saveAllDiagrams() {
    const previewArea = document.querySelector('.vditor-preview');
    if (!previewArea) {
        showToast('Preview area not found', 'error');
        return;
    }
    
    const svgs = previewArea.querySelectorAll('svg');
    if (svgs.length === 0) {
        showToast('No diagrams found in preview', 'error');
        return;
    }
    
    showLoading();
    let successCount = 0;
    
    for (let i = 0; i < svgs.length; i++) {
        const blob = await captureSvgAsPNG(svgs[i]);
        if (blob && blob.size > 100) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `diagram-${String(i + 1).padStart(2, '0')}.png`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 100);
            successCount++;
        }
        await new Promise(r => setTimeout(r, 300));
    }
    
    hideLoading();
    showToast(`✅ Saved ${successCount} of ${svgs.length} diagrams`, 'success');
}

async function saveAllTables() {
    const previewArea = document.querySelector('.vditor-preview');
    if (!previewArea) {
        showToast('Preview area not found', 'error');
        return;
    }
    
    const tables = previewArea.querySelectorAll('table');
    if (tables.length === 0) {
        showToast('No tables found in preview', 'error');
        return;
    }
    
    showLoading();
    let successCount = 0;
    
    for (let i = 0; i < tables.length; i++) {
        const blob = await captureTableAsPNG(tables[i]);
        if (blob && blob.size > 100) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `table-${String(i + 1).padStart(2, '0')}.png`;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 100);
            successCount++;
        }
        await new Promise(r => setTimeout(r, 300));
    }
    
    hideLoading();
    showToast(`✅ Saved ${successCount} of ${tables.length} tables`, 'success');
}

async function captureSvgAsPNG(svgElement) {
    return new Promise((resolve) => {
        try {
            let width = svgElement.clientWidth || 800;
            let height = svgElement.clientHeight || 600;
            if (width <= 0) width = 800;
            if (height <= 0) height = 600;
            
            const clonedSvg = svgElement.cloneNode(true);
            clonedSvg.setAttribute('width', width);
            clonedSvg.setAttribute('height', height);
            
            const serializer = new XMLSerializer();
            const svgString = serializer.serializeToString(clonedSvg);
            
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, width, height);
            
            const img = new Image();
            const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            
            img.onload = () => {
                ctx.drawImage(img, 0, 0, width, height);
                URL.revokeObjectURL(url);
                canvas.toBlob(resolve, 'image/png');
            };
            img.onerror = () => {
                URL.revokeObjectURL(url);
                resolve(null);
            };
            img.src = url;
        } catch (error) {
            console.error('SVG capture error:', error);
            resolve(null);
        }
    });
}

async function captureTableAsPNG(tableElement) {
    return new Promise((resolve) => {
        try {
            if (typeof html2canvas !== 'undefined') {
                const originalBg = tableElement.style.backgroundColor;
                tableElement.style.backgroundColor = '#ffffff';
                
                html2canvas(tableElement, {
                    scale: 2,
                    backgroundColor: '#ffffff',
                    logging: false
                }).then(canvas => {
                    tableElement.style.backgroundColor = originalBg;
                    canvas.toBlob(resolve, 'image/png');
                }).catch(() => {
                    tableElement.style.backgroundColor = originalBg;
                    resolve(null);
                });
            } else {
                resolve(null);
            }
        } catch (error) {
            console.error('Table capture error:', error);
            resolve(null);
        }
    });
}

// ============================================
// BUILD STORY FUNCTION - Calls Python Backend
// ============================================

async function buildStory() {
    if (!storyData) {
        showToast('Story data not loaded', 'error');
        return;
    }
    
    const storyName = storyData.title || storyData.name || 'untitled';
    const safeStoryName = sanitizeFileName(storyName);
    const content = vditor ? await vditor.getValue() : originalContent;
    
    const mermaidCount = countMermaidBlocks(content);
    const tableCount = countMarkdownTables(content);
    
    if (mermaidCount === 0 && tableCount === 0) {
        showToast('No diagrams or tables found in the content', 'error');
        return;
    }
    
    if (!confirm(`Build story "${storyName}"?\n\nFound:\n- ${mermaidCount} Mermaid diagrams\n- ${tableCount} Tables\n\nThis will:\n1. Send content to Python backend\n2. Render diagrams and tables as PNG\n3. Create folder at same level as original story\n4. Save images in "images" subfolder\n5. Create new .md file with image references\n\nContinue?`)) {
        return;
    }
    
    showLoading();
    
    try {
        const formData = new FormData();
        formData.append('storyKey', storyKey);
        formData.append('storyName', safeStoryName);
        formData.append('content', content);
        
        console.log('Calling Python backend to build story...');
        
        const response = await fetch(`${API_BASE}/stories/build-export-python`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        console.log('Backend response:', result);
        
        if (result.success) {
            showToast(
                `✅ Build complete!\n\nDiagrams: ${result.diagrams || 0}\nTables: ${result.tables || 0}\nImages saved: ${result.imagesSaved}\n\nFolder: ${result.folderPath}`, 
                'success'
            );
            
            if (result.mdContent) {
                downloadMarkdownFile(result.mdContent, `${safeStoryName}.md`);
            }
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
    const blob = new Blob([content], { type: 'text/markdown' });
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

// ============================================
// AUTO-SAVE & SAVE FUNCTIONS
// ============================================

async function autoSave() {
    if (!AUTO_SAVE_ENABLED) return;
    if (!vditor) return;
    const current = await vditor.getValue();
    if (current !== originalContent) {
        console.log('Auto-saving...');
        await saveContent(current);
    }
}

async function saveContent(content) {
    try {
        const res = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`, {
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.success) { 
            originalContent = content; 
        }
    } catch(e) { console.error(e); }
}

async function saveStory() {
    let current = vditor ? await vditor.getValue() : document.getElementById('fallback-editor')?.value;
    if (!current) return;
    if (current === originalContent) { showToast('No changes', 'info'); return; }
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`, {
            method: 'PUT', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ content: current })
        });
        const data = await res.json();
        if (data.success) { 
            originalContent = current; 
            showToast('Saved!', 'success'); 
        } else {
            showToast('Error: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch(e) { 
        console.error('Save error:', e);
        showToast('Error: ' + e.message, 'error'); 
    } finally { 
        hideLoading(); 
    }
}

// ============================================
// EXPORT FUNCTIONS
// ============================================

async function exportAsHTML() {
    let content = vditor ? await vditor.getHTML() : '';
    if (!content) return;
    const fullHtml = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${escapeHtml(document.getElementById('storyTitle').textContent)}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"><\/script>
    <script>mermaid.initialize({startOnLoad:true});<\/script></head><body>${content}</body></html>`;
    const blob = new Blob([fullHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${document.getElementById('storyTitle').textContent.replace(/[^a-z0-9]/gi, '_')}.html`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
    showToast('HTML exported', 'success');
}

function copyMarkdown() {
    if (vditor) {
        vditor.getValue().then(content => navigator.clipboard.writeText(content).then(() => showToast('Copied!', 'success')));
    }
}

function toggleVditorMode() {
    if (!vditor) return;
    currentMode = (currentMode + 1) % 3;
    if (currentMode === 0) { vditor.setMode('ir'); showToast('WYSIWYG Mode', 'info'); }
    else if (currentMode === 1) { vditor.setMode('sv'); showToast('Split View', 'info'); }
    else { vditor.setPreviewMode(true); showToast('Preview', 'info'); }
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
    navigator.clipboard.writeText(title).then(() => {
        const el = document.getElementById('storyTitle');
        const orig = el.innerHTML;
        el.innerHTML = '✅ Copied!';
        setTimeout(() => el.innerHTML = orig, 1500);
    });
}

// ============================================
// UI HELPER FUNCTIONS
// ============================================

function showLoading() { 
    const el = document.getElementById('loadingOverlay'); 
    if (el) el.style.display = 'flex'; 
}

function hideLoading() { 
    const el = document.getElementById('loadingOverlay'); 
    if (el) el.style.display = 'none'; 
}

function showToast(msg, type) {
    // Create toast element
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

function showError(msg) { 
    showToast('❌ ' + msg, 'error'); 
}

function escapeHtml(t) { 
    if (!t) return ''; 
    return t.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m])); 
}

// ============================================
// GLOBAL EXPORTS
// ============================================

window.saveStory = saveStory;
window.copyTitleToClipboard = copyTitleToClipboard;
window.toggleDetails = toggleDetails;
window.exportAsHTML = exportAsHTML;
window.copyMarkdown = copyMarkdown;
window.toggleVditorMode = toggleVditorMode;
window.buildStory = buildStory;
window.saveAllDiagrams = saveAllDiagrams;
window.saveAllTables = saveAllTables;