/**
 * Apex Campus Advisor - Frontend Client Logic
 * Handles interactive RAG chatbot sessions, inspection panels, and knowledge catalog.
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.getElementById('chat-messages');
  const chatForm = document.getElementById('chat-form');
  const userInput = document.getElementById('user-input');
  const topkSelect = document.getElementById('topk-select');
  const btnClearChat = document.getElementById('btn-clear-chat');
  const btnOpenKnowledge = document.getElementById('btn-open-knowledge');
  const btnOpenRagGuide = document.getElementById('btn-open-rag-guide');
  const modalKnowledge = document.getElementById('modal-knowledge');
  const drawerRagGuide = document.getElementById('drawer-rag-guide');
  const btnReloadKb = document.getElementById('btn-reload-kb');
  const knowledgeSummary = document.getElementById('knowledge-summary');
  const knowledgeCategoriesList = document.getElementById('knowledge-categories-list');

  let isSubmitting = false;

  // Auto-resize textarea
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 120) + 'px';
  });

  // Handle Enter to submit (Shift+Enter for newline)
  userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isSubmitting) {
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }
  });

  // Setup suggestion chip clicks
  function bindSuggestionChips() {
    document.querySelectorAll('.chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const promptText = chip.getAttribute('data-prompt');
        if (promptText && !isSubmitting) {
          userInput.value = promptText;
          userInput.style.height = 'auto';
          submitQuery(promptText);
        }
      });
    });
  }
  bindSuggestionChips();

  // Clear chat
  btnClearChat.addEventListener('click', () => {
    if (confirm('Clear the current conversation?')) {
      location.reload();
    }
  });

  // Handle Form Submission
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = userInput.value.trim();
    if (!query || isSubmitting) return;
    submitQuery(query);
  });

  async function submitQuery(query) {
    isSubmitting = true;
    userInput.value = '';
    userInput.style.height = 'auto';
    userInput.disabled = true;

    // 1. Hide welcome card if present
    const welcomeCard = document.getElementById('welcome-card');
    if (welcomeCard) {
      welcomeCard.style.display = 'none';
    }

    // 2. Append User Message
    appendUserMessage(query);

    // 3. Append Bot Loading Indicator
    const loadingId = appendLoadingIndicator();
    scrollToBottom();

    // 4. Send API request
    try {
      const topK = parseInt(topkSelect.value, 10) || 3;
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, top_k: topK })
      });

      const data = await response.json();
      removeLoadingIndicator(loadingId);

      if (response.ok && data.status === 'success') {
        appendBotResponse(data);
      } else {
        appendErrorMessage(data.message || 'Unable to process your request at this time.');
      }
    } catch (err) {
      removeLoadingIndicator(loadingId);
      appendErrorMessage('Network connection error. Is the Flask server running?');
      console.error('Chat error:', err);
    } finally {
      isSubmitting = false;
      userInput.disabled = false;
      userInput.focus();
      scrollToBottom();
    }
  }

  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'msg-row user';
    row.innerHTML = `
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${escapeHtml(text)}</div>
      </div>
      <div class="msg-avatar user">
        <i class="fa-solid fa-user"></i>
      </div>
    `;
    chatMessages.appendChild(row);
  }

  function appendLoadingIndicator() {
    const id = 'loading-' + Date.now();
    const row = document.createElement('div');
    row.className = 'msg-row bot';
    row.id = id;
    row.innerHTML = `
      <div class="msg-avatar bot">
        <i class="fa-solid fa-robot"></i>
      </div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble">
          <div class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
          </div>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
    return id;
  }

  function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorMessage(msg) {
    const row = document.createElement('div');
    row.className = 'msg-row bot';
    row.innerHTML = `
      <div class="msg-avatar bot" style="background: #ef4444;">
        <i class="fa-solid fa-triangle-exclamation"></i>
      </div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble" style="border-color: rgba(239, 68, 68, 0.4);">
          <strong style="color: #fca5a5;">Notice:</strong>
          <p>${escapeHtml(msg)}</p>
        </div>
      </div>
    `;
    chatMessages.appendChild(row);
  }

  function appendBotResponse(data) {
    const row = document.createElement('div');
    row.className = 'msg-row bot';
    const panelId = 'rag-panel-' + Date.now();

    // Render markdown safely
    const formattedHtml = typeof marked !== 'undefined' ? marked.parse(data.answer) : data.answer;

    // Build chunks HTML
    let chunksHtml = '';
    if (data.retrieved_chunks && data.retrieved_chunks.length > 0) {
      chunksHtml = data.retrieved_chunks.map((chunk, idx) => {
        const scorePercent = Math.round(chunk.similarity_score * 100);
        return `
          <div class="rag-chunk-card">
            <div class="rag-chunk-header">
              <span class="rag-chunk-title">[Chunk #${idx + 1}] ${escapeHtml(chunk.title)}</span>
              <span class="rag-similarity-pill">Match: ${scorePercent}%</span>
            </div>
            <p class="rag-chunk-text">${escapeHtml(chunk.content)}</p>
          </div>
        `;
      }).join('');
    } else {
      chunksHtml = '<p style="color: var(--text-dim); font-size: 0.8rem;">No high-confidence chunks matched this query.</p>';
    }

    row.innerHTML = `
      <div class="msg-avatar bot">
        <i class="fa-solid fa-graduation-cap"></i>
      </div>
      <div class="msg-content-wrapper">
        <div class="msg-bubble">${formattedHtml}</div>
        
        <!-- RAG Metadata Bar -->
        <div class="rag-meta-bar">
          <span class="rag-latency-badge" title="Retrieval and Total Processing Time">
            <i class="fa-regular fa-clock"></i> Retrieval: ${data.retrieval_latency_ms}ms • Total: ${data.total_latency_ms}ms
          </span>
          <span class="rag-latency-badge">
            <i class="fa-solid fa-microchip"></i> ${escapeHtml(data.backend)}
          </span>
          <button class="rag-inspect-toggle" data-target="${panelId}">
            <i class="fa-solid fa-magnifying-glass-chart"></i> Inspect RAG Pipeline
          </button>
        </div>

        <!-- Hidden Expandable RAG Inspection Panel -->
        <div id="${panelId}" class="rag-inspector-panel">
          <div class="rag-inspector-title">
            <span><i class="fa-solid fa-layer-group"></i> Retrieved Context Chunks (${data.retrieved_chunks ? data.retrieved_chunks.length : 0})</span>
            <span style="font-size: 0.72rem; color: var(--accent-cyan);">Top-K Vector Ranking</span>
          </div>
          ${chunksHtml}

          <div style="margin-top: 0.8rem;">
            <div style="font-size: 0.76rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.3rem;">
              <i class="fa-solid fa-terminal"></i> Augmented Prompt Sent to Generator:
            </div>
            <div class="rag-prompt-preview">${escapeHtml(data.rag_prompt || '')}</div>
          </div>
        </div>
      </div>
    `;

    chatMessages.appendChild(row);

    // Bind toggle button for this panel
    const toggleBtn = row.querySelector('.rag-inspect-toggle');
    const panelEl = row.querySelector(`#${panelId}`);
    toggleBtn.addEventListener('click', () => {
      const isOpen = panelEl.classList.toggle('open');
      toggleBtn.innerHTML = isOpen
        ? '<i class="fa-solid fa-chevron-up"></i> Hide RAG Details'
        : '<i class="fa-solid fa-magnifying-glass-chart"></i> Inspect RAG Pipeline';
      scrollToBottom();
    });
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Modals & Drawer Management
  function setupModalsAndDrawers() {
    // Open Knowledge Modal
    btnOpenKnowledge.addEventListener('click', () => {
      loadKnowledgeCatalog();
      modalKnowledge.classList.add('open');
      modalKnowledge.setAttribute('aria-hidden', 'false');
    });

    // Open RAG Guide Drawer
    btnOpenRagGuide.addEventListener('click', () => {
      drawerRagGuide.classList.add('open');
      drawerRagGuide.setAttribute('aria-hidden', 'false');
    });

    // Close buttons
    document.querySelectorAll('[data-close]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-close');
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
          targetEl.classList.remove('open');
          targetEl.setAttribute('aria-hidden', 'true');
        }
      });
    });

    // Close on backdrop click
    [modalKnowledge, drawerRagGuide].forEach((container) => {
      container.addEventListener('click', (e) => {
        if (e.target === container) {
          container.classList.remove('open');
          container.setAttribute('aria-hidden', 'true');
        }
      });
    });

    // Reload Knowledge Base
    btnReloadKb.addEventListener('click', async () => {
      btnReloadKb.disabled = true;
      btnReloadKb.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Re-indexing...';
      try {
        const res = await fetch('/api/reload', { method: 'POST' });
        const result = await res.json();
        alert(result.message);
        loadKnowledgeCatalog();
      } catch (e) {
        alert('Failed to reload knowledge index: ' + e);
      } finally {
        btnReloadKb.disabled = false;
        btnReloadKb.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Re-index Documents';
      }
    });
  }

  async function loadKnowledgeCatalog() {
    try {
      knowledgeSummary.textContent = 'Fetching current document catalog...';
      const res = await fetch('/api/topics');
      const data = await res.json();

      knowledgeSummary.textContent = `${data.total_documents} Verified Document Chunks • ${data.vocabulary_size} TF-IDF Vocabulary Terms`;

      knowledgeCategoriesList.innerHTML = '';
      for (const [category, topics] of Object.entries(data.categories)) {
        const groupEl = document.createElement('div');
        groupEl.className = 'category-group';
        
        let topicsHtml = topics.map((t) => `
          <div class="topic-item">
            <span class="topic-name">${escapeHtml(t.title)}</span>
            <button class="topic-ask-btn" data-title="${escapeHtml(t.title)}">Ask About This</button>
          </div>
        `).join('');

        groupEl.innerHTML = `
          <div class="category-title">
            <i class="fa-regular fa-folder-open"></i> ${escapeHtml(category)} (${topics.length})
          </div>
          ${topicsHtml}
        `;
        knowledgeCategoriesList.appendChild(groupEl);
      }

      // Bind 'Ask About This' inside modal
      knowledgeCategoriesList.querySelectorAll('.topic-ask-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const title = btn.getAttribute('data-title');
          modalKnowledge.classList.remove('open');
          const prompt = `Tell me all details regarding ${title}`;
          userInput.value = prompt;
          submitQuery(prompt);
        });
      });
    } catch (err) {
      knowledgeSummary.textContent = 'Error loading knowledge base.';
      console.error(err);
    }
  }

  setupModalsAndDrawers();
});
