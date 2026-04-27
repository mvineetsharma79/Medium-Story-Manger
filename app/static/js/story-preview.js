// ============================================
// STORY PREVIEW PAGE - Export Diagrams from Preview
// ============================================

// ========== CONFIGURATION CONSTANTS ==========
const AUTO_SAVE_ENABLED = false;  // Set to false to disable auto-save
const AUTO_SAVE_DELAY = 1000;    // Delay in milliseconds (1 second)
// ============================================

const API_BASE = '/api';
let storyKey = null;
let originalContent = '';
let vditor = null;
let saveTimeout = null;
let currentMode = 0;

mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true }
});

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

async function loadStoryContent() {
    showLoading();
    try {
        const response = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`);
        const data = await response.json();
        if (data.success) {
            originalContent = data.content || '';
            
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
        }
    } catch (error) {
        showError('Error: ' + error.message);
        createFallbackEditor('');
    } finally {
        hideLoading();
    }
}

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
                
                // Show auto-save status in console
                if (AUTO_SAVE_ENABLED) {
                    console.log(`✅ Auto-save enabled (${AUTO_SAVE_DELAY}ms delay)`);
                } else {
                    console.log('❌ Auto-save disabled');
                }
            },
            input: () => {
                // Only set up auto-save if enabled
                if (AUTO_SAVE_ENABLED) {
                    if (saveTimeout) clearTimeout(saveTimeout);
                    saveTimeout = setTimeout(() => autoSave(), AUTO_SAVE_DELAY);
                }
                setTimeout(() => updateButtonCount(), 1000);
            }
        });
    } catch (error) {
        createFallbackEditor(content);
    }
}

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
    panel.innerHTML = `<button id="export-diagrams-btn" style="background: transparent; border: none; color: white; padding: 10px 20px; font-weight: bold; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px;">📸 Scanning for diagrams...</button>`;
    document.body.appendChild(panel);
    
    document.getElementById('export-diagrams-btn').onclick = () => showExportMenu();
    updateButtonCount();
    setInterval(() => updateButtonCount(), 3000);
}

function updateButtonCount() {
    const diagrams = findRenderedDiagrams();
    const btn = document.getElementById('export-diagrams-btn');
    if (btn) {
        const count = diagrams.length;
        if (count === 0) {
            btn.innerHTML = `📸 No diagrams found`;
        } else {
            btn.innerHTML = `📸 Save Diagrams (${count})`;
        }
    }
    return diagrams.length;
}

function findRenderedDiagrams() {
    const previewArea = document.querySelector('.vditor-preview');
    if (!previewArea) return [];
    
    const canvases = previewArea.querySelectorAll('canvas');
    const svgs = previewArea.querySelectorAll('svg');
    const mermaidDivs = previewArea.querySelectorAll('.mermaid');
    
    const diagrams = [];
    
    canvases.forEach(canvas => {
        diagrams.push({ type: 'canvas', element: canvas });
    });
    
    svgs.forEach(svg => {
        diagrams.push({ type: 'svg', element: svg });
    });
    
    mermaidDivs.forEach(div => {
        const canvas = div.querySelector('canvas');
        const svg = div.querySelector('svg');
        if (canvas && !diagrams.find(d => d.element === canvas)) {
            diagrams.push({ type: 'canvas', element: canvas });
        }
        if (svg && !diagrams.find(d => d.element === svg)) {
            diagrams.push({ type: 'svg', element: svg });
        }
    });
    
    return diagrams;
}

function showExportMenu() {
    const diagrams = findRenderedDiagrams();
    if (diagrams.length === 0) {
        showToast('No diagrams found in preview. Make sure diagrams are rendered.', 'error');
        return;
    }
    
    const existingMenu = document.getElementById('export-menu');
    if (existingMenu) existingMenu.remove();
    
    const menu = document.createElement('div');
    menu.id = 'export-menu';
    menu.style.cssText = `
        position: fixed; bottom: 80px; right: 20px; background: white; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.25); z-index: 10000; min-width: 280px;
        max-height: 400px; overflow-y: auto; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    `;
    
    const header = document.createElement('div');
    header.style.cssText = 'padding: 12px 16px; background: #f8f9fa; border-bottom: 1px solid #eee; font-weight: bold; position: sticky; top: 0;';
    header.innerHTML = `📸 Save Diagrams (${diagrams.length} found)`;
    menu.appendChild(header);
    
    // Export All button
    const allOption = document.createElement('div');
    allOption.style.cssText = 'padding: 12px 16px; cursor: pointer; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 10px; background: #e8f5e9;';
    allOption.innerHTML = '<span style="font-size: 18px;">📦</span> <div><strong>Save All Diagrams</strong><br><span style="font-size: 11px;">Save all as PNG files</span></div>';
    allOption.onclick = async () => {
        menu.remove();
        await saveAllDiagrams();
    };
    menu.appendChild(allOption);
    
    // Individual diagrams
    diagrams.forEach((diagram, idx) => {
        const item = document.createElement('div');
        item.style.cssText = 'padding: 10px 16px; cursor: pointer; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;';
        item.onmouseenter = () => item.style.background = '#f0f0f0';
        item.onmouseleave = () => item.style.background = 'white';
        
        const label = document.createElement('span');
        label.textContent = `Diagram ${idx + 1} (${diagram.type.toUpperCase()})`;
        label.style.fontSize = '12px';
        
        const pngBtn = document.createElement('button');
        pngBtn.textContent = '📸 Save PNG';
        pngBtn.style.cssText = 'background: #28a745; color: white; border: none; border-radius: 4px; padding: 4px 12px; cursor: pointer; font-size: 11px; font-weight: bold;';
        pngBtn.onclick = async (e) => {
            e.stopPropagation();
            menu.remove();
            await saveDiagramAsPNG(diagram.element, idx);
        };
        
        item.appendChild(label);
        item.appendChild(pngBtn);
        menu.appendChild(item);
    });
    
    const closeBtn = document.createElement('div');
    closeBtn.style.cssText = 'padding: 10px 16px; text-align: center; background: #f8f9fa; cursor: pointer; color: #6c757d; font-size: 13px; border-top: 1px solid #eee;';
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

async function saveDiagramAsPNG(element, index) {
    showLoading();
    try {
        console.log(`Saving diagram ${index + 1} as PNG`);
        
        if (element.tagName === 'svg' || element.tagName === 'SVG') {
            const clonedSvg = element.cloneNode(true);
            clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
            
            let width = element.clientWidth || parseInt(element.getAttribute('width')) || 800;
            let height = element.clientHeight || parseInt(element.getAttribute('height')) || 600;
            if (width <= 0) width = 800;
            if (height <= 0) height = 600;
            clonedSvg.setAttribute('width', width);
            clonedSvg.setAttribute('height', height);
            
            const tempContainer = document.createElement('div');
            tempContainer.style.position = 'absolute';
            tempContainer.style.left = '-9999px';
            tempContainer.style.top = '-9999px';
            tempContainer.appendChild(clonedSvg);
            document.body.appendChild(tempContainer);
            
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, width, height);
            
            const svgString = new XMLSerializer().serializeToString(clonedSvg);
            const img = new Image();
            const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            
            await new Promise((resolve, reject) => {
                img.onload = () => {
                    ctx.drawImage(img, 0, 0, width, height);
                    URL.revokeObjectURL(url);
                    resolve();
                };
                img.onerror = reject;
                img.src = url;
            });
            
            canvas.toBlob((blobData) => {
                if (blobData) {
                    const downloadUrl = URL.createObjectURL(blobData);
                    const link = document.createElement('a');
                    link.href = downloadUrl;
                    link.download = `diagram-${index + 1}.png`;
                    document.body.appendChild(link);
                    link.click();
                    
                    setTimeout(() => {
                        document.body.removeChild(link);
                        URL.revokeObjectURL(downloadUrl);
                    }, 100);
                    
                    showToast(`✅ Diagram ${index + 1} saved!`, 'success');
                }
            }, 'image/png');
            
            document.body.removeChild(tempContainer);
        } 
        else if (element.tagName === 'canvas' || element.tagName === 'CANVAS') {
            element.toBlob((blobData) => {
                if (blobData) {
                    const downloadUrl = URL.createObjectURL(blobData);
                    const link = document.createElement('a');
                    link.href = downloadUrl;
                    link.download = `diagram-${index + 1}.png`;
                    document.body.appendChild(link);
                    link.click();
                    
                    setTimeout(() => {
                        document.body.removeChild(link);
                        URL.revokeObjectURL(downloadUrl);
                    }, 100);
                    
                    showToast(`✅ Diagram ${index + 1} saved!`, 'success');
                }
            }, 'image/png');
        }
        
    } catch (error) {
        console.error('Save error:', error);
        showToast('Failed to save diagram: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function saveAllDiagrams() {
    const diagrams = findRenderedDiagrams();
    if (diagrams.length === 0) {
        showToast('No diagrams found', 'error');
        return;
    }
    
    showLoading();
    let successCount = 0;
    
    for (let i = 0; i < diagrams.length; i++) {
        try {
            await new Promise((resolve) => {
                const element = diagrams[i].element;
                
                if (element.tagName === 'svg' || element.tagName === 'SVG') {
                    const clonedSvg = element.cloneNode(true);
                    clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    
                    let width = element.clientWidth || 800;
                    let height = element.clientHeight || 600;
                    if (width <= 0) width = 800;
                    if (height <= 0) height = 600;
                    clonedSvg.setAttribute('width', width);
                    clonedSvg.setAttribute('height', height);
                    
                    const tempContainer = document.createElement('div');
                    tempContainer.style.position = 'absolute';
                    tempContainer.style.left = '-9999px';
                    tempContainer.style.top = '-9999px';
                    tempContainer.appendChild(clonedSvg);
                    document.body.appendChild(tempContainer);
                    
                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(0, 0, width, height);
                    
                    const svgString = new XMLSerializer().serializeToString(clonedSvg);
                    const img = new Image();
                    const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
                    const url = URL.createObjectURL(blob);
                    
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0, width, height);
                        URL.revokeObjectURL(url);
                        
                        canvas.toBlob((blobData) => {
                            if (blobData) {
                                const downloadUrl = URL.createObjectURL(blobData);
                                const link = document.createElement('a');
                                link.href = downloadUrl;
                                link.download = `diagram-${i + 1}.png`;
                                document.body.appendChild(link);
                                link.click();
                                
                                setTimeout(() => {
                                    document.body.removeChild(link);
                                    URL.revokeObjectURL(downloadUrl);
                                }, 100);
                                
                                successCount++;
                            }
                            document.body.removeChild(tempContainer);
                            resolve();
                        }, 'image/png');
                    };
                    img.onerror = () => {
                        URL.revokeObjectURL(url);
                        document.body.removeChild(tempContainer);
                        resolve();
                    };
                    img.src = url;
                }
                else if (element.tagName === 'canvas' || element.tagName === 'CANVAS') {
                    element.toBlob((blobData) => {
                        if (blobData) {
                            const downloadUrl = URL.createObjectURL(blobData);
                            const link = document.createElement('a');
                            link.href = downloadUrl;
                            link.download = `diagram-${i + 1}.png`;
                            document.body.appendChild(link);
                            link.click();
                            
                            setTimeout(() => {
                                document.body.removeChild(link);
                                URL.revokeObjectURL(downloadUrl);
                            }, 100);
                            
                            successCount++;
                        }
                        resolve();
                    }, 'image/png');
                } else {
                    resolve();
                }
            });
            
            await new Promise(r => setTimeout(r, 500));
        } catch (error) {
            console.error(`Error saving diagram ${i + 1}:`, error);
        }
    }
    
    hideLoading();
    showToast(`✅ Saved ${successCount} of ${diagrams.length} diagrams`, 'success');
    closeMenus();
}

function closeMenus() {
    const menus = document.querySelectorAll('#export-menu');
    menus.forEach(m => m.remove());
}

// ============================================
// AUTO-SAVE FUNCTION (controlled by constant)
// ============================================

async function autoSave() {
    if (!AUTO_SAVE_ENABLED) {
        console.log('Auto-save is disabled');
        return;
    }
    
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
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content })
        });
        const data = await res.json();
        if (data.success) { 
            originalContent = content; 
            showToast('Auto-saved', 'success'); 
        }
    } catch(e) { console.error(e); }
}

// ============================================
// FALLBACK EDITOR & SAVE FUNCTIONS
// ============================================

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

async function saveStory() {
    let current = vditor ? await vditor.getValue() : document.getElementById('fallback-editor')?.value;
    if (!current) return;
    if (current === originalContent) { showToast('No changes', 'info'); return; }
    showLoading();
    try {
        const res = await fetch(`${API_BASE}/stories/content/${encodeURIComponent(storyKey)}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: current })
        });
        const data = await res.json();
        if (data.success) { 
            originalContent = current; 
            showToast('Saved!', 'success'); 
        }
    } catch(e) { showToast('Error: ' + e.message, 'error'); }
    finally { hideLoading(); }
}

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
    setTimeout(() => document.body.removeChild(a), 100);
    URL.revokeObjectURL(url);
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

function showLoading() { const el = document.getElementById('loadingOverlay'); if (el) el.style.display = 'flex'; }
function hideLoading() { const el = document.getElementById('loadingOverlay'); if (el) el.style.display = 'none'; }
function showToast(msg, type) {
    const toast = document.createElement('div'); toast.className = 'toast-custom';
    if (type === 'error') toast.classList.add('error');
    toast.textContent = msg; document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
function showError(msg) { showToast('❌ ' + msg, 'error'); }
function escapeHtml(t) { if (!t) return ''; return t.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m])); }

window.saveStory = saveStory;
window.copyTitleToClipboard = copyTitleToClipboard;
window.toggleDetails = toggleDetails;
window.exportAsHTML = exportAsHTML;
window.copyMarkdown = copyMarkdown;
window.toggleVditorMode = toggleVditorMode;