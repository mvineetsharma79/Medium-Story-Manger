/**
 * ai-content.js - AI Content Lab Module (NON-BLOCKING PROGRESS + STREAMING)
 * Three separate prompts for LinkedIn, YouTube, SlideShare
 */

// ============================================
// CONFIGURATION - DEEPSEEK (RELIABLE)
// ============================================

const OPENROUTER_API_KEY = "sk-a7ea1ead7c8249a58ee3f585a7ca133c";
const OPENROUTER_URL = "https://api.deepseek.com/v1/chat/completions";
const DEFAULT_MODEL = "deepseek-v4-flash";

// ============================================
// PROMPT CONSTANTS - FULL CONTEXT
// ============================================

const PROMPT_LINKEDIN = `Create hook optimized post for LinkedIn post mentioning "{{STORY_NAME}}" story at "{{MEDIUM_URL}}" as read here

Mention Medium at "https://mvineetsharma.medium.com/" and LinkedIn at "www.linkedin.com/in/vineet-sharma-architect/"

The context below:

\`\`\`
{{MARKUP}}
\`\`\`

Generate a professional, engaging LinkedIn post with appropriate line breaks and hashtags.`;

const PROMPT_YOUTUBE = `Create hook optimized description for YouTube video mentioning "{{STORY_NAME}}" story at "{{MEDIUM_URL}}" as read here

Mention Medium at "https://mvineetsharma.medium.com/" and LinkedIn at "www.linkedin.com/in/vineet-sharma-architect/"

The context below:

\`\`\`
{{MARKUP}}
\`\`\`

Generate a YouTube description and a call to subscribe.`;

const PROMPT_SLIDESHARE = `Create hook optimized description for SlideShare mentioning "{{STORY_NAME}}" story at "{{MEDIUM_URL}}" as read here

Mention Medium at "https://mvineetsharma.medium.com/" and LinkedIn at "www.linkedin.com/in/vineet-sharma-architect/"

The context below:

\`\`\`
{{MARKUP}}
\`\`\`

Generate a SlideShare description and a call to subscribe.`;

// System prompts
const SYSTEM_PROMPT_LINKEDIN = `You are a LinkedIn expert. Write a short post (1000-2000 words). Use line breaks. End with 3 hashtags.`;
const SYSTEM_PROMPT_YOUTUBE = `You are a YouTube publisher. Write a short post (500-1000 words). Use line breaks. End with 3 hashtags.`;
const SYSTEM_PROMPT_SLIDESHARE = `You are a presentation publisher. Use line breaks. End with 3 hashtags.`;

// ============================================
// AI CONTENT MODULE - NON-BLOCKING PROGRESS
// ============================================

(function() {
    'use strict';

    let vditorInstance = null;
    let currentStoryData = null;
    let aiVditor = null;
    let promptCache = {};
    let currentAbortController = null;
    let isGenerating = false;
    let progressInterval = null;
    let progressStartTime = 0;

    // ============================================
    // PROGRESS BAR COMPONENT (NON-BLOCKING)
    // ============================================
    
    function createProgressIndicator() {
        // Remove existing if any
        var existing = document.getElementById('aiProgressContainer');
        if (existing) existing.remove();
        
        var container = document.createElement('div');
        container.id = 'aiProgressContainer';
        container.style.cssText = 'position: fixed; bottom: 30px; right: 30px; z-index: 10001; min-width: 280px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.2); overflow: hidden; font-family: system-ui, -apple-system, sans-serif;';
        
        container.innerHTML = `
            <div style="padding: 12px 16px; background: #0d6efd; color: white; display: flex; justify-content: space-between; align-items: center;">
                <span><i class="bi bi-robot"></i> <strong>AI Generating...</strong></span>
                <button id="aiCancelBtn" style="background: none; border: none; color: white; cursor: pointer; font-size: 18px;">&times;</button>
            </div>
            <div style="padding: 12px 16px;">
                <div style="margin-bottom: 8px;">
                    <span id="aiProgressStatus" style="font-size: 13px; color: #666;">Connecting to DeepSeek...</span>
                </div>
                <div style="background: #e9ecef; border-radius: 10px; overflow: hidden; height: 8px;">
                    <div id="aiProgressBar" style="width: 0%; height: 100%; background: linear-gradient(90deg, #0d6efd, #0dcaf0); transition: width 0.3s ease;"></div>
                </div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between;">
                    <span id="aiProgressDetails" style="font-size: 11px; color: #999;">Preparing...</span>
                    <span id="aiProgressTimer" style="font-size: 11px; color: #999;">0s</span>
                </div>
                <div id="aiStreamPreview" style="margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 8px; font-size: 12px; color: #666; max-height: 100px; overflow-y: auto; display: none;">
                    <small><i class="bi bi-chat-dots"></i> <span id="aiStreamPreviewText">Waiting for response...</span></small>
                </div>
            </div>
        `;
        
        document.body.appendChild(container);
        
        // Cancel button handler
        document.getElementById('aiCancelBtn').onclick = function() {
            if (currentAbortController) {
                currentAbortController.abort();
                showToast('Generation cancelled', false);
                hideProgressIndicator();
                isGenerating = false;
                if (progressInterval) clearInterval(progressInterval);
            }
        };
        
        return container;
    }
    
    function updateProgress(status, percent, details) {
        var statusEl = document.getElementById('aiProgressStatus');
        var barEl = document.getElementById('aiProgressBar');
        var detailsEl = document.getElementById('aiProgressDetails');
        
        if (statusEl) statusEl.textContent = status;
        if (barEl && percent !== undefined) barEl.style.width = percent + '%';
        if (detailsEl && details) detailsEl.textContent = details;
        
        // Update timer
        if (progressStartTime > 0) {
            var timerEl = document.getElementById('aiProgressTimer');
            if (timerEl) {
                var elapsed = Math.floor((Date.now() - progressStartTime) / 1000);
                timerEl.textContent = elapsed + 's';
            }
        }
    }
    
    function updateStreamPreview(text) {
        var previewContainer = document.getElementById('aiStreamPreview');
        var previewText = document.getElementById('aiStreamPreviewText');
        
        if (previewContainer && previewText) {
            previewContainer.style.display = 'block';
            var truncated = text.length > 200 ? text.substring(0, 200) + '...' : text;
            previewText.textContent = truncated;
            previewContainer.scrollTop = previewContainer.scrollHeight;
        }
    }
    
    function hideProgressIndicator() {
        var container = document.getElementById('aiProgressContainer');
        if (container) {
            container.style.opacity = '0';
            setTimeout(function() {
                if (container && container.parentNode) container.parentNode.removeChild(container);
            }, 300);
        }
        if (progressInterval) clearInterval(progressInterval);
        progressInterval = null;
    }

    function showToast(msg, isError) {
        var toastDiv = document.createElement('div');
        toastDiv.className = 'toast-custom';
        toastDiv.textContent = msg;
        if (isError) toastDiv.style.background = "#dc3545";
        document.body.appendChild(toastDiv);
        setTimeout(function() { toastDiv.remove(); }, 3000);
    }

    async function getStoryData() {
        if (window.storyData) return window.storyData;
        var pathParts = window.location.pathname.split('/');
        var storyKey = pathParts[pathParts.length - 1];
        if (!storyKey || storyKey === 'story-preview') return null;
        try {
            var res = await fetch('/api/stories/content/' + encodeURIComponent(storyKey));
            if (res.ok) {
                var data = await res.json();
                window.storyData = data;
                return data;
            }
        } catch(e) { console.warn(e); }
        return null;
    }

    async function getMarkup() {
        if (window.vditorInstance && typeof window.vditorInstance.getValue === 'function') {
            return await window.vditorInstance.getValue();
        }
        var editorDiv = document.getElementById('vditor-editor');
        if (editorDiv) {
            var textarea = editorDiv.querySelector('textarea');
            if (textarea) return textarea.value;
        }
        return '';
    }

    async function buildPrompt(template, platform) {
        var markup = await getMarkup();
        var markupHash = markup.length + '_' + (markup.substring(0, 200) || '');
        var cacheKey = platform + '_' + markupHash;
        
        if (promptCache[cacheKey]) {
            return promptCache[cacheKey];
        }
        
        if (!currentStoryData) {
            currentStoryData = await getStoryData();
        }
        var name = (currentStoryData && (currentStoryData.title || currentStoryData.name)) || "this story";
        var url = (currentStoryData && currentStoryData.medium_url) || "$";
        
        var prompt = template
            .replace(/{{STORY_NAME}}/g, name)
            .replace(/{{MEDIUM_URL}}/g, url)
            .replace(/{{MARKUP}}/g, markup);
        
        promptCache[cacheKey] = prompt;
        return prompt;
    }

    async function updatePromptArea(platform) {
        var promptArea = document.getElementById('aiPromptArea');
        if (!promptArea) return;
        var prompt = "";
        var systemPrompt = "";
        
        if (platform === 'linkedin') {
            prompt = await buildPrompt(PROMPT_LINKEDIN, 'linkedin');
            systemPrompt = SYSTEM_PROMPT_LINKEDIN;
        } else if (platform === 'youtube') {
            prompt = await buildPrompt(PROMPT_YOUTUBE, 'youtube');
            systemPrompt = SYSTEM_PROMPT_YOUTUBE;
        } else if (platform === 'slideshare') {
            prompt = await buildPrompt(PROMPT_SLIDESHARE, 'slideshare');
            systemPrompt = SYSTEM_PROMPT_SLIDESHARE;
        }
        
        promptArea.value = prompt;
        promptArea.dataset.systemPrompt = systemPrompt;
        promptArea.removeAttribute('readonly');
        showToast('✅ ' + platform.toUpperCase() + ' prompt ready', false);
    }

    // ============================================
    // STREAMING API CALL WITH PROGRESS UPDATES
    // ============================================
    async function callDeepSeekStream(systemPrompt, userPrompt) {
        if (currentAbortController) {
            currentAbortController.abort();
        }
        currentAbortController = new AbortController();
        isGenerating = true;
        progressStartTime = Date.now();
        
        // Show progress indicator
        createProgressIndicator();
        updateProgress('Connecting to DeepSeek API...', 5, 'Initializing connection');
        
        // Clear and prepare Vditor for streaming
        if (aiVditor) {
            aiVditor.setValue('');
        } else {
            initAiResponseVditor('');
        }
        
        // Animated progress simulation while waiting
        var simulatedProgress = 5;
        progressInterval = setInterval(function() {
            if (isGenerating && simulatedProgress < 90) {
                simulatedProgress += Math.random() * 3;
                if (simulatedProgress > 90) simulatedProgress = 90;
                updateProgress('Generating content...', simulatedProgress, 'Streaming response');
            }
        }, 500);
        
        var fullContent = '';
        var chunksReceived = 0;
        var startTime = Date.now();
        
        try {
            updateProgress('Sending request to DeepSeek...', 10, 'Processing your prompt');
            
            var response = await fetch(OPENROUTER_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + OPENROUTER_API_KEY,
                    'HTTP-Referer': window.location.origin,
                    'X-Title': 'Story AI Studio'
                },
                body: JSON.stringify({
                    model: DEFAULT_MODEL,
                    messages: [
                        { role: "system", content: systemPrompt },
                        { role: "user", content: userPrompt }
                    ],
                    temperature: 0.7,
                    max_tokens: 2000,
                    top_p: 0.9,
                    stream: true
                }),
                signal: currentAbortController.signal
            });
            
            if (!response.ok) {
                var errData = await response.json().catch(function() { return {}; });
                throw new Error(errData.error?.message || 'API error: ' + response.status);
            }
            
            updateProgress('Receiving streaming response...', 20, 'First tokens arriving');
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(data);
                            const content = parsed.choices?.[0]?.delta?.content;
                            if (content) {
                                fullContent += content;
                                chunksReceived++;
                                
                                // Update Vditor in real-time
                                if (aiVditor) {
                                    aiVditor.setValue(fullContent);
                                }
                                
                                // Update preview
                                updateStreamPreview(fullContent);
                                
                                // Update progress based on chunks and time
                                var elapsed = (Date.now() - startTime) / 1000;
                                var progressPercent = Math.min(95, 20 + (chunksReceived * 2));
                                if (progressPercent > 95) progressPercent = 95;
                                
                                updateProgress('Streaming... (' + chunksReceived + ' chunks)', progressPercent, 'Received ' + fullContent.length + ' characters');
                            }
                        } catch (e) {
                            // Skip invalid JSON
                        }
                    }
                }
            }
            
            var elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            console.log('DeepSeek streaming complete: ' + elapsed + 's, ' + fullContent.length + ' chars');
            
            updateProgress('Complete!', 100, 'Generation finished in ' + elapsed + 's');
            
            // Brief pause to show 100% then hide
            setTimeout(function() {
                hideProgressIndicator();
            }, 1500);
            
            return fullContent;
        } catch(err) {
            if (err.name !== 'AbortError') {
                console.error('DeepSeek error:', err);
                updateProgress('Error: ' + err.message, 0, 'Generation failed');
                showToast('Error: ' + err.message, true);
                setTimeout(function() { hideProgressIndicator(); }, 3000);
            } else {
                updateProgress('Cancelled', 0, 'Generation cancelled by user');
                setTimeout(function() { hideProgressIndicator(); }, 1000);
            }
            return null;
        } finally {
            if (progressInterval) clearInterval(progressInterval);
            isGenerating = false;
            currentAbortController = null;
        }
    }

    // Fallback non-streaming call
    async function callDeepSeekNonStreaming(systemPrompt, userPrompt) {
        createProgressIndicator();
        updateProgress('Using non-streaming mode...', 30, 'Processing request');
        
        if (currentAbortController) {
            currentAbortController.abort();
        }
        currentAbortController = new AbortController();
        var startTime = Date.now();
        
        // Simulate progress
        var simulatedProgress = 30;
        progressInterval = setInterval(function() {
            if (simulatedProgress < 90) {
                simulatedProgress += 5;
                updateProgress('Processing...', simulatedProgress, 'Waiting for response');
            }
        }, 800);
        
        try {
            var response = await fetch(OPENROUTER_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + OPENROUTER_API_KEY,
                    'HTTP-Referer': window.location.origin,
                    'X-Title': 'Story AI Studio'
                },
                body: JSON.stringify({
                    model: DEFAULT_MODEL,
                    messages: [
                        { role: "system", content: systemPrompt },
                        { role: "user", content: userPrompt }
                    ],
                    temperature: 0.7,
                    max_tokens: 2000,
                    top_p: 0.9,
                    stream: false
                }),
                signal: currentAbortController.signal
            });
            
            var elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            console.log('DeepSeek response time: ' + elapsed + 's');
            
            if (!response.ok) {
                var errData = await response.json().catch(function() { return {}; });
                throw new Error(errData.error?.message || 'API error: ' + response.status);
            }
            var data = await response.json();
            var content = data.choices && data.choices[0] && data.choices[0].message ? data.choices[0].message.content : null;
            
            if (content) {
                updateProgress('Complete!', 100, 'Generation finished in ' + elapsed + 's');
                setTimeout(function() { hideProgressIndicator(); }, 1500);
            }
            
            return content;
        } catch(err) {
            if (err.name !== 'AbortError') {
                console.error('DeepSeek error:', err);
                showToast('Error: ' + err.message, true);
                hideProgressIndicator();
            }
            return null;
        } finally {
            if (progressInterval) clearInterval(progressInterval);
            currentAbortController = null;
        }
    }

    async function handleGenerate() {
        if (isGenerating) {
            showToast('Generation already in progress. Please wait or cancel.', true);
            return;
        }
        
        var promptArea = document.getElementById('aiPromptArea');
        var userPrompt = promptArea.value;
        var systemPrompt = promptArea.dataset.systemPrompt || SYSTEM_PROMPT_LINKEDIN;
        
        if (!userPrompt || userPrompt.trim() === "") {
            showToast("Click LinkedIn, YouTube, or SlideShare first", true);
            return;
        }
        
        var platform = "LinkedIn";
        if (userPrompt.indexOf("YouTube") !== -1) platform = "YouTube";
        else if (userPrompt.indexOf("SlideShare") !== -1) platform = "SlideShare";
        
        // Try streaming first
        var response = await callDeepSeekStream(systemPrompt, userPrompt);
        
        // If streaming fails or returns empty, fall back to non-streaming
        if (!response || response.trim() === '') {
            showToast('Streaming unavailable, using standard mode...', false);
            response = await callDeepSeekNonStreaming(systemPrompt, userPrompt);
        }
        
        if (response && response.trim() !== '') {
            if (!aiVditor) {
                initAiResponseVditor(response);
            }
            showToast('✨ ' + platform + ' content ready!', false);
        } else if (response === null) {
            // Error already shown
        } else {
            showToast('Generation failed. Please try again.', true);
        }
    }

    function initAiResponseVditor(content) {
        var container = document.getElementById('aiResponseVditor');
        if (!container) return;
        if (aiVditor) aiVditor.destroy();
        container.innerHTML = '';
        aiVditor = new Vditor('aiResponseVditor', {
            height: 400,
            mode: 'ir',
            theme: 'classic',
            icon: 'material',
            value: content || '# AI content will appear here\n\n1. Click LinkedIn, YouTube, or SlideShare\n2. Click Generate\n3. Watch progress bar and streaming response\n4. Edit and copy',
            toolbar: ['bold', 'italic', 'strike', '|', 'list', 'ordered-list', '|', 'table', 'link', '|', 'preview', 'fullscreen'],
            cache: { enable: false },
            preview: { mode: 'both', theme: { current: 'light' }, markdown: { mermaid: true } }
        });
    }

    function copyResponse() {
        if (aiVditor) {
            aiVditor.getValue().then(function(content) {
                if (content && content !== '# AI content will appear here' && content.indexOf('failed') === -1 && content.trim() !== '') {
                    navigator.clipboard.writeText(content);
                    showToast("📋 Copied to clipboard!", false);
                } else {
                    showToast("Generate content first", true);
                }
            });
        }
    }

    function clearResponse() {
        if (aiVditor) {
            aiVditor.setValue('');
            showToast("Cleared", false);
        }
    }

    async function updateStoryContext() {
        var noteSpan = document.getElementById('storyContextNote');
        if (!noteSpan) return;
        if (!currentStoryData) currentStoryData = await getStoryData();
        if (currentStoryData) {
            var storyName = currentStoryData.name || currentStoryData.title || "Story";
            var storyUrl = currentStoryData.medium_url || "";
            if (storyUrl) {
                noteSpan.innerHTML = '<i class="bi bi-link-45deg"></i> 📖 <a href="' + storyUrl + '" target="_blank">' + storyName.substring(0, 45) + '...</a>';
            } else {
                noteSpan.innerHTML = '<i class="bi bi-book"></i> 📖 ' + storyName.substring(0, 50);
            }
        }
    }

    function switchTab(tabId) {
        document.querySelectorAll('.tab-pane').forEach(function(pane) {
            pane.classList.remove('active-pane');
        });
        document.getElementById(tabId).classList.add('active-pane');
        document.querySelectorAll('.tab-btn').forEach(function(btn) {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabId) btn.classList.add('active');
        });
        if (tabId === 'ai-tab') updateStoryContext();
    }

    async function init() {
        var checkInterval = setInterval(function() {
            if (window.vditorInstance) {
                vditorInstance = window.vditorInstance;
                console.log('AI Content: Connected to main editor');
                clearInterval(checkInterval);
            }
        }, 500);
        
        currentStoryData = await getStoryData();
        await updateStoryContext();
        initAiResponseVditor();
        
        document.getElementById('linkedinBtn')?.addEventListener('click', function() { updatePromptArea('linkedin'); });
        document.getElementById('youtubeBtn')?.addEventListener('click', function() { updatePromptArea('youtube'); });
        document.getElementById('slideshareBtn')?.addEventListener('click', function() { updatePromptArea('slideshare'); });
        document.getElementById('generateContentBtn')?.addEventListener('click', handleGenerate);
        document.getElementById('copyResponseBtn')?.addEventListener('click', copyResponse);
        document.getElementById('clearResponseBtn')?.addEventListener('click', clearResponse);
        
        document.querySelectorAll('.tab-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                if (this.dataset.tab) switchTab(this.dataset.tab);
            });
        });
        
        setTimeout(function() { updatePromptArea('linkedin'); }, 500);
        console.log('AI Module ready - Non-blocking progress + Streaming');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();