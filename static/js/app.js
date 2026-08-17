// DOM Elements - Authentication
const loginOverlay = document.getElementById('login-overlay');
const appContainer = document.getElementById('app-container');
const authTitle = document.getElementById('auth-title');
const authSubtitle = document.getElementById('auth-subtitle');
const authAlert = document.getElementById('auth-alert');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const linkShowRegister = document.getElementById('link-show-register');
const toggleAuthText = document.getElementById('toggle-auth-text');

const userEmailDisplay = document.getElementById('user-email-display');
const userRoleDisplay = document.getElementById('user-role-display');
const btnLogout = document.getElementById('btn-logout');
const adminNavItem = document.getElementById('admin-nav-item');
const chatNavItem = document.getElementById('chat-nav-item');
const sidebarFilesStatus = document.getElementById('sidebar-files-status');

// DOM Elements - App Views
const btnChatView = document.getElementById('btn-chat-view');
const btnAdminView = document.getElementById('btn-admin-view');
const chatView = document.getElementById('chat-view');
const adminView = document.getElementById('admin-view');
const viewTitle = document.getElementById('view-title');
const viewDescription = document.getElementById('view-description');

// DOM Elements - Chat Interface
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const chatHistory = document.getElementById('chat-history');
const chatBottom = document.getElementById('chat-bottom');
const typingIndicator = document.getElementById('typing-indicator');
const btnClearChat = document.getElementById('btn-clear-chat');

// DOM Elements - Ingestion Panel
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadStatusCard = document.getElementById('upload-status-card');
const uploadFilename = document.getElementById('upload-filename');
const uploadBadge = document.getElementById('upload-badge');
const uploadStatusMsg = document.getElementById('upload-status-msg');
const uploadProgressBar = document.getElementById('upload-progress-bar');

const docSearchInput = document.getElementById('doc-search-input');
const documentsTableBody = document.getElementById('documents-table-body');
const btnRefreshDocs = document.getElementById('btn-refresh-docs');
const fileCountBadge = document.getElementById('file-count-badge');

let ingestedFiles = [];
let currentUser = null;

// --- Authentication UI Toggles ---
linkShowRegister.addEventListener('click', (e) => {
    e.preventDefault();
    authAlert.classList.add('d-none');
    
    if (registerForm.classList.contains('d-none')) {
        // Switch to Sign Up
        registerForm.classList.remove('d-none');
        loginForm.classList.add('d-none');
        authTitle.innerText = "Create Account";
        authSubtitle.innerText = "Sign up as a new business user";
        toggleAuthText.innerHTML = 'Already have an account? <a href="#" id="link-show-register" class="text-primary text-decoration-none">Sign In</a>';
        
        // Rebind click event
        document.getElementById('link-show-register').addEventListener('click', toggleAuthView);
    }
});

function toggleAuthView(e) {
    e.preventDefault();
    authAlert.classList.add('d-none');
    
    registerForm.classList.add('d-none');
    loginForm.classList.remove('d-none');
    authTitle.innerText = "Welcome to CognitiveRAG";
    authSubtitle.innerText = "Log in to query internal knowledge documents";
    toggleAuthText.innerHTML = 'Don\'t have an account? <a href="#" id="link-show-register" class="text-primary text-decoration-none">Sign Up</a>';
    
    // Rebind original event
    document.getElementById('link-show-register').addEventListener('click', (ev) => {
        ev.preventDefault();
        linkShowRegister.click();
    });
}

// --- Session Verification ---
async function checkSession() {
    try {
        const response = await fetch('/session');
        const data = await response.json();
        
        if (data.logged_in) {
            currentUser = data.user;
            
            // Render view states
            userEmailDisplay.innerText = currentUser.email;
            userRoleDisplay.innerText = currentUser.role === 'admin' ? 'Admin' : 'User';
            userRoleDisplay.className = `badge ${currentUser.role === 'admin' ? 'bg-warning text-dark' : 'bg-secondary-subtle text-secondary-emphasis'} font-heading`;
            
            // Role-based visibility
            if (currentUser.role === 'admin') {
                adminNavItem.classList.remove('d-none');
                chatNavItem.classList.add('d-none');
                sidebarFilesStatus.classList.remove('d-none');
                toggleView('admin'); // Force admins to stay in Ingestion view
            } else {
                adminNavItem.classList.add('d-none');
                chatNavItem.classList.remove('d-none');
                sidebarFilesStatus.classList.add('d-none');
                toggleView('chat'); // Force regular users to stay in chat view
            }
            
            // Switch views
            loginOverlay.classList.add('d-none');
            appContainer.classList.remove('d-none');
            
            // Load messages
            loadChatHistory();
        } else {
            currentUser = null;
            appContainer.classList.add('d-none');
            loginOverlay.classList.remove('d-none');
        }
    } catch (err) {
        console.error("Session check error:", err);
    }
}

// --- Auth Event Listeners ---
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    authAlert.classList.add('d-none');
    
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        
        if (data.success) {
            loginForm.reset();
            checkSession();
        } else {
            authAlert.innerText = data.message;
            authAlert.classList.remove('d-none');
        }
    } catch (err) {
        console.error("Login request error:", err);
        authAlert.innerText = "Failed to connect to backend server.";
        authAlert.classList.remove('d-none');
    }
});

registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const confirmPassword = document.getElementById('register-confirm-password').value;
    
    authAlert.classList.add('d-none');
    
    if (password !== confirmPassword) {
        authAlert.innerText = "Passwords do not match!";
        authAlert.classList.remove('d-none');
        return;
    }
    
    try {
        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await response.json();
        
        if (data.success) {
            alert("Registration successful! You can now log in.");
            registerForm.reset();
            // Trigger UI switch back to Login
            const mockEvent = { preventDefault: () => {} };
            toggleAuthView(mockEvent);
        } else {
            authAlert.innerText = data.message;
            authAlert.classList.remove('d-none');
        }
    } catch (err) {
        console.error("Register request error:", err);
        authAlert.innerText = "Failed to connect to backend server.";
        authAlert.classList.remove('d-none');
    }
});

btnLogout.addEventListener('click', async () => {
    try {
        const response = await fetch('/logout', { method: 'POST' });
        if (response.ok) {
            checkSession();
        }
    } catch (err) {
        console.error("Logout request error:", err);
    }
});

// --- View Toggling ---
btnChatView.addEventListener('click', (e) => {
    e.preventDefault();
    toggleView('chat');
});

btnAdminView.addEventListener('click', (e) => {
    e.preventDefault();
    if (currentUser && currentUser.role === 'admin') {
        toggleView('admin');
    }
});

function toggleView(view) {
    if (view === 'chat') {
        chatView.classList.remove('d-none');
        adminView.classList.add('d-none');
        btnChatView.classList.add('active');
        btnChatView.classList.remove('text-secondary');
        btnChatView.classList.add('text-white');
        btnAdminView.classList.remove('active');
        btnAdminView.classList.add('text-secondary');
        btnAdminView.classList.remove('text-white');
        viewTitle.innerText = "User Chatroom";
        viewDescription.innerText = "Ask questions based on ingested business documents";
        scrollToBottom();
    } else {
        chatView.classList.add('d-none');
        adminView.classList.remove('d-none');
        btnAdminView.classList.add('active');
        btnAdminView.classList.remove('text-secondary');
        btnAdminView.classList.add('text-white');
        btnChatView.classList.remove('active');
        btnChatView.classList.add('text-secondary');
        btnChatView.classList.remove('text-white');
        viewTitle.innerText = "Knowledge Ingestion Dashboard";
        viewDescription.innerText = "Upload and manage business document assets";
        loadDocuments();
    }
}

// --- Helper Functions ---
function scrollToBottom() {
    chatBottom.scrollIntoView({ behavior: 'smooth' });
}

// Simple Markdown-to-HTML parser for rendering chatbot output nicely
function parseMarkdown(text) {
    if (!text) return "";
    
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // 1. Codeblocks ```language ... ```
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
        return `
            <div class="code-container" style="position: relative; margin-top: 10px;">
                <button class="copy-btn btn-sm" onclick="copyToClipboard(this)"><i class="bi bi-clipboard"></i> Copy</button>
                <pre><code>${code.trim()}</code></pre>
            </div>
        `;
    });

    // 2. Inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // 3. Bold text **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // 4. Italic text *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // 5. Lists: replace "- item" or "* item" lines
    const lines = html.split('\n');
    let inList = false;
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith('- ') || line.startsWith('* ')) {
            let itemContent = line.substring(2);
            if (!inList) {
                lines[i] = '<ul><li>' + itemContent + '</li>';
                inList = true;
            } else {
                lines[i] = '<li>' + itemContent + '</li>';
            }
        } else {
            if (inList) {
                lines[i - 1] = lines[i - 1] + '</ul>';
                inList = false;
            }
        }
    }
    if (inList) {
        lines[lines.length - 1] = lines[lines.length - 1] + '</ul>';
    }
    
    html = lines.join('\n');
    html = html.replace(/\n/g, '<br>');
    html = html.replace(/<\/ul><br>/g, '</ul>');
    html = html.replace(/<\/pre><br>/g, '</pre>');
    html = html.replace(/<\/div><br>/g, '</div>');

    return html;
}

// Global Clipboard Copy Handler
window.copyToClipboard = function(btn) {
    const container = btn.closest('.code-container');
    const codeEl = container.querySelector('code');
    const textToCopy = codeEl.innerText || codeEl.textContent;
    
    navigator.clipboard.writeText(textToCopy).then(() => {
        // Success feedback on button
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-lg"></i> Copied!';
        btn.style.color = "var(--success)";
        btn.style.borderColor = "var(--success)";
        
        // Show floating copy toast
        const toast = document.getElementById('copy-toast');
        if (toast) {
            toast.classList.add('show');
        }
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.color = "";
            btn.style.borderColor = "";
            if (toast) {
                toast.classList.remove('show');
            }
        }, 1800);
    }).catch(err => {
        console.error("Clipboard copy failed:", err);
    });
};

// --- Chat History Management ---
async function loadChatHistory() {
    try {
        const response = await fetch('/history');
        const data = await response.json();
        
        // Clear history box (keep welcome bubble)
        const welcomeBubbleHTML = `
            <div class="message-bubble bot-message p-3 rounded-4 d-flex align-items-start gap-3">
                <div class="bot-avatar bg-primary text-white d-flex align-items-center justify-content-center">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    <h6 class="m-0 text-white font-heading mb-1">CognitiveRAG System</h6>
                    <p class="mb-0">Hello! I am your context-aware intelligence assistant. Upload documents in the **Knowledge Ingestion** tab, and I will search those documents to answer your questions accurately.</p>
                    <div class="suggested-queries mt-3 d-flex flex-wrap gap-2">
                        <button class="btn btn-outline-secondary btn-sm rounded-pill px-3 sample-query-btn" data-query="What is this chatbot and how does it work?">
                            What is this chatbot?
                        </button>
                        <button class="btn btn-outline-secondary btn-sm rounded-pill px-3 sample-query-btn" data-query="What is the store manager name and emergency gate code?">
                            Suzuki emergency codes
                        </button>
                        <button class="btn btn-outline-secondary btn-sm rounded-pill px-3 sample-query-btn" data-query="Tell me about Scheduled Maintenance intervals and engine oil specifications.">
                            Car Maintenance rules
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        chatHistory.innerHTML = welcomeBubbleHTML;
        
        // Setup suggested query buttons click events again
        document.querySelectorAll('.sample-query-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                chatInput.value = query;
                chatInput.focus();
            });
        });
        
        if (data.success && data.history.length > 0) {
            data.history.forEach(msg => {
                addMessageBubble(msg.message, msg.sender, [], false);
            });
            scrollToBottom();
        }
    } catch (err) {
        console.error("Error loading chat logs:", err);
    }
}

btnClearChat.addEventListener('click', async () => {
    if (!confirm("Are you sure you want to delete all conversation history? This cannot be undone.")) {
        return;
    }
    
    try {
        const response = await fetch('/clear-history', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            loadChatHistory();
        } else {
            alert("Error clearing history: " + data.message);
        }
    } catch (err) {
        console.error("Error clearing chat log:", err);
    }
});

// --- Document Loading (Admin Only) ---
async function loadDocuments() {
    if (!currentUser || currentUser.role !== 'admin') return;
    
    try {
        const response = await fetch('/documents');
        const data = await response.json();
        
        if (data.success) {
            ingestedFiles = data.documents;
            renderDocumentsTable(ingestedFiles);
            fileCountBadge.innerText = ingestedFiles.length;
        } else {
            console.error("Failed to load documents:", data.message);
        }
    } catch (err) {
        console.error("Error fetching documents:", err);
    }
}

function renderDocumentsTable(files) {
    if (files.length === 0) {
        documentsTableBody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-secondary py-5">
                    <i class="bi bi-folder-x fs-1 d-block mb-2 text-dark-subtle"></i>
                    No documents ingested yet. Upload text or PDF files to start.
                </td>
            </tr>
        `;
        return;
    }

    documentsTableBody.innerHTML = files.map(filename => {
        const ext = filename.split('.').pop().toUpperCase();
        const iconClass = ext === 'PDF' ? 'bi-file-earmark-pdf-fill text-danger' : 'bi-file-earmark-text-fill text-info';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <i class="bi ${iconClass} fs-5 me-3"></i>
                        <span class="text-white text-truncate font-sans" style="max-width: 320px;">${filename}</span>
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary font-heading" style="font-size: 0.75rem;">${ext}</span>
                </td>
                <td class="text-end">
                    <button class="btn btn-outline-danger btn-sm rounded-3 py-1 px-2 border-0" onclick="deleteDocument('${filename}')" title="Delete document">
                        <i class="bi bi-trash-fill"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

async function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete "${filename}" from the Knowledge Base?`)) {
        return;
    }
    
    try {
        const response = await fetch('/delete-document', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await response.json();
        
        if (data.success) {
            loadDocuments();
        } else {
            alert("Error deleting document: " + data.message);
        }
    } catch (err) {
        console.error("Error during deletion:", err);
        alert("Failed to connect to backend server.");
    }
}

// Search Filter
docSearchInput.addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    const filtered = ingestedFiles.filter(name => name.toLowerCase().includes(query));
    renderDocumentsTable(filtered);
});

btnRefreshDocs.addEventListener('click', loadDocuments);

// --- File Upload / Drag & Drop Handling ---
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
});

dropZone.addEventListener('drop', (e) => {
    if (!currentUser || currentUser.role !== 'admin') return;
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
        handleFileUpload(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileUpload(e.target.files[0]);
    }
});

async function handleFileUpload(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pdf' && ext !== 'txt') {
        alert("Unsupported file format! Please upload a PDF or TXT document.");
        return;
    }
    
    // Show Progress Indicator
    uploadStatusCard.classList.remove('d-none');
    uploadFilename.innerText = file.name;
    uploadBadge.innerText = "Uploading";
    uploadBadge.className = "badge bg-warning text-dark";
    uploadStatusMsg.innerText = "Uploading file to server...";
    uploadProgressBar.style.width = "40%";
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        uploadStatusMsg.innerText = "Parsing text and generating embeddings via Gemini API...";
        uploadProgressBar.style.width = "75%";
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            uploadBadge.innerText = "Success";
            uploadBadge.className = "badge bg-success";
            uploadStatusMsg.innerText = data.message;
            uploadProgressBar.style.width = "100%";
            uploadProgressBar.className = "progress-bar bg-success";
            
            loadDocuments();
            
            setTimeout(() => {
                uploadStatusCard.classList.add('d-none');
                uploadProgressBar.className = "progress-bar bg-warning progress-bar-striped progress-bar-animated";
            }, 4000);
        } else {
            showUploadError(data.message);
        }
    } catch (err) {
        console.error("Upload error:", err);
        showUploadError("Network connection error. Server might be down.");
    }
}

function showUploadError(msg) {
    uploadBadge.innerText = "Error";
    uploadBadge.className = "badge bg-danger";
    uploadStatusMsg.innerText = msg;
    uploadProgressBar.style.width = "100%";
    uploadProgressBar.className = "progress-bar bg-danger";
}

// --- Chat Interface Query Handling ---
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const queryText = chatInput.value.trim();
    if (!queryText) return;
    
    // Add user message bubble to screen
    addMessageBubble(queryText, 'user');
    chatInput.value = '';
    
    // Show typing/querying indicator
    typingIndicator.classList.remove('d-none');
    scrollToBottom();
    
    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryText })
        });
        
        if (response.status === 401) {
            typingIndicator.classList.add('d-none');
            addMessageBubble("Your session has expired. Please log in again.", 'bot');
            setTimeout(() => checkSession(), 2000);
            return;
        }
        
        if (!response.ok) {
            typingIndicator.classList.add('d-none');
            const data = await response.json();
            addMessageBubble(data.answer || "An error occurred.", 'bot');
            return;
        }
        
        typingIndicator.classList.add('d-none');
        
        // 1. Create a blank placeholder bubble for the bot response
        const bubble = document.createElement('div');
        bubble.className = `message-bubble bot-message p-3 rounded-4 d-flex align-items-start gap-3`;
        bubble.innerHTML = `
            <div class="bot-avatar bg-primary text-white d-flex align-items-center justify-content-center">
                <i class="bi bi-robot"></i>
            </div>
            <div class="message-content">
                <h6 class="m-0 text-white font-heading mb-1">CognitiveRAG System</h6>
                <div class="font-sans message-text-content"></div>
            </div>
        `;
        chatHistory.appendChild(bubble);
        scrollToBottom();
        
        const messageTextDiv = bubble.querySelector('.message-text-content');
        
        // 2. Read the SSE stream chunk by chunk
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let botText = "";
        let sources = [];
        
        // Buffer to accumulate split packets
        let buffer = "";
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunkStr = decoder.decode(value, { stream: true });
            buffer += chunkStr;
            
            const lines = buffer.split('\n');
            // Keep the last partial line in the buffer
            buffer = lines.pop();
            
            for (const line of lines) {
                const trimmedLine = line.trim();
                if (trimmedLine.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(trimmedLine.substring(6));
                        if (data.sources) {
                            sources = data.sources;
                        }
                        if (data.text) {
                            botText += data.text;
                            messageTextDiv.innerHTML = parseMarkdown(botText);
                            scrollToBottom();
                        }
                        if (data.error) {
                            messageTextDiv.innerHTML += `<br><span class="text-danger">Error: ${data.error}</span>`;
                        }
                    } catch (parseErr) {
                        // Ignore JSON parse errors for incomplete split chunks
                    }
                }
            }
        }
        
        // Process any remaining data in the buffer
        if (buffer.trim().startsWith('data: ')) {
            try {
                const data = JSON.parse(buffer.trim().substring(6));
                if (data.sources) sources = data.sources;
                if (data.text) {
                    botText += data.text;
                    messageTextDiv.innerHTML = parseMarkdown(botText);
                }
            } catch (e) {}
        }
        
        // 3. Append RAG grounding accordion if sources were matched
        if (sources && sources.length > 0) {
            const randomId = 'sources-' + Math.floor(Math.random() * 100000);
            
            const uniqueSources = {};
            sources.forEach(src => {
                if (!uniqueSources[src.filename]) {
                    uniqueSources[src.filename] = [];
                }
                uniqueSources[src.filename].push(src.chunk);
            });
            
            let sourcesListHTML = Object.entries(uniqueSources).map(([filename, chunks]) => {
                return `<li><i class="bi bi-file-earmark-check-fill text-success me-1"></i> <strong>${filename}</strong> (matching chunks: ${chunks.join(', ')})</li>`;
            }).join('');
            
            const accordionHTML = `
                <div class="card sources-card rounded-3 mt-3">
                    <div class="card-header p-2 cursor-pointer d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#${randomId}">
                        <span class="font-heading text-secondary" style="font-size: 0.75rem;"><i class="bi bi-journal-bookmark-fill me-1"></i> RAG Grounding: ${sources.length} sources matched</span>
                        <i class="bi bi-chevron-down text-secondary" style="font-size: 0.75rem;"></i>
                    </div>
                    <div id="${randomId}" class="collapse">
                        <div class="card-body p-2 border-top border-dark-subtle">
                            <ul class="list-unstyled m-0 ps-1" style="font-size: 0.7rem; color: var(--text-secondary);">
                                ${sourcesListHTML}
                            </ul>
                        </div>
                    </div>
                </div>
            `;
            messageTextDiv.innerHTML += accordionHTML;
            scrollToBottom();
        }
        
    } catch (err) {
        console.error("Chat error:", err);
        typingIndicator.classList.add('d-none');
        addMessageBubble("Sorry, I encountered an error connecting to the server. Make sure your Python backend is running.", 'bot');
    }
});

function addMessageBubble(text, sender, sources = [], animate = true) {
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${sender}-message p-3 rounded-4 d-flex align-items-start gap-3`;
    if (!animate) {
        bubble.style.animation = 'none'; // Don't animate database history messages on reload
    }
    
    let avatarHTML = '';
    let headerHTML = '';
    
    if (sender === 'bot') {
        avatarHTML = `
            <div class="bot-avatar bg-primary text-white d-flex align-items-center justify-content-center">
                <i class="bi bi-robot"></i>
            </div>
        `;
        headerHTML = `<h6 class="m-0 text-white font-heading mb-1">CognitiveRAG System</h6>`;
    } else {
        avatarHTML = `
            <div class="user-avatar d-flex align-items-center justify-content-center">
                <i class="bi bi-person-fill"></i>
            </div>
        `;
        headerHTML = `<h6 class="m-0 text-white font-heading mb-1">You</h6>`;
    }
    
    let contentHTML = parseMarkdown(text);
    
    // Append sources accordion
    if (sender === 'bot' && sources && sources.length > 0) {
        const randomId = 'sources-' + Math.floor(Math.random() * 100000);
        
        const uniqueSources = {};
        sources.forEach(src => {
            if (!uniqueSources[src.filename]) {
                uniqueSources[src.filename] = [];
            }
            uniqueSources[src.filename].push(src.chunk);
        });
        
        let sourcesListHTML = Object.entries(uniqueSources).map(([filename, chunks]) => {
            return `<li><i class="bi bi-file-earmark-check-fill text-success me-1"></i> <strong>${filename}</strong> (matching chunks: ${chunks.join(', ')})</li>`;
        }).join('');
        
        contentHTML += `
            <div class="card sources-card rounded-3 mt-3">
                <div class="card-header p-2 cursor-pointer d-flex justify-content-between align-items-center" data-bs-toggle="collapse" data-bs-target="#${randomId}">
                    <span class="font-heading text-secondary" style="font-size: 0.75rem;"><i class="bi bi-journal-bookmark-fill me-1"></i> RAG Grounding: ${sources.length} sources matched</span>
                    <i class="bi bi-chevron-down text-secondary" style="font-size: 0.75rem;"></i>
                </div>
                <div id="${randomId}" class="collapse">
                    <div class="card-body p-2 border-top border-dark-subtle">
                        <ul class="list-unstyled m-0 ps-1" style="font-size: 0.7rem; color: var(--text-secondary);">
                            ${sourcesListHTML}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }
    
    bubble.innerHTML = `
        ${avatarHTML}
        <div class="message-content">
            ${headerHTML}
            <div class="font-sans">${contentHTML}</div>
        </div>
    `;
    
    chatHistory.appendChild(bubble);
    if (animate) {
        scrollToBottom();
    }
}

// Initial Load check
window.addEventListener('DOMContentLoaded', () => {
    checkSession();
});
