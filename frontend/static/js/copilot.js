/**
 * SemPKM Copilot Chat Module
 *
 * Lazy-loaded ES module that provides a chat interface for the AI Copilot
 * bottom panel. Streams LLM responses via SSE, renders markdown, converts
 * IRI references to clickable object pills, and handles SPARQL approval flow.
 *
 * Loaded on first AI COPILOT tab activation via dynamic import() in workspace.js.
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
var _messageThread = [];
var _isStreaming = false;
var _abortController = null;
var _activeObjectIri = null;
var _currentConversationId = null;
var _conversations = [];
var _activePersonaId = null;
var _personas = [];

// DOM refs (set in initCopilotChat)
var _messagesEl = null;
var _inputEl = null;
var _sendBtn = null;

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

export function initCopilotChat() {
  _messagesEl = document.getElementById('copilot-messages');
  _inputEl = document.getElementById('copilot-input');
  _sendBtn = document.getElementById('copilot-send-btn');

  if (!_messagesEl || !_inputEl || !_sendBtn) {
    console.error('copilot: missing DOM elements');
    return;
  }

  // Wire send button
  _sendBtn.addEventListener('click', _handleSend);

  // Wire keyboard: Enter sends, Shift+Enter inserts newline
  _inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      _handleSend();
    }
  });

  // Auto-resize textarea on input
  _inputEl.addEventListener('input', _autoResize);

  // Update send button disabled state on input
  _inputEl.addEventListener('input', _updateSendBtn);

  // Initial state
  _updateSendBtn();

  // Check LLM availability
  _checkLlmStatus();

  // Init Lucide icons in the container
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({
      attrs: { class: ['lucide'] },
      nameAttr: 'data-lucide'
    });
  }

  // Focus input
  _inputEl.focus();

  // Track active object IRI via tab-activated events
  document.addEventListener('sempkm:tab-activated', function (e) {
    var detail = e.detail || {};
    if (detail.isObjectTab) {
      _activeObjectIri = detail.tabId;
    } else {
      _activeObjectIri = null;
    }
    SemPKM.debug('copilot', 'active object tracking', _activeObjectIri ? 'iri=' + _activeObjectIri : 'null');
  });

  // Load existing conversations
  _loadConversations();

  // Load personas for the selector
  _loadPersonas();

  SemPKM.debug('copilot', 'initialized');
}

// ---------------------------------------------------------------------------
// Conversation management
// ---------------------------------------------------------------------------

function _loadConversations() {
  apiFetch('/api/copilot/conversations', { credentials: 'same-origin', silent: true })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      _conversations = data || [];
      SemPKM.debug('copilot', 'conversations loaded, count=' + _conversations.length);
      _renderConversationHeader();
      if (_conversations.length > 0) {
        _switchConversation(_conversations[0].id);
      } else {
        _showEmptyState();
      }
    })
    .catch(function (err) {
      console.warn('copilot: failed to load conversations', err);
      _renderConversationHeader();
      _showEmptyState();
    });
}

function _switchConversation(id) {
  if (_isStreaming) return;
  _currentConversationId = id;
  _messageThread = [];
  if (_messagesEl) _messagesEl.innerHTML = '';

  SemPKM.debug('copilot', 'switched conversation id=' + id);

  apiFetch('/api/copilot/conversations/' + id, { credentials: 'same-origin', silent: true })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      var messages = data.messages || [];
      _updateHeaderTitle(data.title || 'New Chat');
      for (var i = 0; i < messages.length; i++) {
        var m = messages[i];
        if (m.role === 'user' || m.role === 'assistant') {
          var msg = { role: m.role, content: m.content, timestamp: m.created_at ? new Date(m.created_at) : new Date() };
          _messageThread.push(msg);
          _renderMessage(msg);
        }
      }
      if (_messageThread.length === 0) {
        _showEmptyState();
      }
      _scrollToBottom();
      // Close dropdown if open
      _closeConversationDropdown();
    })
    .catch(function (err) {
      console.warn('copilot: failed to load conversation', id, err);
      _showEmptyState();
    });
}

function _createNewChat() {
  if (_isStreaming) return;

  apiFetch('/api/copilot/conversations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title: null }),
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      _currentConversationId = data.id;
      _messageThread = [];
      if (_messagesEl) _messagesEl.innerHTML = '';
      _conversations.unshift({ id: data.id, title: data.title || 'New Chat', updated_at: new Date().toISOString() });
      _updateHeaderTitle(data.title || 'New Chat');
      _showEmptyState();
      SemPKM.debug('copilot', 'new chat created id=' + data.id);
      if (_inputEl && !_inputEl.disabled) _inputEl.focus();
    })
    .catch(function (err) {
      console.warn('copilot: failed to create conversation', err);
    });
}

function _deleteConversation(id) {
  apiFetch('/api/copilot/conversations/' + id, {
    method: 'DELETE',
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) {
      return resp.json();
    })
    .then(function () {
      SemPKM.debug('copilot', 'conversation deleted id=' + id);
      _conversations = _conversations.filter(function (c) { return c.id !== id; });
      if (_currentConversationId === id) {
        if (_conversations.length > 0) {
          _switchConversation(_conversations[0].id);
        } else {
          _currentConversationId = null;
          _messageThread = [];
          if (_messagesEl) _messagesEl.innerHTML = '';
          _updateHeaderTitle('New Chat');
          _showEmptyState();
        }
      }
      _closeConversationDropdown();
    })
    .catch(function (err) {
      console.warn('copilot: failed to delete conversation', id, err);
    });
}

// ---------------------------------------------------------------------------
// Conversation selector header
// ---------------------------------------------------------------------------

function _renderConversationHeader() {
  // Remove existing header if present
  var existing = document.getElementById('copilot-conv-header');
  if (existing) existing.remove();

  var header = document.createElement('div');
  header.className = 'copilot-conv-header';
  header.id = 'copilot-conv-header';

  // Menu button
  var menuBtn = document.createElement('button');
  menuBtn.className = 'copilot-conv-menu-btn';
  menuBtn.setAttribute('aria-label', 'Conversation list');
  menuBtn.title = 'Conversation list';
  menuBtn.innerHTML = '<i data-lucide="menu"></i>';
  menuBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    _toggleConversationDropdown();
  });
  header.appendChild(menuBtn);

  // Title
  var title = document.createElement('span');
  title.className = 'copilot-conv-title';
  title.id = 'copilot-conv-title';
  title.textContent = 'New Chat';
  header.appendChild(title);

  // New chat button
  var newBtn = document.createElement('button');
  newBtn.className = 'copilot-conv-new-btn';
  newBtn.setAttribute('aria-label', 'New chat');
  newBtn.title = 'New chat';
  newBtn.innerHTML = '<i data-lucide="plus"></i>';
  newBtn.addEventListener('click', function () {
    _createNewChat();
  });
  header.appendChild(newBtn);

  // Insert before messages area
  var container = document.getElementById('copilot-container');
  if (container && _messagesEl) {
    container.insertBefore(header, _messagesEl);
  }

  // Init Lucide icons in header
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }
}

function _updateHeaderTitle(text) {
  var titleEl = document.getElementById('copilot-conv-title');
  if (titleEl) titleEl.textContent = text;
}

function _toggleConversationDropdown() {
  var existing = document.getElementById('copilot-conv-dropdown');
  if (existing) {
    existing.remove();
    return;
  }

  var dropdown = document.createElement('div');
  dropdown.className = 'copilot-conv-dropdown';
  dropdown.id = 'copilot-conv-dropdown';

  if (_conversations.length === 0) {
    var emptyItem = document.createElement('div');
    emptyItem.className = 'copilot-conv-dropdown-empty';
    emptyItem.textContent = 'No conversations yet';
    dropdown.appendChild(emptyItem);
  } else {
    for (var i = 0; i < _conversations.length; i++) {
      (function (conv) {
        var item = document.createElement('div');
        item.className = 'copilot-conv-dropdown-item';
        if (conv.id === _currentConversationId) {
          item.classList.add('copilot-conv-dropdown-active');
        }

        var itemText = document.createElement('div');
        itemText.className = 'copilot-conv-dropdown-text';

        var itemTitle = document.createElement('span');
        itemTitle.className = 'copilot-conv-dropdown-title';
        itemTitle.textContent = conv.title || 'New Chat';
        itemText.appendChild(itemTitle);

        var itemTime = document.createElement('span');
        itemTime.className = 'copilot-conv-dropdown-time';
        itemTime.textContent = _relativeTime(conv.updated_at);
        itemText.appendChild(itemTime);

        itemText.addEventListener('click', function () {
          _switchConversation(conv.id);
        });
        item.appendChild(itemText);

        var delBtn = document.createElement('button');
        delBtn.className = 'copilot-conv-dropdown-del';
        delBtn.setAttribute('aria-label', 'Delete conversation');
        delBtn.title = 'Delete';
        delBtn.innerHTML = '<i data-lucide="x"></i>';
        delBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          _deleteConversation(conv.id);
        });
        item.appendChild(delBtn);

        dropdown.appendChild(item);
      })(_conversations[i]);
    }
  }

  var header = document.getElementById('copilot-conv-header');
  if (header) {
    header.appendChild(dropdown);
  }

  // Init Lucide icons in dropdown
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  // Close on outside click
  function _outsideClick(e) {
    var dd = document.getElementById('copilot-conv-dropdown');
    if (dd && !dd.contains(e.target) && !e.target.closest('.copilot-conv-menu-btn')) {
      dd.remove();
      document.removeEventListener('click', _outsideClick);
    }
  }
  // Defer to avoid the triggering click from closing the dropdown immediately
  setTimeout(function () {
    document.addEventListener('click', _outsideClick);
  }, 0);
}

function _closeConversationDropdown() {
  var dd = document.getElementById('copilot-conv-dropdown');
  if (dd) dd.remove();
}

function _relativeTime(isoStr) {
  if (!isoStr) return '';
  try {
    var d = new Date(isoStr);
    var now = new Date();
    var diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    return d.toLocaleDateString();
  } catch (e) {
    return '';
  }
}

// ---------------------------------------------------------------------------
// LLM availability check
// ---------------------------------------------------------------------------

function _checkLlmStatus() {
  apiFetch('/api/llm/status', { credentials: 'same-origin', silent: true })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.available) {
        _showLlmNotConfigured();
      } else {
        _showEmptyState();
      }
    })
    .catch(function () {
      // Network error — show the chat anyway, errors will surface when sending
      _showEmptyState();
    });
}

function _showLlmNotConfigured() {
  if (!_messagesEl) return;
  _messagesEl.innerHTML =
    '<div class="copilot-not-configured">' +
      '<i data-lucide="bot-off"></i>' +
      '<p>AI Copilot requires an LLM provider.<br>' +
      'Go to <a href="/settings">Settings → AI</a> to configure one.</p>' +
    '</div>';
  _inputEl.disabled = true;
  _sendBtn.disabled = true;
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] } });
  }
}

function _showEmptyState() {
  if (!_messagesEl || _messageThread.length > 0) return;
  _messagesEl.innerHTML =
    '<div class="copilot-empty" id="copilot-empty">' +
      '<i data-lucide="sparkles"></i>' +
      '<p>Ask anything about your knowledge graph.<br>' +
      '<span style="font-size:0.8rem;opacity:0.7;">e.g. "How many projects do I have?" or "Show me all tasks due this week"</span></p>' +
    '</div>';
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] } });
  }
}

// ---------------------------------------------------------------------------
// Send message
// ---------------------------------------------------------------------------

function _handleSend() {
  if (_isStreaming) return;
  var text = (_inputEl.value || '').trim();
  if (!text) return;

  // Clear empty state if present
  var emptyEl = document.getElementById('copilot-empty');
  if (emptyEl) emptyEl.remove();

  // Add user message to thread
  var userMsg = { role: 'user', content: text, timestamp: new Date() };
  _messageThread.push(userMsg);
  _renderMessage(userMsg);

  // Clear input and reset height
  _inputEl.value = '';
  _inputEl.style.height = '';
  _inputEl.rows = 1;
  _updateSendBtn();

  // Stream assistant response
  _streamCopilotResponse();
}

// ---------------------------------------------------------------------------
// SSE streaming
// ---------------------------------------------------------------------------

function _streamCopilotResponse() {
  _isStreaming = true;
  _updateSendBtn();

  // Prepare messages for API (role + content only)
  var apiMessages = _messageThread.map(function (m) {
    return { role: m.role, content: m.content };
  });

  // Show typing indicator
  var typingEl = _createTypingIndicator();
  _messagesEl.appendChild(typingEl);
  _scrollToBottom();

  // Create assistant message element (hidden until first token)
  var assistantEl = document.createElement('div');
  assistantEl.className = 'copilot-msg copilot-msg-assistant';
  assistantEl.style.display = 'none';

  var accumulatedContent = '';

  _abortController = new AbortController();

  apiFetch('/api/copilot/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: apiMessages,
      conversation_id: _currentConversationId,
      active_object_iri: _activeObjectIri,
      persona_id: _activePersonaId
    }),
    credentials: 'same-origin',
    signal: _abortController.signal,
    silent: true
  })
    .then(function (response) {
      if (!response) return; // AbortError — apiFetch returns undefined
      return response.body.getReader();
    })
    .then(function (reader) {
      if (!reader) return; // abort case
      var decoder = new TextDecoder();
      var buffer = '';

      function processChunk() {
        return reader.read().then(function (result) {
          if (result.done) {
            _finishStream(typingEl, assistantEl, accumulatedContent);
            return;
          }

          buffer += decoder.decode(result.value, { stream: true });

          // Parse SSE lines from the buffer
          var lines = buffer.split('\n');
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || '';

          var currentEvent = null;
          for (var i = 0; i < lines.length; i++) {
            var line = lines[i];

            if (line.startsWith('event: ')) {
              currentEvent = line.substring(7).trim();
              continue;
            }

            if (line.startsWith('data: ')) {
              var dataStr = line.substring(6);

              if (dataStr.trim() === '[DONE]') {
                _finishStream(typingEl, assistantEl, accumulatedContent);
                return;
              }

              // Handle custom events
              if (currentEvent === 'conversation_created') {
                try {
                  var convData = JSON.parse(dataStr);
                  if (convData.conversation_id) {
                    _currentConversationId = convData.conversation_id;
                    var convTitle = convData.title || 'New Chat';
                    _updateHeaderTitle(convTitle);
                    // Add to conversations list if not already present
                    var found = false;
                    for (var ci = 0; ci < _conversations.length; ci++) {
                      if (_conversations[ci].id === convData.conversation_id) { found = true; break; }
                    }
                    if (!found) {
                      _conversations.unshift({
                        id: convData.conversation_id,
                        title: convTitle,
                        updated_at: new Date().toISOString()
                      });
                    }
                    SemPKM.debug('copilot', 'conversation_created id=' + convData.conversation_id);
                  }
                } catch (e) {
                  console.warn('copilot: failed to parse conversation_created event', e);
                }
                currentEvent = null;
                continue;
              }

              if (currentEvent === 'sparql_query') {
                try {
                  var sparqlData = JSON.parse(dataStr);
                  _renderApprovalCard(sparqlData, assistantEl);
                } catch (e) {
                  console.warn('copilot: failed to parse sparql_query event', e);
                }
                currentEvent = null;
                continue;
              }

              if (currentEvent === 'create_object') {
                try {
                  var createData = JSON.parse(dataStr);
                  _renderCreateObjectCard(createData, assistantEl);
                } catch (e) {
                  console.warn('copilot: failed to parse create_object event', e);
                }
                currentEvent = null;
                continue;
              }

              if (currentEvent === 'error') {
                try {
                  var errorData = JSON.parse(dataStr);
                  _renderErrorMessage(errorData.error || 'Unknown error');
                } catch (e) {
                  _renderErrorMessage(dataStr);
                }
                currentEvent = null;
                continue;
              }

              // Standard OpenAI streaming data
              currentEvent = null;
              try {
                var chunk = JSON.parse(dataStr);
                var choices = chunk.choices || [];
                if (choices.length > 0) {
                  var delta = choices[0].delta || {};
                  var token = delta.content || '';
                  if (token) {
                    // Remove typing indicator and show assistant message on first token
                    if (!accumulatedContent) {
                      if (typingEl.parentNode) typingEl.remove();
                      _messagesEl.appendChild(assistantEl);
                      assistantEl.style.display = '';
                    }
                    accumulatedContent += token;
                    _updateAssistantMessage(assistantEl, accumulatedContent);
                    _scrollToBottom();
                  }
                }
              } catch (e) {
                // Ignore unparseable lines
              }
            }

            // Empty line resets event type
            if (line === '') {
              currentEvent = null;
            }
          }

          return processChunk();
        });
      }

      return processChunk();
    })
    .catch(function (err) {
      if (err.name === 'AbortError') return;
      console.error('copilot: stream error', err);
      if (typingEl.parentNode) typingEl.remove();
      _renderErrorMessage('Failed to connect to copilot: ' + (err.message || 'unknown error'));
      _isStreaming = false;
      _updateSendBtn();
    });
}

function _finishStream(typingEl, assistantEl, accumulatedContent) {
  if (typingEl.parentNode) typingEl.remove();

  if (accumulatedContent) {
    // Store in thread
    _messageThread.push({
      role: 'assistant',
      content: accumulatedContent,
      timestamp: new Date()
    });
    // Final markdown render with IRI pill conversion
    _updateAssistantMessage(assistantEl, accumulatedContent);
  }

  _isStreaming = false;
  _abortController = null;
  _updateSendBtn();
  _scrollToBottom();

  // Re-focus input
  if (_inputEl && !_inputEl.disabled) {
    _inputEl.focus();
  }
}

// ---------------------------------------------------------------------------
// Message rendering
// ---------------------------------------------------------------------------

function _renderMessage(msg) {
  var el = document.createElement('div');
  el.className = 'copilot-msg';

  if (msg.role === 'user') {
    el.className += ' copilot-msg-user';
    el.textContent = msg.content;
  } else if (msg.role === 'assistant') {
    el.className += ' copilot-msg-assistant';
    el.innerHTML = _renderMarkdown(msg.content);
  } else {
    el.className += ' copilot-msg-system';
    el.textContent = msg.content;
  }

  _messagesEl.appendChild(el);
  _scrollToBottom();
}

function _renderErrorMessage(text) {
  var el = document.createElement('div');
  el.className = 'copilot-msg copilot-msg-error';
  el.textContent = text;
  _messagesEl.appendChild(el);
  _scrollToBottom();
}

function _updateAssistantMessage(el, content) {
  var html = _renderMarkdown(content);
  html = _convertIriPills(html);
  el.innerHTML = html;

  // Init any Lucide icons inside pills
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }
}

// ---------------------------------------------------------------------------
// Markdown rendering
// ---------------------------------------------------------------------------

function _renderMarkdown(text) {
  // Use marked.js if available (loaded by workspace)
  if (typeof globalThis.marked !== 'undefined') {
    try {
      var html = globalThis.marked.parse(text);
      // Sanitize if DOMPurify available
      if (typeof DOMPurify !== 'undefined') {
        html = DOMPurify.sanitize(html);
      }
      return html;
    } catch (e) {
      console.warn('copilot: markdown parse error, falling back to escaped text', e);
    }
  }
  // Fallback: basic escaping with line breaks
  return _escapeHtml(text).replace(/\n/g, '<br>');
}

// ---------------------------------------------------------------------------
// IRI Pill Conversion
// ---------------------------------------------------------------------------

/**
 * Convert [[iri|label]] markers in rendered HTML to clickable pills.
 *
 * The CopilotService formats object references as [[iri|label]] in its
 * prose output. We also convert markdown-style [Label](iri:full-iri) links.
 */
function _convertIriPills(html) {
  // Pattern 1: [[iri|label]] markers from CopilotService.execute_and_format()
  html = html.replace(/\[\[([^|]+)\|([^\]]+)\]\]/g, function (match, iri, label) {
    return '<a class="copilot-iri-pill" href="#" title="' + _escapeAttr(iri) + '" ' +
      'onclick="event.preventDefault();if(window.SemPKM.openTab){window.SemPKM.openTab(\'' +
      _escapeJs(iri) + '\',\'' + _escapeJs(label) + '\')}">' +
      _escapeHtml(label) + '</a>';
  });

  // Pattern 2: [Label](iri:full-iri) links rendered as <a href="iri:...">
  // The markdown renderer may have already converted these to <a> tags
  html = html.replace(/<a\s+href="iri:([^"]+)"[^>]*>([^<]+)<\/a>/g, function (match, iri, label) {
    return '<a class="copilot-iri-pill" href="#" title="' + _escapeAttr(iri) + '" ' +
      'onclick="event.preventDefault();if(window.SemPKM.openTab){window.SemPKM.openTab(\'' +
      _escapeJs(iri) + '\',\'' + _escapeJs(label) + '\')}">' +
      _escapeHtml(label) + '</a>';
  });

  return html;
}

// ---------------------------------------------------------------------------
// SPARQL Approval Card
// ---------------------------------------------------------------------------

/**
 * Basic SPARQL keyword highlighting for display in approval cards.
 * Wraps known keywords in <span class="sparql-kw"> for styling.
 */
function _highlightSparql(text) {
  var escaped = _escapeHtml(text);
  // Highlight SPARQL keywords
  var keywords = /\b(SELECT|WHERE|GRAPH|FILTER|PREFIX|ORDER\s+BY|GROUP\s+BY|LIMIT|OFFSET|OPTIONAL|UNION|BIND|AS|DISTINCT|COUNT|SUM|AVG|MIN|MAX|HAVING|VALUES|ASK|CONSTRUCT|DESCRIBE|FROM|NAMED|STR|LANG|LANGMATCHES|REGEX|BOUND|DATATYPE|IRI|URI|BNODE|RAND|ABS|CEIL|FLOOR|ROUND|STRLEN|SUBSTR|UCASE|LCASE|CONTAINS|STRSTARTS|STRENDS|YEAR|MONTH|DAY|HOURS|MINUTES|SECONDS|NOW|IF|COALESCE|EXISTS|NOT|IN|a)\b/gi;
  escaped = escaped.replace(keywords, '<span class="sparql-kw">$1</span>');
  // Highlight variables
  escaped = escaped.replace(/(\?\w+)/g, '<span class="sparql-var">$1</span>');
  // Highlight prefixed names (prefix:local) — but not inside already-wrapped spans
  escaped = escaped.replace(/(?<![">])(\b\w+:\w+\b)(?![<])/g, '<span class="sparql-prefix">$1</span>');
  return escaped;
}

function _renderApprovalCard(data, parentEl) {
  var target = parentEl && parentEl.parentNode ? parentEl : _messagesEl;

  var card = document.createElement('div');
  card.className = 'copilot-approval-card';
  card.dataset.retryCount = '0';
  card.dataset.query = data.query || '';

  // Header with label and validation status
  var header = document.createElement('div');
  header.className = 'copilot-approval-header';

  var label = document.createElement('div');
  label.className = 'copilot-approval-label';
  label.textContent = 'Generated SPARQL Query';
  header.appendChild(label);

  var status = document.createElement('div');
  status.className = 'copilot-approval-status';
  if (data.valid) {
    status.innerHTML = '<i data-lucide="check-circle"></i> <span>Valid</span>';
    status.classList.add('copilot-approval-status-valid');
  } else {
    status.innerHTML = '<i data-lucide="alert-triangle"></i> <span>Invalid</span>';
    status.classList.add('copilot-approval-status-invalid');
  }
  header.appendChild(status);
  card.appendChild(header);

  // Query display with syntax highlighting
  var queryWrap = document.createElement('div');
  queryWrap.className = 'copilot-approval-query-wrap';

  var pre = document.createElement('pre');
  pre.className = 'copilot-approval-query';
  var code = document.createElement('code');
  code.innerHTML = _highlightSparql(data.query || '');
  pre.appendChild(code);
  queryWrap.appendChild(pre);
  card.appendChild(queryWrap);

  // Validation error text
  if (data.error) {
    var errEl = document.createElement('div');
    errEl.className = 'copilot-approval-error';
    errEl.textContent = data.error;
    card.appendChild(errEl);
  }

  // Loading overlay (hidden by default)
  var loadingEl = document.createElement('div');
  loadingEl.className = 'copilot-approval-loading';
  loadingEl.style.display = 'none';
  loadingEl.innerHTML =
    '<div class="copilot-approval-spinner"></div>' +
    '<span>Executing query…</span>';
  card.appendChild(loadingEl);

  // Action buttons
  var actions = document.createElement('div');
  actions.className = 'copilot-approval-actions';

  if (data.valid) {
    var approveBtn = document.createElement('button');
    approveBtn.className = 'copilot-approval-btn copilot-approval-btn-approve';
    approveBtn.innerHTML = '<i data-lucide="check"></i> Approve';
    approveBtn.setAttribute('aria-label', 'Approve and execute this SPARQL query');
    approveBtn.addEventListener('click', function () {
      _handleApprove(card);
    });
    actions.appendChild(approveBtn);
  }

  var editBtn = document.createElement('button');
  editBtn.className = 'copilot-approval-btn copilot-approval-btn-edit';
  editBtn.innerHTML = '<i data-lucide="pencil"></i> Edit';
  editBtn.setAttribute('aria-label', 'Edit this SPARQL query');
  editBtn.addEventListener('click', function () {
    _handleEdit(card);
  });
  actions.appendChild(editBtn);

  var rejectBtn = document.createElement('button');
  rejectBtn.className = 'copilot-approval-btn copilot-approval-btn-reject';
  rejectBtn.innerHTML = '<i data-lucide="x"></i> Reject';
  rejectBtn.setAttribute('aria-label', 'Reject this SPARQL query');
  rejectBtn.addEventListener('click', function () {
    _handleReject(card);
  });
  actions.appendChild(rejectBtn);

  card.appendChild(actions);

  // Results area (hidden by default)
  var resultArea = document.createElement('div');
  resultArea.className = 'copilot-approval-result';
  resultArea.style.display = 'none';
  card.appendChild(resultArea);

  // Insert the card after the assistant message element (or at end of thread)
  if (parentEl && parentEl.parentNode) {
    parentEl.parentNode.insertBefore(card, parentEl.nextSibling);
  } else {
    _messagesEl.appendChild(card);
  }

  // Init Lucide icons in the card
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  _scrollToBottom();
}

// ---------------------------------------------------------------------------
// Approval action handlers
// ---------------------------------------------------------------------------

function _setCardLoading(card, loading, text) {
  var loadingEl = card.querySelector('.copilot-approval-loading');
  var actionsEl = card.querySelector('.copilot-approval-actions');
  if (loadingEl) {
    loadingEl.style.display = loading ? '' : 'none';
    if (text) {
      var span = loadingEl.querySelector('span');
      if (span) span.textContent = text;
    }
  }
  if (actionsEl) {
    actionsEl.style.display = loading ? 'none' : '';
  }
}

function _disableCardButtons(card) {
  var buttons = card.querySelectorAll('.copilot-approval-btn');
  buttons.forEach(function (b) { b.disabled = true; });
}

function _handleApprove(card) {
  var query = card.dataset.query;
  _setCardLoading(card, true, 'Executing query…');

  apiFetch('/api/copilot/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: query, action: 'approve' }),
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) { return resp.json(); })
    .then(function (result) {
      _setCardLoading(card, false);
      if (result.status === 'approved') {
        _showApprovalResult(card, result);
      } else if (result.error) {
        _showApprovalError(card, query, result.error);
      }
    })
    .catch(function (err) {
      _setCardLoading(card, false);
      _showApprovalError(card, query, err.message || 'Network error');
    });
}

function _handleEdit(card) {
  var query = card.dataset.query;
  var queryWrap = card.querySelector('.copilot-approval-query-wrap');
  var actionsEl = card.querySelector('.copilot-approval-actions');
  if (!queryWrap || !actionsEl) return;

  // Replace pre block with textarea
  queryWrap.innerHTML = '';
  var textarea = document.createElement('textarea');
  textarea.className = 'copilot-approval-edit-textarea';
  textarea.value = query;
  textarea.rows = Math.max(5, query.split('\n').length + 1);
  textarea.setAttribute('aria-label', 'Edit SPARQL query');
  queryWrap.appendChild(textarea);

  // Replace buttons with Run Edited / Cancel
  actionsEl.innerHTML = '';

  var runBtn = document.createElement('button');
  runBtn.className = 'copilot-approval-btn copilot-approval-btn-approve';
  runBtn.innerHTML = '<i data-lucide="play"></i> Run Edited Query';
  runBtn.setAttribute('aria-label', 'Execute the edited SPARQL query');
  runBtn.addEventListener('click', function () {
    var editedQuery = textarea.value.trim();
    if (!editedQuery) return;
    card.dataset.query = editedQuery;
    _setCardLoading(card, true, 'Executing query…');

    apiFetch('/api/copilot/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, action: 'edit', edited_query: editedQuery }),
      credentials: 'same-origin',
      silent: true
    })
      .then(function (resp) { return resp.json(); })
      .then(function (result) {
        _setCardLoading(card, false);
        if (result.status === 'approved') {
          // Restore query display with the edited query
          _restoreQueryDisplay(card, editedQuery);
          _showApprovalResult(card, result);
        } else if (result.error) {
          _showApprovalError(card, editedQuery, result.error);
        }
      })
      .catch(function (err) {
        _setCardLoading(card, false);
        _showApprovalError(card, editedQuery, err.message || 'Network error');
      });
  });
  actionsEl.appendChild(runBtn);

  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'copilot-approval-btn copilot-approval-btn-reject';
  cancelBtn.innerHTML = '<i data-lucide="x"></i> Cancel';
  cancelBtn.setAttribute('aria-label', 'Cancel editing');
  cancelBtn.addEventListener('click', function () {
    // Restore original query display
    _restoreQueryDisplay(card, query);
    card.dataset.query = query;
  });
  actionsEl.appendChild(cancelBtn);

  // Init Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  textarea.focus();
}

function _restoreQueryDisplay(card, query) {
  var queryWrap = card.querySelector('.copilot-approval-query-wrap');
  var actionsEl = card.querySelector('.copilot-approval-actions');
  if (!queryWrap) return;

  // Restore pre+code display
  queryWrap.innerHTML = '';
  var pre = document.createElement('pre');
  pre.className = 'copilot-approval-query';
  var code = document.createElement('code');
  code.innerHTML = _highlightSparql(query);
  pre.appendChild(code);
  queryWrap.appendChild(pre);

  // Restore action buttons
  if (actionsEl) {
    actionsEl.innerHTML = '';

    var approveBtn = document.createElement('button');
    approveBtn.className = 'copilot-approval-btn copilot-approval-btn-approve';
    approveBtn.innerHTML = '<i data-lucide="check"></i> Approve';
    approveBtn.setAttribute('aria-label', 'Approve and execute this SPARQL query');
    approveBtn.addEventListener('click', function () {
      _handleApprove(card);
    });
    actionsEl.appendChild(approveBtn);

    var editBtn = document.createElement('button');
    editBtn.className = 'copilot-approval-btn copilot-approval-btn-edit';
    editBtn.innerHTML = '<i data-lucide="pencil"></i> Edit';
    editBtn.setAttribute('aria-label', 'Edit this SPARQL query');
    editBtn.addEventListener('click', function () {
      _handleEdit(card);
    });
    actionsEl.appendChild(editBtn);

    var rejectBtn = document.createElement('button');
    rejectBtn.className = 'copilot-approval-btn copilot-approval-btn-reject';
    rejectBtn.innerHTML = '<i data-lucide="x"></i> Reject';
    rejectBtn.setAttribute('aria-label', 'Reject this SPARQL query');
    rejectBtn.addEventListener('click', function () {
      _handleReject(card);
    });
    actionsEl.appendChild(rejectBtn);

    // Init Lucide icons
    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
    }
  }
}

function _handleReject(card) {
  var query = card.dataset.query;
  _disableCardButtons(card);

  apiFetch('/api/copilot/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: query, action: 'reject' }),
    credentials: 'same-origin',
    silent: true
  })
    .then(function () {
      card.classList.add('copilot-approval-rejected');
      var actionsEl = card.querySelector('.copilot-approval-actions');
      if (actionsEl) {
        actionsEl.innerHTML = '<span class="copilot-approval-cancelled">Query cancelled</span>';
      }
    })
    .catch(function () {
      card.classList.add('copilot-approval-rejected');
    });
}

function _showApprovalResult(card, result) {
  // Remove action buttons (query was executed)
  var actionsEl = card.querySelector('.copilot-approval-actions');
  if (actionsEl) {
    actionsEl.innerHTML = '<span class="copilot-approval-success"><i data-lucide="check-circle"></i> Query executed</span>';
    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
    }
  }

  // Render results as an assistant message after the card
  var proseHtml = _renderMarkdown(result.prose || 'Query executed successfully.');
  proseHtml = _convertIriPills(proseHtml);

  var resultEl = document.createElement('div');
  resultEl.className = 'copilot-msg copilot-msg-assistant';
  resultEl.innerHTML = proseHtml;

  // Store as assistant message
  _messageThread.push({
    role: 'assistant',
    content: result.prose || 'Query executed successfully.',
    timestamp: new Date()
  });

  // Insert after the approval card
  if (card.nextSibling) {
    card.parentNode.insertBefore(resultEl, card.nextSibling);
  } else {
    _messagesEl.appendChild(resultEl);
  }

  // Re-init Lucide icons for any pills in the result
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  _scrollToBottom();
}

function _showApprovalError(card, query, errorMsg) {
  var retryCount = parseInt(card.dataset.retryCount || '0', 10);
  var actionsEl = card.querySelector('.copilot-approval-actions');
  if (!actionsEl) return;

  // Clear existing error messages from the card
  var oldErr = card.querySelector('.copilot-approval-error');
  if (oldErr) oldErr.remove();

  // Show error message
  var errEl = document.createElement('div');
  errEl.className = 'copilot-approval-error';
  errEl.textContent = errorMsg;
  var queryWrap = card.querySelector('.copilot-approval-query-wrap');
  if (queryWrap) {
    queryWrap.insertAdjacentElement('afterend', errEl);
  } else {
    card.insertBefore(errEl, actionsEl);
  }

  // Replace buttons with retry/reject
  actionsEl.innerHTML = '';

  if (retryCount < 2) {
    var retryBtn = document.createElement('button');
    retryBtn.className = 'copilot-approval-btn copilot-approval-btn-approve';
    retryBtn.innerHTML = '<i data-lucide="refresh-cw"></i> Retry';
    retryBtn.setAttribute('aria-label', 'Retry with self-correction');
    retryBtn.addEventListener('click', function () {
      _handleRetry(card, query, errorMsg);
    });
    actionsEl.appendChild(retryBtn);
  }

  var editBtn = document.createElement('button');
  editBtn.className = 'copilot-approval-btn copilot-approval-btn-edit';
  editBtn.innerHTML = '<i data-lucide="pencil"></i> Edit';
  editBtn.setAttribute('aria-label', 'Edit this SPARQL query');
  editBtn.addEventListener('click', function () {
    _handleEdit(card);
  });
  actionsEl.appendChild(editBtn);

  var rejectBtn = document.createElement('button');
  rejectBtn.className = 'copilot-approval-btn copilot-approval-btn-reject';
  rejectBtn.innerHTML = '<i data-lucide="x"></i> Dismiss';
  rejectBtn.setAttribute('aria-label', 'Dismiss this query');
  rejectBtn.addEventListener('click', function () {
    _handleReject(card);
  });
  actionsEl.appendChild(rejectBtn);

  // Init Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  _scrollToBottom();
}

function _handleRetry(card, query, errorMsg) {
  var retryCount = parseInt(card.dataset.retryCount || '0', 10);
  var attempt = retryCount + 1;

  // Show retry status message
  _setCardLoading(card, true, 'Retrying… (attempt ' + (attempt + 1) + '/3)');

  // Add a system message to the thread
  var retryMsg = document.createElement('div');
  retryMsg.className = 'copilot-msg copilot-retry-msg';
  retryMsg.textContent = 'Self-correcting… attempt ' + (attempt + 1) + ' of 3';
  if (card.nextSibling) {
    card.parentNode.insertBefore(retryMsg, card.nextSibling);
  } else {
    _messagesEl.appendChild(retryMsg);
  }
  _scrollToBottom();

  apiFetch('/api/copilot/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      action: 'retry',
      error: errorMsg,
      retry_count: retryCount
    }),
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) { return resp.json(); })
    .then(function (result) {
      _setCardLoading(card, false);

      if (result.status === 'max_retries') {
        // Remove retry message and show max-retries error
        if (retryMsg.parentNode) retryMsg.remove();
        var maxErr = document.createElement('div');
        maxErr.className = 'copilot-msg copilot-retry-msg copilot-retry-exhausted';
        maxErr.textContent = result.error || 'Unable to generate a valid query after 3 attempts. Try rephrasing your question.';
        if (card.nextSibling) {
          card.parentNode.insertBefore(maxErr, card.nextSibling);
        } else {
          _messagesEl.appendChild(maxErr);
        }

        // Disable the card
        _disableCardButtons(card);
        var actionsEl = card.querySelector('.copilot-approval-actions');
        if (actionsEl) {
          actionsEl.innerHTML = '<span class="copilot-approval-cancelled">Max retries reached</span>';
        }
        _scrollToBottom();
        return;
      }

      if (result.status === 'retry_result' && result.new_query) {
        // Remove old retry message
        if (retryMsg.parentNode) retryMsg.remove();

        // Update the card with the corrected query
        card.dataset.query = result.new_query;
        card.dataset.retryCount = String(result.retry_count);

        // Update the query display
        _restoreQueryDisplay(card, result.new_query);

        // Update validation status
        var statusEl = card.querySelector('.copilot-approval-status');
        if (statusEl) {
          statusEl.className = 'copilot-approval-status';
          if (result.valid) {
            statusEl.innerHTML = '<i data-lucide="check-circle"></i> <span>Valid</span>';
            statusEl.classList.add('copilot-approval-status-valid');
          } else {
            statusEl.innerHTML = '<i data-lucide="alert-triangle"></i> <span>Invalid</span>';
            statusEl.classList.add('copilot-approval-status-invalid');
          }
        }

        // Clear previous error
        var oldErr = card.querySelector('.copilot-approval-error');
        if (oldErr) oldErr.remove();

        // Show new error if invalid
        if (!result.valid && result.error) {
          var errEl = document.createElement('div');
          errEl.className = 'copilot-approval-error';
          errEl.textContent = result.error;
          var queryWrap = card.querySelector('.copilot-approval-query-wrap');
          if (queryWrap && queryWrap.nextSibling) {
            card.insertBefore(errEl, queryWrap.nextSibling);
          }
        }

        // Init Lucide icons
        if (typeof lucide !== 'undefined') {
          lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
        }
        _scrollToBottom();
      } else if (result.error) {
        // Retry produced an error
        if (retryMsg.parentNode) retryMsg.remove();
        _showApprovalError(card, query, result.error);
      }
    })
    .catch(function (err) {
      _setCardLoading(card, false);
      if (retryMsg.parentNode) retryMsg.remove();
      _showApprovalError(card, query, err.message || 'Retry request failed');
    });
}

// ---------------------------------------------------------------------------
// Typing indicator
// ---------------------------------------------------------------------------

function _createTypingIndicator() {
  var el = document.createElement('div');
  el.className = 'copilot-typing';
  el.id = 'copilot-typing';
  el.innerHTML =
    '<span class="copilot-typing-dot"></span>' +
    '<span class="copilot-typing-dot"></span>' +
    '<span class="copilot-typing-dot"></span>';
  return el;
}

// ---------------------------------------------------------------------------
// Textarea auto-resize
// ---------------------------------------------------------------------------

function _autoResize() {
  if (!_inputEl) return;
  // Reset to single row to measure scroll height correctly
  _inputEl.style.height = 'auto';
  // Cap at ~5 lines (approx 120px)
  var maxHeight = 120;
  var newHeight = Math.min(_inputEl.scrollHeight, maxHeight);
  _inputEl.style.height = newHeight + 'px';
}

function _updateSendBtn() {
  if (!_sendBtn || !_inputEl) return;
  var hasText = (_inputEl.value || '').trim().length > 0;
  _sendBtn.disabled = !hasText || _isStreaming || _inputEl.disabled;
}

// ---------------------------------------------------------------------------
// Scroll helper
// ---------------------------------------------------------------------------

function _scrollToBottom() {
  if (!_messagesEl) return;
  // Use requestAnimationFrame to ensure DOM has updated
  requestAnimationFrame(function () {
    _messagesEl.scrollTop = _messagesEl.scrollHeight;
  });
}

// ---------------------------------------------------------------------------
// Escaping utilities
// ---------------------------------------------------------------------------

function _escapeHtml(str) {
  var div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function _escapeAttr(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function _escapeJs(str) {
  return str
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '\\"');
}

// ---------------------------------------------------------------------------
// Persona management
// ---------------------------------------------------------------------------

function _loadPersonas() {
  apiFetch('/api/copilot/personas', { credentials: 'same-origin', silent: true })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      _personas = data || [];
      // Find active persona
      for (var i = 0; i < _personas.length; i++) {
        if (_personas[i].is_active) {
          _activePersonaId = _personas[i].id;
          break;
        }
      }
      SemPKM.debug('copilot', 'personas loaded, count=' + _personas.length + ', active=' + _activePersonaId);
      _renderPersonaSelector();
    })
    .catch(function (err) {
      console.warn('copilot: failed to load personas', err);
    });
}

function _renderPersonaSelector() {
  // Remove existing selector if present
  var existing = document.getElementById('copilot-persona-selector');
  if (existing) existing.remove();

  var header = document.getElementById('copilot-conv-header');
  if (!header || _personas.length === 0) return;

  // Find the active persona for display
  var activePersona = null;
  for (var i = 0; i < _personas.length; i++) {
    if (_personas[i].id === _activePersonaId) {
      activePersona = _personas[i];
      break;
    }
  }

  var wrapper = document.createElement('div');
  wrapper.className = 'copilot-persona-selector';
  wrapper.id = 'copilot-persona-selector';

  var btn = document.createElement('button');
  btn.className = 'copilot-persona-btn';
  btn.setAttribute('aria-label', 'Switch persona');
  btn.title = activePersona ? activePersona.name : 'Select persona';
  btn.innerHTML = '<span class="copilot-persona-icon">' + (activePersona ? _escapeHtml(activePersona.icon) : '🤖') + '</span>' +
    '<span class="copilot-persona-name">' + _escapeHtml(activePersona ? activePersona.name : 'Persona') + '</span>' +
    '<i data-lucide="chevron-down"></i>';
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    _togglePersonaDropdown();
  });
  wrapper.appendChild(btn);

  // Insert between title and new-chat button
  var newBtn = header.querySelector('.copilot-conv-new-btn');
  if (newBtn) {
    header.insertBefore(wrapper, newBtn);
  } else {
    header.appendChild(wrapper);
  }

  // Init Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }
}

function _togglePersonaDropdown() {
  var existing = document.getElementById('copilot-persona-dropdown');
  if (existing) {
    existing.remove();
    return;
  }

  var dropdown = document.createElement('div');
  dropdown.className = 'copilot-persona-dropdown';
  dropdown.id = 'copilot-persona-dropdown';

  for (var i = 0; i < _personas.length; i++) {
    (function (persona) {
      var item = document.createElement('div');
      item.className = 'copilot-persona-item';
      if (persona.id === _activePersonaId) {
        item.classList.add('copilot-persona-item-active');
      }

      var icon = document.createElement('span');
      icon.className = 'copilot-persona-item-icon';
      icon.textContent = persona.icon;
      item.appendChild(icon);

      var info = document.createElement('div');
      info.className = 'copilot-persona-item-info';

      var name = document.createElement('span');
      name.className = 'copilot-persona-item-name';
      name.textContent = persona.name;
      info.appendChild(name);

      item.appendChild(info);

      if (persona.id === _activePersonaId) {
        var check = document.createElement('span');
        check.className = 'copilot-persona-item-check';
        check.innerHTML = '<i data-lucide="check"></i>';
        item.appendChild(check);
      }

      item.addEventListener('click', function () {
        _activatePersona(persona.id);
      });
      dropdown.appendChild(item);
    })(_personas[i]);
  }

  var selector = document.getElementById('copilot-persona-selector');
  if (selector) {
    selector.appendChild(dropdown);
  }

  // Init Lucide icons in dropdown
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  // Close on outside click
  function _outsideClick(e) {
    var dd = document.getElementById('copilot-persona-dropdown');
    if (dd && !dd.contains(e.target) && !e.target.closest('.copilot-persona-btn')) {
      dd.remove();
      document.removeEventListener('click', _outsideClick);
    }
  }
  setTimeout(function () {
    document.addEventListener('click', _outsideClick);
  }, 0);
}

function _activatePersona(personaId) {
  apiFetch('/api/copilot/personas/' + personaId + '/activate', {
    method: 'POST',
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      _activePersonaId = data.id;
      // Update is_active flags in local state
      for (var i = 0; i < _personas.length; i++) {
        _personas[i].is_active = (_personas[i].id === data.id);
      }
      SemPKM.debug('copilot', 'persona activated id=' + data.id + ', name=' + data.name);
      _renderPersonaSelector();
      // Close dropdown
      var dd = document.getElementById('copilot-persona-dropdown');
      if (dd) dd.remove();
    })
    .catch(function (err) {
      console.warn('copilot: failed to activate persona', err);
    });
}

// ---------------------------------------------------------------------------
// Create Object Confirmation Card
// ---------------------------------------------------------------------------

function _renderCreateObjectCard(data, parentEl) {
  var target = parentEl && parentEl.parentNode ? parentEl : _messagesEl;

  var card = document.createElement('div');
  card.className = 'copilot-create-card';

  // Header
  var header = document.createElement('div');
  header.className = 'copilot-create-header';

  var label = document.createElement('div');
  label.className = 'copilot-create-label';
  label.textContent = 'Create Object';
  header.appendChild(label);

  var typeBadge = document.createElement('div');
  typeBadge.className = 'copilot-create-type';
  // Show just the local name from the type IRI
  var typeLabel = data.label || _iriLocalName(data.type || '');
  typeBadge.textContent = typeLabel;
  header.appendChild(typeBadge);

  card.appendChild(header);

  // Properties table
  var props = data.properties || {};
  var propKeys = Object.keys(props);
  if (propKeys.length > 0) {
    var table = document.createElement('div');
    table.className = 'copilot-create-props';
    for (var i = 0; i < propKeys.length; i++) {
      var row = document.createElement('div');
      row.className = 'copilot-create-prop-row';

      var keyEl = document.createElement('span');
      keyEl.className = 'copilot-create-prop-key';
      keyEl.textContent = _iriLocalName(propKeys[i]);
      row.appendChild(keyEl);

      var valEl = document.createElement('span');
      valEl.className = 'copilot-create-prop-val';
      valEl.textContent = String(props[propKeys[i]]);
      row.appendChild(valEl);

      table.appendChild(row);
    }
    card.appendChild(table);
  }

  // Action buttons
  var actions = document.createElement('div');
  actions.className = 'copilot-create-actions';

  var createBtn = document.createElement('button');
  createBtn.className = 'copilot-approval-btn copilot-approval-btn-approve';
  createBtn.innerHTML = '<i data-lucide="plus"></i> Create';
  createBtn.setAttribute('aria-label', 'Create this object');
  createBtn.addEventListener('click', function () {
    _handleCreateObject(card, data);
  });
  actions.appendChild(createBtn);

  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'copilot-approval-btn copilot-approval-btn-reject';
  cancelBtn.innerHTML = '<i data-lucide="x"></i> Cancel';
  cancelBtn.setAttribute('aria-label', 'Cancel object creation');
  cancelBtn.addEventListener('click', function () {
    _handleCancelCreate(card);
  });
  actions.appendChild(cancelBtn);

  card.appendChild(actions);

  // Loading overlay (hidden by default)
  var loadingEl = document.createElement('div');
  loadingEl.className = 'copilot-approval-loading copilot-create-loading';
  loadingEl.style.display = 'none';
  loadingEl.innerHTML =
    '<div class="copilot-approval-spinner"></div>' +
    '<span>Creating object…</span>';
  card.appendChild(loadingEl);

  // Result area (hidden by default)
  var resultArea = document.createElement('div');
  resultArea.className = 'copilot-create-result';
  resultArea.style.display = 'none';
  card.appendChild(resultArea);

  // Insert after the assistant message element
  if (parentEl && parentEl.parentNode) {
    parentEl.parentNode.insertBefore(card, parentEl.nextSibling);
  } else {
    _messagesEl.appendChild(card);
  }

  // Init Lucide icons
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
  }

  _scrollToBottom();
}

function _handleCreateObject(card, data) {
  var actionsEl = card.querySelector('.copilot-create-actions');
  var loadingEl = card.querySelector('.copilot-create-loading');
  if (actionsEl) actionsEl.style.display = 'none';
  if (loadingEl) loadingEl.style.display = '';

  // Build the Command API payload
  var commandPayload = {
    command: 'object.create',
    params: {
      type: data.type,
      properties: data.properties || {}
    }
  };

  // Add label as dcterms:title if present and not already in properties
  if (data.label && !data.properties['http://purl.org/dc/terms/title'] && !data.properties['dcterms:title']) {
    commandPayload.params.properties['dcterms:title'] = data.label;
  }

  apiFetch('/api/commands', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(commandPayload),
    credentials: 'same-origin',
    silent: true
  })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (result) {
      if (loadingEl) loadingEl.style.display = 'none';

      // Show success state
      var resultArea = card.querySelector('.copilot-create-result');
      if (resultArea) {
        var createdIri = result.results && result.results[0] ? result.results[0].iri : '';
        var displayLabel = data.label || _iriLocalName(data.type || 'Object');
        resultArea.style.display = '';
        resultArea.innerHTML =
          '<div class="copilot-create-success">' +
            '<i data-lucide="check-circle"></i> Created ' +
            (createdIri
              ? '<a class="copilot-iri-pill" href="#" title="' + _escapeAttr(createdIri) + '" ' +
                'onclick="event.preventDefault();if(window.SemPKM.openTab){window.SemPKM.openTab(\'' +
                _escapeJs(createdIri) + '\',\'' + _escapeJs(displayLabel) + '\')}">' +
                _escapeHtml(displayLabel) + '</a>'
              : _escapeHtml(displayLabel)) +
          '</div>';

        // Init Lucide icons
        if (typeof lucide !== 'undefined') {
          lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
        }
      }

      // Add system message to thread
      var typeLabel = _iriLocalName(data.type || 'Object');
      var iri = result.results && result.results[0] ? result.results[0].iri : '';
      var sysContent = 'Created ' + typeLabel + (iri ? ': [[' + iri + '|' + (data.label || typeLabel) + ']]' : '');
      _messageThread.push({ role: 'assistant', content: sysContent, timestamp: new Date() });

      _scrollToBottom();
      SemPKM.debug('copilot', 'object created iri=' + iri);
    })
    .catch(function (err) {
      if (loadingEl) loadingEl.style.display = 'none';
      if (actionsEl) actionsEl.style.display = '';

      // Show error in the result area
      var resultArea = card.querySelector('.copilot-create-result');
      if (resultArea) {
        resultArea.style.display = '';
        resultArea.innerHTML =
          '<div class="copilot-create-error">' +
            '<i data-lucide="alert-circle"></i> ' + _escapeHtml(err.message || 'Failed to create object') +
          '</div>';
        if (typeof lucide !== 'undefined') {
          lucide.createIcons({ attrs: { class: ['lucide'] }, nameAttr: 'data-lucide' });
        }
      }
      console.warn('copilot: object creation failed', err);
      _scrollToBottom();
    });
}

function _handleCancelCreate(card) {
  card.classList.add('copilot-create-cancelled');
  var actionsEl = card.querySelector('.copilot-create-actions');
  if (actionsEl) {
    actionsEl.innerHTML = '<span class="copilot-approval-cancelled">Creation cancelled</span>';
  }
}

/**
 * Extract the local name from an IRI.
 * e.g. "http://example.org/vocab#Task" → "Task"
 *      "urn:sempkm:model:basic-pkm:Note" → "Note"
 */
function _iriLocalName(iri) {
  if (!iri) return '';
  var hashIdx = iri.lastIndexOf('#');
  if (hashIdx >= 0) return iri.substring(hashIdx + 1);
  var slashIdx = iri.lastIndexOf('/');
  if (slashIdx >= 0) return iri.substring(slashIdx + 1);
  var colonIdx = iri.lastIndexOf(':');
  if (colonIdx >= 0) return iri.substring(colonIdx + 1);
  return iri;
}
