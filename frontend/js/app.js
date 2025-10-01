/// ==================== CONFIGURACIÓN Y VARIABLES GLOBALES ====================
// URL CORREGIDA para producción - ESTA ES LA CLAVE
const API_URL = 'https://claro-asistente-ia.onrender.com';

// Estado global de la aplicación
const appState = {
    currentMode: null,
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
    
    // Main content
    welcomePage: document.getElementById('welcomePage'),
    chatPage: document.getElementById('chatPage'),
    chatHistory: document.getElementById('chatHistory'),
    
    // Input
    userInput: document.getElementById('userInput'),
    addBtn: document.getElementById('addBtn'),
    actionMenu: document.getElementById('actionMenu'),
    actionItems: document.querySelectorAll('.action-item'),
    
    // Suggestions
    suggestionCards: document.querySelectorAll('.suggestion-card'),
    
    // Loading
    loadingOverlay: document.getElementById('loadingOverlay')
};

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Iniciando aplicación en:', API_URL);
    initializeEventListeners();
    loadFromLocalStorage();
    
    // Mostrar URL actual para debug
    showDebugInfo();
});

function showDebugInfo() {
    console.log('🔗 URL de API:', API_URL);
    console.log('📱 Navegador:', navigator.userAgent);
    
    // Crear mensaje de debug en la interfaz (oculto)
    const debugDiv = document.createElement('div');
    debugDiv.style.cssText = 'position:fixed; top:10px; right:10px; background:#ff9800; color:white; padding:5px; border-radius:5px; font-size:10px; z-index:9999;';
    debugDiv.innerHTML = `API: ${API_URL}`;
    debugDiv.id = 'debug-info';
    document.body.appendChild(debugDiv);
}

function initializeEventListeners() {
    // Toggle sidebar (móvil)
    elements.menuToggle.addEventListener('click', toggleSidebar);
    elements.overlay.addEventListener('click', closeSidebar);
    
    // Navegación sidebar
    elements.navItems.forEach(item => {
        item.addEventListener('click', handleNavigation);
    });
    
    // Task headers (expandir/contraer)
    elements.taskHeaders.forEach(header => {
        header.addEventListener('click', toggleTaskCard);
    });
    
    // Botón + (mostrar menú de acciones)
    elements.addBtn.addEventListener('click', toggleActionMenu);
    
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

// ==================== CHAT FUNCTIONS ====================
function sendMessage(text) {
    if (!text || !text.trim()) return;
    
    // Cambiar a vista de chat
    showChatView();
    
    // Agregar mensaje del usuario
    addMessage('user', text);
    
    // Mostrar loading
    showLoading();
    
    // Llamar a la API con mejor manejo de errores
    callAPI(text)
        .then(response => {
            addMessage('bot', response);
            
            // Procesar si es una tarea
            if (isTaskMessage(response)) {
                processTask(text, response);
            }
        })
        .catch(error => {
            console.error('Error en sendMessage:', error);
            let errorMessage = '❌ Lo siento, hubo un error al procesar tu mensaje. ';
            
            if (error.message.includes('Failed to fetch') || error.message.includes('Network')) {
                errorMessage += 'Problema de conexión. Verifica tu internet.';
            } else if (error.message.includes('Timeout')) {
                errorMessage += 'El servidor tardó demasiado. Intenta nuevamente.';
            } else {
                errorMessage += 'Por favor, intenta de nuevo.';
            }
            
            addMessage('bot', errorMessage);
        })
        .finally(() => {
            hideLoading();
            saveToLocalStorage();
        });
    
    // Limpiar input
    elements.userInput.value = '';
}

function showChatView() {
    elements.welcomePage.style.display = 'none';
    elements.chatPage.style.display = 'flex';
}

function addMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'msg ' + type;
    messageDiv.textContent = content;
    
    elements.chatHistory.appendChild(messageDiv);
    
    // Auto-scroll al final
    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
    
    // Guardar en historial
    appState.conversationHistory.push({ type, content, timestamp: new Date().toISOString() });
}

// ==================== API CALLS ====================
async function callAPI(message) {
    console.log('📡 Enviando mensaje a:', `${API_URL}/chat`);
    
    try {
        // Configuración mejorada para móviles
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 segundos timeout
        
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                action: appState.currentMode
            }),
            signal: controller.signal,
            mode: 'cors',
            credentials: 'omit'
        });
        
        clearTimeout(timeoutId);
        
        console.log('📡 Status de respuesta:', response.status);
        
        if (!response.ok) {
            let errorText = 'Error del servidor';
            try {
                errorText = await response.text();
            } catch (e) {
                // No se pudo leer el cuerpo de la respuesta
            }
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('✅ Respuesta recibida:', data);
        
        if (data.success) {
            return data.response;
        } else {
            throw new Error(data.error || 'Error desconocido del servidor');
        }
        
    } catch (error) {
        console.error('❌ Error en callAPI:', error);
        
        if (error.name === 'AbortError') {
            throw new Error('Timeout: La petición tardó demasiado. Intenta nuevamente.');
        } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            throw new Error('Error de conexión. No se pudo conectar al servidor.');
        } else {
            throw error;
        }
    }
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
    const timestamp = new Date().toLocaleString('es-ES');
    
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
    // Actualizar cada sección de tareas
    updateTaskSection('reminders', 'Recordatorios');
    updateTaskSection('notes', 'Notas');
    updateTaskSection('calendar', 'Agenda');
}

function updateTaskSection(taskType, label) {
    const tasks = appState.tasks[taskType];
    const containers = document.querySelectorAll('.task-body');
    const index = taskType === 'reminders' ? 0 : taskType === 'calendar' ? 1 : 2;
    const container = containers[index];
    
    if (!container) return;
    
    if (tasks.length === 0) {
        container.innerHTML = `No hay ${label.toLowerCase()}`;
        return;
    }
    
    let html = '<div style="max-height: 200px; overflow-y: auto;">';
    tasks.forEach((task, idx) => {
        html += `
            <div class="task-item" style="background: white; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #00BCD4; position: relative;">
                <div style="font-size: 13px; color: #333; padding-right: 20px;">${task.content}</div>
                <div style="font-size: 11px; color: #999; margin-top: 4px;">${task.created_at}</div>
                <button onclick="deleteTask('${taskType}', ${idx})" style="position: absolute; top: 5px; right: 5px; background: none; border: none; color: #dc3545; cursor: pointer; font-size: 16px;">×</button>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

function deleteTask(taskType, index) {
    if (confirm('¿Eliminar esta tarea?')) {
        appState.tasks[taskType].splice(index, 1);
        updateTasksUI();
        saveToLocalStorage();
    }
}

// Hacer disponible globalmente para onclick
window.deleteTask = deleteTask;

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
        localStorage.setItem('claroGenAI_state', JSON.stringify({
            conversationHistory: appState.conversationHistory.slice(-50), // Solo últimas 50
            tasks: appState.tasks
        }));
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
            
            // Restaurar mensajes del chat si existen
            if (appState.conversationHistory.length > 0) {
                showChatView();
                appState.conversationHistory.forEach(msg => {
                    addMessage(msg.type, msg.content);
                });
            }
            
            updateTasksUI();
        }
    } catch (e) {
        console.error('Error cargando desde localStorage:', e);
    }
}

// ==================== UTILITY FUNCTIONS ====================
function clearChat() {
    if (confirm('¿Estás seguro de que quieres limpiar el chat?')) {
        appState.conversationHistory = [];
        elements.chatHistory.innerHTML = '';
        elements.welcomePage.style.display = 'flex';
        elements.chatPage.style.display = 'none';
        saveToLocalStorage();
    }
}

function clearAllTasks() {
    if (confirm('¿Estás seguro de que quieres eliminar todas las tareas?')) {
        appState.tasks = { reminders: [], notes: [], calendar: [] };
        updateTasksUI();
        saveToLocalStorage();
    }
}

// Hacer disponibles globalmente si se necesitan
window.clearChat = clearChat;
window.clearAllTasks = clearAllTasks;

// ==================== RESPONSIVE HANDLERS ====================
window.addEventListener('resize', function() {
    if (window.innerWidth >= 900) {
        // En desktop, asegurar que el sidebar esté visible
        elements.sidebar.style.left = '0';
        elements.overlay.classList.remove('active');
    } else {
        // En móvil, resetear
        if (!elements.sidebar.classList.contains('active')) {
            elements.sidebar.style.left = '-280px';
        }
    }
});

// ==================== DIAGNÓSTICO AUTOMÁTICO ====================
// Probar conexión automáticamente al cargar
window.addEventListener('load', function() {
    setTimeout(() => {
        fetch(`${API_URL}/health`)
            .then(response => response.json())
            .then(data => {
                console.log('🏥 Health check exitoso:', data);
                document.getElementById('debug-info').innerHTML += ' | ✅ Conectado';
            })
            .catch(error => {
                console.error('🏥 Health check falló:', error);
                document.getElementById('debug-info').innerHTML += ' | ❌ Sin conexión';
            });
    }, 1000);
});

// ==================== CONSOLE INFO ====================
console.log('%c🚀 Telecom Copilot Initialized', 'color: #DA291C; font-size: 16px; font-weight: bold;');
console.log('%cAPI URL:', 'color: #00BCD4; font-weight: bold;', API_URL);
console.log('%cPara probar conexión ejecuta: testConnection()', 'color: #ff9800;');


