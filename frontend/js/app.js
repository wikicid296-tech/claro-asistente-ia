// ==================== CONFIGURACIÓN Y VARIABLES GLOBALES ====================
const API_URL = 'https://claro-asistente-ia.onrender.com'; // Tu URL de Render

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
    
    // Suggestions
    suggestionCards: document.querySelectorAll('.suggestion-card'),
    
    // Loading
    loadingOverlay: document.getElementById('loadingOverlay'),
    
    // Task lists
    remindersList: document.getElementById('reminders-list'),
    notesList: document.getElementById('notes-list'),
    calendarList: document.getElementById('calendar-list')
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadFromLocalStorage();
});

function initializeEventListeners() {
    // Toggle sidebar (móvil)
    elements.menuToggle.addEventListener('click', toggleSidebar);
    elements.overlay.addEventListener('click', closeSidebar);
    
    // Navegación sidebar
    elements.navItems.forEach(item => {
        item.addEventListener('click', handleNavigation);
    });
    
    // Nueva conversación (SIN ALERT)
    if (elements.newConversationBtn) {
        elements.newConversationBtn.addEventListener('click', startNewConversation);
    }
    
    // Task headers (expandir/contraer)
    elements.taskHeaders.forEach(header => {
        header.addEventListener('click', toggleTaskCard);
    });
    
    // Limpiar tareas (SIN ALERT)
    if (elements.clearTasksBtn) {
        elements.clearTasksBtn.addEventListener('click', clearAllTasks);
    }
    
    // Botón + (mostrar menú de acciones)
    elements.addBtn.addEventListener('click', toggleActionMenu);
    
    // Botón enviar
    if (elements.sendBtn) {
        elements.sendBtn.addEventListener('click', function() {
            const text = elements.userInput.value.trim();
            if (text) {
                sendMessage(text);
                elements.userInput.value = '';
            }
        });
    }
    
    // Action items (opciones del menú)
    elements.actionItems.forEach(item => {
        item.addEventListener('click', selectAction);
    });
    
    // Suggestion cards
    elements.suggestionCards.forEach(card => {
        card.addEventListener('click', handleSuggestionClick);
    });
    
    // Input de usuario (Enter para enviar)
    elements.userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && this.value.trim()) {
            sendMessage(this.value.trim());
            this.value = '';
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
    
    // Si es "home", iniciar nueva conversación
    if (section === 'home') {
        startNewConversation();
        return;
    }
    
    // Remover active de todos
    elements.navItems.forEach(item => item.classList.remove('active'));
    this.classList.add('active');
    
    // Toggle tasks container
    if (section === 'tasks') {
        elements.tasksContainer.classList.toggle('active');
    } else {
        elements.tasksContainer.classList.remove('active');
    }
    
    // No cerrar sidebar en desktop, solo en móvil
    if (window.innerWidth < 900) {
        closeSidebar();
    }
}

// ==================== NUEVA CONVERSACIÓN (SIN ALERT) ====================
function startNewConversation() {
    // Limpiar historial directamente sin confirmación
    appState.conversationHistory = [];
    elements.chatHistory.innerHTML = '';
    elements.welcomePage.style.display = 'flex';
    elements.chatPage.style.display = 'none';
    saveToLocalStorage();
    
    // Activar "Nueva conversación"
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
    
    // Cerrar todos primero
    document.querySelectorAll('.task-body').forEach(b => b.classList.remove('open'));
    document.querySelectorAll('.task-header').forEach(h => h.classList.remove('collapsed'));
    
    // Abrir el clickeado si no estaba abierto
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
    
    // Remover selected de todos
    elements.actionItems.forEach(item => item.classList.remove('selected'));
    this.classList.add('selected');
    
    // Cambiar placeholder según la acción
    const placeholders = {
        'aprende': 'Pregunta sobre cursos de aprende.org',
        'busqueda': 'Pregunta lo que quieras',
        'tareas': 'Crea o asigna una tarea...',
        'aprende-estudia': 'Pide un resumen o lección...',
        'productividad': 'Organiza tu trabajo...'
    };
    
    elements.userInput.placeholder = placeholders[action] || 'Pregunta lo que quieras';
    appState.currentMode = action;
    
    // Cerrar menú
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
    
    // Cambiar a vista de chat
    showChatView();
    
    // Agregar mensaje del usuario
    addMessage('user', text);
    
    // Mostrar loading
    showLoading();
    
    // Llamar a la API REAL
    callAPI(text)
        .then(response => {
            addMessage('bot', response);
            
            // Procesar si es una tarea
            if (isTaskMessage(response)) {
                processTask(text, response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('bot', '❌ Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta de nuevo.');
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
    
    // Formatear el contenido
    content = formatMessage(content);
    messageDiv.innerHTML = content;
    
    elements.chatHistory.appendChild(messageDiv);
    
    // Auto-scroll al final
    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
    
    // Guardar en historial
    appState.conversationHistory.push({ 
        type, 
        content, 
        timestamp: new Date().toISOString() 
    });
}

// ==================== FUNCIÓN MEJORADA PARA FORMATEAR MENSAJES ====================
function formatMessage(content) {
    // 1. Escapar HTML para prevenir inyección
    content = content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // 2. Convertir markdown básico
    // Negritas: **texto** o __texto__
    content = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    content = content.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Cursivas: *texto* o _texto_
    content = content.replace(/\*(.*?)\*/g, '<em>$1</em>');
    content = content.replace(/_(.*?)_/g, '<em>$1</em>');
    
    // 3. Formatear listas numeradas
    content = content.replace(/(\d+\.\s+[^\n]+)/g, '<br>$1');
    
    // 4. Formatear listas con viñetas
    content = content.replace(/([•\-\*]\s+[^\n]+)/g, '<br>$1');
    
    // 5. Detectar y formatear párrafos (dos saltos de línea)
    content = content.replace(/\n\n/g, '<br><br>');
    
    // 6. Detectar frases que empiezan con mayúscula después de punto
    // Esto ayuda a separar oraciones largas
    content = content.replace(/\.\s+([A-ZÁÉÍÓÚÑ])/g, '.<br><br>$1');
    
    // 7. Saltos de línea simples
    content = content.replace(/\n/g, '<br>');
    
    // 8. Formatear títulos (# Título)
    content = content.replace(/^#\s+(.+)$/gm, '<strong style="font-size: 1.1em;">$1</strong><br>');
    content = content.replace(/^##\s+(.+)$/gm, '<strong>$1</strong><br>');
    
    // 9. Formatear emojis con colores
    content = content.replace(/✅/g, '<span style="color: #28a745;">✅</span>');
    content = content.replace(/📝/g, '<span style="color: #17a2b8;">📝</span>');
    content = content.replace(/📅/g, '<span style="color: #ffc107;">📅</span>');
    content = content.replace(/❌/g, '<span style="color: #dc3545;">❌</span>');
    content = content.replace(/⚠️/g, '<span style="color: #ff9800;">⚠️</span>');
    content = content.replace(/ℹ️/g, '<span style="color: #2196F3;">ℹ️</span>');
    
    // 10. Añadir espaciado después de puntos seguidos
    content = content.replace(/\.\s+/g, '. &nbsp;');
    
    return content;
}

// ==================== TASK MANAGEMENT ====================
function isTaskMessage(message) {
    return message.includes('✅') || 
           message.includes('📝') || 
           message.includes('📅') ||
           message.toLowerCase().includes('recordatorio') ||
           message.toLowerCase().includes('nota') ||
           message.toLowerCase().includes('evento');
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
        completed: false
    };
    
    // Determinar tipo de tarea
    if (botResponse.includes('✅') || userMessage.toLowerCase().includes('recordatorio')) {
        appState.tasks.reminders.push(task);
    } else if (botResponse.includes('📝') || userMessage.toLowerCase().includes('nota')) {
        appState.tasks.notes.push(task);
    } else if (botResponse.includes('📅') || userMessage.toLowerCase().includes('evento')) {
        appState.tasks.calendar.push(task);
    }
    
    updateTasksUI();
    saveToLocalStorage();
}

function updateTasksUI() {
    updateTaskList(elements.remindersList, appState.tasks.reminders, 'reminders', 'No hay recordatorios pendientes');
    updateTaskList(elements.notesList, appState.tasks.notes, 'notes', 'No hay notas');
    updateTaskList(elements.calendarList, appState.tasks.calendar, 'calendar', 'No hay eventos programados');
}

function updateTaskList(container, tasks, taskType, emptyMessage) {
    if (!container) return;
    
    if (tasks.length === 0) {
        container.innerHTML = emptyMessage;
        return;
    }
    
    let html = '';
    tasks.forEach((task, idx) => {
        html += `
            <div class="task-item">
                <div class="task-content">${task.content}</div>
                <div class="task-time">${task.created_at}</div>
                <button class="task-delete" onclick="deleteTask('${taskType}', ${idx})">×</button>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function deleteTask(taskType, index) {
    // Eliminar directamente sin confirmación
    appState.tasks[taskType].splice(index, 1);
    updateTasksUI();
    saveToLocalStorage();
}

// ==================== LIMPIAR TAREAS (SIN ALERT) ====================
function clearAllTasks() {
    // Limpiar directamente sin confirmación
    appState.tasks = { 
        reminders: [], 
        notes: [], 
        calendar: [] 
    };
    updateTasksUI();
    saveToLocalStorage();
}

// Hacer disponibles globalmente
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
            currentMode: appState.currentMode
        };
        localStorage.setItem('claroGenAI_state', JSON.stringify(data));
    } catch (e) {
        console.error('Error guardando en localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        const saved = localStorage.getItem('claroGenAI_state');
        if (saved) {
            const data = JSON.parse(saved);
            appState.conversationHistory = data.conversationHistory || [];
            appState.tasks = data.tasks || { reminders: [], notes: [], calendar: [] };
            appState.currentMode = data.currentMode || 'busqueda';
            
            // Restaurar mensajes del chat si existen
            if (appState.conversationHistory.length > 0) {
                showChatView();
                elements.chatHistory.innerHTML = '';
                appState.conversationHistory.forEach(msg => {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'msg ' + msg.type;
                    messageDiv.innerHTML = formatMessage(msg.content);
                    elements.chatHistory.appendChild(messageDiv);
                });
            }
            
            updateTasksUI();
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
console.log('%cReady to chat!', 'color: #28a745;');



