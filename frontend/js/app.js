// ==================== CONFIGURACIÓN Y VARIABLES GLOBALES ====================
const API_URL = 'https://claro-asistente-ia.onrender.com'; // Tu URL de Render



// Configuración de tokens
const TOKEN_CONFIG = {
    MAX_TOKENS: 1000,
    CHARS_PER_TOKEN: 3.5 // Promedio fijo entre 3 y 4
};

// Estado global de la aplicación
const appState = {
    currentMode: 'busqueda',
    conversationHistory: [],
    tasks: {
        reminders: [],
        notes: [],
        calendar: []
    }
};

// Elementos del DOM
const elements = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    overlay: document.getElementById('overlay'),
    menuToggle: document.getElementById('menuToggle'),
    navItems: document.querySelectorAll('.nav-item'),
    tasksContainer: document.getElementById('tasksContainer'),
    taskHeaders: document.querySelectorAll('.task-header'),
    newConversationBtn: document.getElementById('newConversationBtn'),
    clearTasksBtn: document.getElementById('clear-tasks'),
    
    // Main content
    welcomePage: document.getElementById('welcomePage'),
    chatPage: document.getElementById('chatPage'),
    chatHistory: document.getElementById('chatHistory'),
    
    // Input
    userInput: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    addBtn: document.getElementById('addBtn'),
    actionMenu: document.getElementById('actionMenu'),
    actionItems: document.querySelectorAll('.action-item'),
    
    // Token counter - NUEVO
    tokenCounter: document.getElementById('tokenCounter'),
    currentTokens: document.getElementById('currentTokens'),
    maxTokens: document.getElementById('maxTokens'),
    
    // Suggestions
    suggestionCards: document.querySelectorAll('.suggestion-card'),
    
    // Loading
    loadingOverlay: document.getElementById('loadingOverlay'),
    
    // Task lists
    remindersList: document.getElementById('reminders-list'),
    notesList: document.getElementById('notes-list'),
    calendarList: document.getElementById('calendar-list')
};

// ==================== FUNCIONES DE TOKENS ====================
/**
 * Estima tokens usando un promedio fijo de 3.5 caracteres por token
 */
function estimateTokens(text) {
    if (!text || text.length === 0) {
        return 0;
    }
    return Math.ceil(text.length / TOKEN_CONFIG.CHARS_PER_TOKEN);
}

/**
 * Actualiza el contador visual y el estado del botón
 */
function updateTokenCounter(tokens) {
    if (!elements.currentTokens) return;
    
    elements.currentTokens.textContent = tokens;
    
    // Cambiar color según porcentaje
    const percentage = (tokens / TOKEN_CONFIG.MAX_TOKENS) * 100;
    
    // Deshabilitar botón si excede el límite
    const exceedsLimit = tokens > TOKEN_CONFIG.MAX_TOKENS;
    elements.sendBtn.disabled = exceedsLimit;
    
    if (exceedsLimit) {
        elements.tokenCounter.style.color = '#dc3545';
        elements.tokenCounter.style.fontWeight = 'bold';
        elements.sendBtn.style.opacity = '0.5';
        elements.sendBtn.style.cursor = 'not-allowed';
    } else if (percentage >= 75) {
        elements.tokenCounter.style.color = '#ff9800';
        elements.tokenCounter.style.fontWeight = '500';
        elements.sendBtn.style.opacity = '1';
        elements.sendBtn.style.cursor = 'pointer';
    } else if (percentage >= 50) {
        elements.tokenCounter.style.color = '#ffc107';
        elements.tokenCounter.style.fontWeight = 'normal';
        elements.sendBtn.style.opacity = '1';
        elements.sendBtn.style.cursor = 'pointer';
    } else {
        elements.tokenCounter.style.color = '#999';
        elements.tokenCounter.style.fontWeight = 'normal';
        elements.sendBtn.style.opacity = '1';
        elements.sendBtn.style.cursor = 'pointer';
    }
}

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadFromLocalStorage();
    
    // Inicializar contador de tokens
    if (elements.maxTokens) {
        elements.maxTokens.textContent = TOKEN_CONFIG.MAX_TOKENS;
    }
    updateTokenCounter(0);
});

function initializeEventListeners() {
    // Toggle sidebar (móvil)
    elements.menuToggle.addEventListener('click', toggleSidebar);
    elements.overlay.addEventListener('click', closeSidebar);
    
    // Navegación sidebar
    elements.navItems.forEach(item => {
        item.addEventListener('click', handleNavigation);
    });
    
    // Nueva conversación
    if (elements.newConversationBtn) {
        elements.newConversationBtn.addEventListener('click', startNewConversation);
    }
    
    // Task headers
    elements.taskHeaders.forEach(header => {
        header.addEventListener('click', toggleTaskCard);
    });
    
    // Limpiar tareas
    if (elements.clearTasksBtn) {
        elements.clearTasksBtn.addEventListener('click', clearAllTasks);
    }
    
    // Botón +
    elements.addBtn.addEventListener('click', toggleActionMenu);
    
    // Botón enviar
    if (elements.sendBtn) {
        elements.sendBtn.addEventListener('click', function() {
            const text = elements.userInput.value.trim();
            if (text && !elements.sendBtn.disabled) {
                sendMessage(text);
                elements.userInput.value = '';
                updateTokenCounter(0);
            }
        });
    }
    
    // Action items
    elements.actionItems.forEach(item => {
        item.addEventListener('click', selectAction);
    });
    
    // Suggestion cards
    elements.suggestionCards.forEach(card => {
        card.addEventListener('click', handleSuggestionClick);
    });
    
    // Input de usuario - actualizar tokens en tiempo real
    elements.userInput.addEventListener('input', function() {
        const tokens = estimateTokens(this.value);
        updateTokenCounter(tokens);
    });

    // Enter para enviar
    elements.userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && this.value.trim() && !elements.sendBtn.disabled) {
            sendMessage(this.value.trim());
            this.value = '';
            updateTokenCounter(0);
        }
    });
    
    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', handleOutsideClick);
}

// ==================== SIDEBAR FUNCTIONS ====================
function toggleSidebar() {
    elements.sidebar.classList.toggle('active');
    elements.overlay.classList.toggle('active');
}

function closeSidebar() {
    elements.sidebar.classList.remove('active');
    elements.overlay.classList.remove('active');
}

function handleNavigation(e) {
    const section = this.getAttribute('data-section');
    
    if (section === 'home') {
        startNewConversation();
        return;
    }
    
    elements.navItems.forEach(item => item.classList.remove('active'));
    this.classList.add('active');
    
    if (section === 'tasks') {
        elements.tasksContainer.classList.toggle('active');
    } else {
        elements.tasksContainer.classList.remove('active');
    }
    
    if (window.innerWidth < 900) {
        closeSidebar();
    }
}

// ==================== NUEVA CONVERSACIÓN ====================
function startNewConversation() {
    appState.conversationHistory = [];
    elements.chatHistory.innerHTML = '';
    elements.welcomePage.style.display = 'flex';
    elements.chatPage.style.display = 'none';
    saveToLocalStorage();
    
    elements.navItems.forEach(item => item.classList.remove('active'));
    if (elements.newConversationBtn) {
        elements.newConversationBtn.classList.add('active');
    }
    elements.tasksContainer.classList.remove('active');
    
    if (window.innerWidth < 900) {
        closeSidebar();
    }
}

function toggleTaskCard(e) {
    const body = this.nextElementSibling;
    const isOpen = body.classList.contains('open');
    
    document.querySelectorAll('.task-body').forEach(b => b.classList.remove('open'));
    document.querySelectorAll('.task-header').forEach(h => h.classList.remove('collapsed'));
    
    if (!isOpen) {
        body.classList.add('open');
        this.classList.add('collapsed');
    }
}

// ==================== ACTION MENU FUNCTIONS ====================
function toggleActionMenu(e) {
    e.stopPropagation();
    elements.actionMenu.classList.toggle('active');
}

function selectAction(e) {
    const action = this.getAttribute('data-action');
    
    elements.actionItems.forEach(item => item.classList.remove('selected'));
    this.classList.add('selected');
    
    const placeholders = {
        'aprende': 'Pregunta sobre cursos de aprende.org',
        'busqueda': 'Pregunta lo que quieras',
        'tareas': 'Crea o asigna una tarea...',
        'aprende-estudia': 'Pide un resumen o lección...',
        'productividad': 'Organiza tu trabajo...'
    };
    
    elements.userInput.placeholder = placeholders[action] || 'Pregunta lo que quieras';
    appState.currentMode = action;
    
    elements.actionMenu.classList.remove('active');
}

function handleOutsideClick(e) {
    const menu = elements.actionMenu;
    const addBtn = e.target.closest('.add-btn');
    const menuItem = e.target.closest('.action-item');
    
    if (!addBtn && !menuItem && menu.classList.contains('active')) {
        menu.classList.remove('active');
    }
}

// ==================== SUGGESTION CARDS ====================
function handleSuggestionClick(e) {
    const text = this.querySelector('.card-desc').textContent.replace(/['"]/g, '');
    sendMessage(text);
}

// ==================== CHAT FUNCTIONS CON API ====================
function sendMessage(text) {
    if (!text || !text.trim()) return;
    
    showChatView();
    addMessage('user', text);
    showLoading();
    
    callAPI(text)
        .then(response => {
            addMessage('bot', response);
            
            if (isTaskMessage(text, response)) {
                processTask(text, response);
            }
        })
        .catch(error => {
            console.error('Error completo:', error);
            
            let errorMessage = 'Lo siento, ocurrió un error al procesar tu solicitud. Por favor, intenta nuevamente.';
            
            if (error.status === 429 || 
                (error.message && (error.message.toLowerCase().includes('token') || 
                                  error.message.toLowerCase().includes('limit') ||
                                  error.message.toLowerCase().includes('rate')))) {
                errorMessage = 'Lo sentimos, has alcanzado tu límite de tokens. 🚫 Te recomendamos actualizar a una cuenta Pro para seguir disfrutando sin interrupciones.';
            } else if (!navigator.onLine) {
                errorMessage = 'No hay conexión a internet. Por favor, verifica tu conexión e intenta nuevamente.';
            }
            
            addMessage('bot', errorMessage);
        })
        .finally(() => {
            hideLoading();
            saveToLocalStorage();
        });
}

// ==================== API CALLS ====================
async function callAPI(message) {
    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                action: appState.currentMode
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            return data.response;
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

function showChatView() {
    elements.welcomePage.style.display = 'none';
    elements.chatPage.style.display = 'flex';
}

function addMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'msg ' + type;
    
    const formattedContent = formatMessage(content);
    messageDiv.innerHTML = formattedContent;
    
    elements.chatHistory.appendChild(messageDiv);
    
    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
    
    appState.conversationHistory.push({ 
        type, 
        content: content,
        timestamp: new Date().toISOString() 
    });
}

// ==================== FORMATEAR MENSAJES ====================
function formatMessage(content) {
    content = content.replace(/<!--[\s\S]*?-->/g, '');
    content = content.replace(/<!-+/g, '');
    content = content.replace(/-+>/g, '');
    
    const escapeHtml = (text) => {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
        };
        return text.replace(/[&<>]/g, m => map[m]);
    };
    
    content = content.replace(/(?:\|?.+\|.+\n(?:\|?[-:| ]+)+\n(?:\|?.+\|.+\n?)+)/g, (tableMatch) => {
        const rows = tableMatch.trim().split('\n').filter(row => row.trim());
        
        if (rows.length < 2) return tableMatch;
        
        let tableHtml = '<div class="table-container"><table class="markdown-table">';
        
        rows.forEach((row, rowIndex) => {
            const cleanRow = row.trim().replace(/^\||\|$/g, '');
            const cells = cleanRow.split('|').map(cell => cell.trim());
            
            if (cells.length === 0) return;
            
            const isHeaderRow = rowIndex === 0;
            const isSeparatorRow = rowIndex === 1 && cells.every(cell => cell.replace(/[-:]/g, '').trim() === '');
            
            if (isSeparatorRow) {
                return;
            }
            
            tableHtml += '<tr>';
            
            cells.forEach((cell, cellIndex) => {
                let cellContent = escapeHtml(cell);
                
                cellContent = cellContent
                    .replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>')
                    .replace(/(?<!\*)\*([^\*]+)\*(?!\*)/g, '<em>$1</em>')
                    .replace(/`([^`]+)`/g, '<code class="msg-code">$1</code>')
                    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="msg-link">$1</a>');
                
                const tag = isHeaderRow ? 'th' : 'td';
                tableHtml += `<${tag}>${cellContent}</${tag}>`;
            });
            
            tableHtml += '</tr>';
        });
        
        tableHtml += '</table></div>';
        return tableHtml;
    });
    
    let lines = content.split('\n');
    
    let formatted = lines.map((line) => {
        if (line.includes('</table>') || line.includes('<div class="table-container">')) {
            return line;
        }
        
        if (line.trim().match(/^-{3,}$/)) {
            return '<hr class="msg-divider" />';
        }
        
        if (line.trim() === '') {
            return '<div class="msg-spacer"></div>';
        }
        
        if (line.startsWith('### ')) {
            return `<h3 class="msg-header">${escapeHtml(line.substring(4))}</h3>`;
        }
        if (line.startsWith('## ')) {
            return `<h2 class="msg-header">${escapeHtml(line.substring(3))}</h2>`;
        }
        if (line.startsWith('# ')) {
            return `<h1 class="msg-header">${escapeHtml(line.substring(2))}</h1>`;
        }
        
        if (line.startsWith('> ')) {
            return `<div class="msg-quote">${escapeHtml(line.substring(2))}</div>`;
        }
        
        if (line.match(/^[\s]*[-\*•]\s+/)) {
            const listContent = line.replace(/^[\s]*[-\*•]\s+/, '');
            return `<li class="msg-list-item">${escapeHtml(listContent)}</li>`;
        }
        
        if (line.match(/^[\s]*\d+\.\s+/)) {
            const listContent = line.replace(/^[\s]*\d+\.\s+/, '');
            return `<li class="msg-list-item numbered">${escapeHtml(listContent)}</li>`;
        }
        
        return `<p class="msg-paragraph">${escapeHtml(line)}</p>`;
    });
    
    let html = formatted.join('');
    
    html = html.replace(/(?![^<]*<\/table>)\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?![^<]*<\/table>)(?<!\*)\*([^\*]+)\*(?!\*)/g, '<em>$1</em>');
    html = html.replace(/(?![^<]*<\/table>)`([^`]+)`/g, '<code class="msg-code">$1</code>');
    html = html.replace(/(?![^<]*<\/table>)\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="msg-link">$1</a>');
    html = html.replace(/(?![^<]*<\/table>)(?<!href="|">)(https?:\/\/[^\s<>"]+)(?![^<]*<\/a>)/g, function(match) {
        return `<a href="${match}" target="_blank" rel="noopener" class="msg-link">${match}</a>`;
    });
    
    html = html.replace(/✅/g, '<span style="color: #28a745;">✅</span>');
    html = html.replace(/📝/g, '<span style="color: #17a2b8;">📝</span>');
    html = html.replace(/📅/g, '<span style="color: #ffc107;">📅</span>');
    html = html.replace(/❌/g, '<span style="color: #dc3545;">❌</span>');
    html = html.replace(/⚠️/g, '<span style="color: #ff9800;">⚠️</span>');
    html = html.replace(/😊/g, '<span style="font-size: 1.2em;">😊</span>');
    
    return html;
}

// ==================== TASK MANAGEMENT ====================
function isTaskMessage(userMsg, botMsg) {
    const lowerUserMsg = userMsg.toLowerCase();
    const lowerBotMsg = botMsg.toLowerCase();
    
    // PRIMERO: Excluir consultas generales que NO son tareas
    if (lowerUserMsg.includes('dime') || 
        lowerUserMsg.includes('cuales') || 
        lowerUserMsg.includes('cuáles') ||
        lowerUserMsg.includes('qué') ||
        lowerUserMsg.includes('que son') ||
        lowerUserMsg.includes('dame') ||
        lowerUserMsg.includes('muestra') ||
        lowerUserMsg.includes('cual es') ||
        lowerUserMsg.includes('cuál es')) {
        // Solo es tarea si el BOT responde con los emojis específicos
        if (botMsg.includes('✅') || botMsg.includes('📝') || botMsg.includes('📅')) {
            // Continuar con la detección normal
        } else {
            return false; // NO es una tarea
        }
    }
    
    // Ahora sí, detectar si es tarea
    return botMsg.includes('✅') || 
           botMsg.includes('📝') || 
           botMsg.includes('📅') ||
           lowerUserMsg.includes('recordar') ||
           lowerUserMsg.includes('recuerdame') ||
           lowerUserMsg.includes('recuérdame') ||
           lowerUserMsg.includes('avisame') ||
           lowerUserMsg.includes('avísame') ||
           lowerUserMsg.includes('nota') ||
           lowerUserMsg.includes('anota') ||
           lowerUserMsg.includes('apunta') ||
           lowerUserMsg.includes('guardar') ||
           lowerUserMsg.includes('agendar') ||
           lowerUserMsg.includes('agenda') ||
           lowerUserMsg.includes('reunion') ||
           lowerUserMsg.includes('reunión') ||
           lowerUserMsg.includes('cita') ||
           lowerUserMsg.includes('evento') ||
           lowerUserMsg.includes('programar') ||
           lowerBotMsg.includes('recordatorio') ||
           lowerBotMsg.includes('nota') ||
           lowerBotMsg.includes('agendado') ||
           lowerBotMsg.includes('evento');
}

function processTask(userMessage, botResponse) {
    const timestamp = new Date().toLocaleString('es-MX', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    const task = {
        content: userMessage,
        response: botResponse,
        created_at: timestamp,
        completed: false,
        id: Date.now() + Math.random().toString(36).substr(2, 9)
    };
    
    let taskType = null;
    const lowerUserMsg = userMessage.toLowerCase();
    const lowerBotMsg = botResponse.toLowerCase();
    
    if (lowerUserMsg.includes('recordar') || 
        lowerUserMsg.includes('recuerdame') || 
        lowerUserMsg.includes('recuérdame') ||
        lowerUserMsg.includes('avisame') ||
        lowerUserMsg.includes('avísame') ||
        lowerUserMsg.includes('recordatorio') ||
        (botResponse.includes('✅') && !lowerUserMsg.includes('agendar')) ||
        (lowerBotMsg.includes('recordatorio') && !lowerBotMsg.includes('agendado'))) {
        taskType = 'reminders';
    } 
    else if (lowerUserMsg.includes('agendar') || 
             lowerUserMsg.includes('agenda ') ||
             lowerUserMsg.includes('programar') ||
             (lowerUserMsg.includes('cita') && !lowerUserMsg.includes('recordar')) ||
             botResponse.includes('📅') ||
             lowerBotMsg.includes('agendado') ||
             lowerBotMsg.includes('he agendado')) {
        taskType = 'calendar';
    } 
    else if (lowerUserMsg.includes('nota') || 
             lowerUserMsg.includes('anota') || 
             lowerUserMsg.includes('apunta') ||
             lowerUserMsg.includes('guardar') ||
             lowerUserMsg.includes('guarda') ||
             botResponse.includes('📝') ||
             lowerBotMsg.includes('nota guardada') ||
             lowerBotMsg.includes('he guardado')) {
        taskType = 'notes';
    }
    
    if (!taskType) {
        taskType = 'reminders';
    }
    
    if (!appState.tasks[taskType]) {
        appState.tasks[taskType] = [];
    }
    
    appState.tasks[taskType].push(task);
    updateTasksUI();
    
    if (elements.tasksContainer) {
        elements.tasksContainer.classList.add('active');
    }
    
    expandTaskSection(taskType);
    saveToLocalStorage();
}

function expandTaskSection(taskType) {
    document.querySelectorAll('.task-body').forEach(body => body.classList.remove('open'));
    document.querySelectorAll('.task-header').forEach(header => header.classList.remove('collapsed'));
    
    const targetHeader = document.querySelector(`.task-header[data-task-type="${taskType}"]`);
    if (targetHeader) {
        const targetBody = targetHeader.nextElementSibling;
        targetBody.classList.add('open');
        targetHeader.classList.add('collapsed');
    }
}

function updateTasksUI() {
    updateTaskList(elements.remindersList, appState.tasks.reminders, 'reminders', 'No hay recordatorios pendientes');
    updateTaskList(elements.notesList, appState.tasks.notes, 'notes', 'No hay notas');
    updateTaskList(elements.calendarList, appState.tasks.calendar, 'calendar', 'No hay eventos programados');
    updateTaskBadges();
}

function updateTaskBadges() {
    const totalTasks = (appState.tasks.reminders?.length || 0) + 
                      (appState.tasks.notes?.length || 0) + 
                      (appState.tasks.calendar?.length || 0);
    
    const tasksNavBtn = document.getElementById('tasksNavBtn');
    if (tasksNavBtn) {
        const textSpan = tasksNavBtn.querySelector('span');
        if (textSpan) {
            let badgeText = 'Gestión de tareas';
            if (totalTasks > 0) {
                badgeText += ` (${totalTasks})`;
            }
            textSpan.textContent = badgeText;
        }
    }
}

function updateTaskList(container, tasks, taskType, emptyMessage) {
    if (!container) return;
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `<div class="empty-task-message">${emptyMessage}</div>`;
        return;
    }
    
    let html = '';
    tasks.forEach((task, idx) => {
        const displayContent = task.content.length > 80 
            ? task.content.substring(0, 80) + '...' 
            : task.content;
            
        html += `
            <div class="task-item" data-task-id="${task.id}">
                <div class="task-content">${escapeHtml(displayContent)}</div>
                <div class="task-time">Creado: ${task.created_at}</div>
                <button class="task-delete" onclick="deleteTask('${taskType}', ${idx})" title="Eliminar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function deleteTask(taskType, index) {
    appState.tasks[taskType].splice(index, 1);
    updateTasksUI();
    saveToLocalStorage();
}

function clearAllTasks() {
    appState.tasks = { 
        reminders: [], 
        notes: [], 
        calendar: [] 
    };
    updateTasksUI();
    saveToLocalStorage();
}

window.deleteTask = deleteTask;
window.clearAllTasks = clearAllTasks;

// ==================== LOADING ====================
function showLoading() {
    elements.loadingOverlay.classList.add('active');
}

function hideLoading() {
    elements.loadingOverlay.classList.remove('active');
}

// ==================== LOCAL STORAGE ====================
function saveToLocalStorage() {
    try {
        const data = {
            conversationHistory: appState.conversationHistory.slice(-50),
            tasks: appState.tasks,
            currentMode: appState.currentMode,
            sessionId: sessionStorage.getItem('claroAssistant_sessionId')
        };
        localStorage.setItem('claroAssistant_state', JSON.stringify(data));
    } catch (e) {
        console.error('Error guardando en localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        let currentSessionId = sessionStorage.getItem('claroAssistant_sessionId');
        
        if (!currentSessionId) {
            currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('claroAssistant_sessionId', currentSessionId);
            localStorage.removeItem('claroAssistant_state');
            console.log('Nueva sesion iniciada');
            return;
        }
        
        const saved = localStorage.getItem('claroAssistant_state');
        if (saved) {
            const data = JSON.parse(saved);
            
            if (data.sessionId === currentSessionId) {
                appState.conversationHistory = data.conversationHistory || [];
                appState.tasks = data.tasks || { reminders: [], notes: [], calendar: [] };
                appState.currentMode = data.currentMode || 'busqueda';
                
                if (appState.conversationHistory.length > 0) {
                    showChatView();
                    elements.chatHistory.innerHTML = '';
                    appState.conversationHistory.forEach(msg => {
                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'msg ' + msg.type;
                        messageDiv.innerHTML = formatMessage(msg.content);
                        elements.chatHistory.appendChild(messageDiv);
                    });
                    console.log('Conversacion restaurada');
                }
                
                updateTasksUI();
                console.log('Tareas cargadas:', appState.tasks);
            } else {
                console.log('Nueva pestana - chat limpio');
            }
        }
    } catch (e) {
        console.error('Error cargando desde localStorage:', e);
    }
}

// ==================== RESPONSIVE HANDLERS ====================
window.addEventListener('resize', function() {
    if (window.innerWidth >= 900) {
        elements.sidebar.classList.remove('active');
        elements.overlay.classList.remove('active');
    }
}); 

// ==================== CONSOLE INFO ====================
console.log('%c🚀 Claro·Assistant Initialized', 'color: #DA291C; font-size: 16px; font-weight: bold;');
console.log('%cAPI URL:', 'color: #00BCD4; font-weight: bold;', API_URL);
console.log('%cToken Limit:', 'color: #28a745; font-weight: bold;', TOKEN_CONFIG.MAX_TOKENS);
console.log('%cReady to chat!', 'color: #28a745;');
