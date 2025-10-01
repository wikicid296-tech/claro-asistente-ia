// Estado de la aplicación
class AppState {
    constructor() {
        this.messages = [];
        this.tasks = {
            reminders: [],
            notes: [],
            calendar: []
        };
        this.showMenu = false;
        this.selectedAction = null;
        this.apiBaseUrl = window.location.origin;
    }
}

const appState = new AppState();

// Elementos DOM
const elements = {
    chatMessages: document.getElementById('chat-messages'),
    messageInput: document.getElementById('message-input'),
    sendButton: document.getElementById('send-button'),
    menuToggle: document.getElementById('menu-toggle'),
    quickMenu: document.getElementById('quick-menu'),
    activeMode: document.getElementById('active-mode'),
    modeIcon: document.getElementById('mode-icon'),
    modeText: document.getElementById('mode-text'),
    closeMode: document.getElementById('close-mode'),
    loading: document.getElementById('loading'),
    clearTasks: document.getElementById('clear-tasks'),
    clearChat: document.getElementById('clear-chat'),
    remindersList: document.getElementById('reminders-list'),
    notesList: document.getElementById('notes-list'),
    calendarList: document.getElementById('calendar-list')
};

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadFromLocalStorage();
    updateTasksUI();
});

function initializeEventListeners() {
    // Envío de mensajes
    elements.sendButton.addEventListener('click', sendMessage);
    elements.messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Menú rápido
    elements.menuToggle.addEventListener('click', toggleQuickMenu);
    elements.closeMode.addEventListener('click', closeActiveMode);

    // Opciones del menú
    document.querySelectorAll('.menu-option').forEach(option => {
        option.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            setActiveMode(action);
        });
    });

    // Botones de limpieza
    elements.clearTasks.addEventListener('click', clearAllTasks);
    elements.clearChat.addEventListener('click', clearChat);

    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', function(e) {
        if (appState.showMenu && 
            !elements.quickMenu.contains(e.target) && 
            !elements.menuToggle.contains(e.target)) {
            toggleQuickMenu();
        }
    });
}

// Funciones del chat
async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message) return;

    // Agregar mensaje del usuario
    addMessage('user', message);
    elements.messageInput.value = '';

    // Mostrar loading
    showLoading();

    try {
        const response = await fetch(`${appState.apiBaseUrl}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                action: appState.selectedAction
            })
        });

        const data = await response.json();

        if (data.success) {
            addMessage('assistant', data.response);
            
            // Verificar si es una tarea y procesarla
            if (data.response.includes('✅') || data.response.includes('📝') || data.response.includes('📅')) {
                processTaskFromResponse(message, data.response);
            }
        } else {
            addMessage('assistant', '❌ Error: ' + (data.error || 'No se pudo procesar tu mensaje'));
        }

        // Limpiar modo activo después de enviar
        if (appState.selectedAction) {
            closeActiveMode();
        }

    } catch (error) {
        console.error('Error:', error);
        addMessage('assistant', '❌ Error de conexión. Por favor, intenta de nuevo.');
    } finally {
        hideLoading();
        saveToLocalStorage();
    }
}

function addMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${role}`;
    
    const timestamp = new Date().toLocaleTimeString('es-ES', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });

    messageDiv.innerHTML = `
        <div class="message-content">${formatMessage(content)}</div>
        <div class="message-time">${timestamp}</div>
    `;

    elements.chatMessages.appendChild(messageDiv);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    
    // Agregar al estado
    appState.messages.push({ role, content });
}

function formatMessage(content) {
    // Convertir saltos de línea a <br>
    content = content.replace(/\n/g, '<br>');
    
    // Formatear listas y mejorar emojis
    content = content.replace(/\•/g, '<br>•');
    content = content.replace(/\✅/g, '<span style="color: #28a745;">✅</span>');
    content = content.replace(/\📝/g, '<span style="color: #17a2b8;">📝</span>');
    content = content.replace(/\📅/g, '<span style="color: #ffc107;">📅</span>');
    content = content.replace(/\❌/g, '<span style="color: #dc3545;">❌</span>');
    
    return content;
}

// Funciones del menú rápido
function toggleQuickMenu() {
    appState.showMenu = !appState.showMenu;
    if (appState.showMenu) {
        elements.quickMenu.classList.remove('hidden');
        elements.menuToggle.innerHTML = '<i class="fas fa-times"></i>';
    } else {
        elements.quickMenu.classList.add('hidden');
        elements.menuToggle.innerHTML = '<i class="fas fa-plus"></i>';
    }
}

function setActiveMode(action) {
    const modeConfig = {
        smart_search: { icon: '💡', text: 'Búsqueda Inteligente' },
        task: { icon: '📋', text: 'Modo Tareas' },
        learn: { icon: '📚', text: 'Modo Aprendizaje' },
        health: { icon: '🏥', text: 'Modo Salud' }
    };

    if (modeConfig[action]) {
        appState.selectedAction = action;
        elements.modeIcon.textContent = modeConfig[action].icon;
        elements.modeText.textContent = modeConfig[action].text;
        elements.activeMode.classList.remove('hidden');
        
        // Actualizar placeholder
        const placeholders = {
            smart_search: '💡 ¿Qué quieres buscar?',
            task: '📋 Describe la tarea...',
            learn: '📚 ¿Qué quieres aprender?',
            health: '🏥 Consulta sobre salud...'
        };
        elements.messageInput.placeholder = placeholders[action] || '¿En qué puedo ayudarte?';
        
        toggleQuickMenu();
    }
}

function closeActiveMode() {
    appState.selectedAction = null;
    elements.activeMode.classList.add('hidden');
    elements.messageInput.placeholder = '¿En qué puedo ayudarte hoy?';
}

// Gestión de tareas
function processTaskFromResponse(message, response) {
    const timestamp = new Date().toLocaleString('es-ES');
    
    if (response.includes('✅')) {
        appState.tasks.reminders.push({
            content: message,
            created_at: timestamp,
            completed: false
        });
    } else if (response.includes('📝')) {
        appState.tasks.notes.push({
            content: message,
            created_at: timestamp,
            completed: false
        });
    } else if (response.includes('📅')) {
        appState.tasks.calendar.push({
            content: message,
            created_at: timestamp,
            completed: false
        });
    }
    
    updateTasksUI();
    saveToLocalStorage();
}

function updateTasksUI() {
    updateTaskList('reminders', elements.remindersList);
    updateTaskList('notes', elements.notesList);
    updateTaskList('calendar', elements.calendarList);
}

function updateTaskList(taskType, listElement) {
    const tasks = appState.tasks[taskType];
    
    if (tasks.length === 0) {
        listElement.innerHTML = '<div class="no-tasks">No hay ' + getTaskLabel(taskType) + '</div>';
        return;
    }
    
    let html = '';
    tasks.forEach((task, index) => {
        html += `
            <div class="task-item">
                <div class="task-content">${task.content}</div>
                <div class="task-time">📅 ${task.created_at}</div>
                <button class="task-delete" onclick="deleteTask('${taskType}', ${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    });
    
    listElement.innerHTML = html;
}

function getTaskLabel(taskType) {
    const labels = {
        reminders: 'recordatorios',
        notes: 'notas', 
        calendar: 'eventos'
    };
    return labels[taskType] || 'tareas';
}

function deleteTask(taskType, index) {
    if (confirm('¿Estás seguro de que quieres eliminar esta tarea?')) {
        appState.tasks[taskType].splice(index, 1);
        updateTasksUI();
        saveToLocalStorage();
    }
}

function clearAllTasks() {
    if (confirm('¿Estás seguro de que quieres eliminar todas las tareas?')) {
        appState.tasks = { reminders: [], notes: [], calendar: [] };
        updateTasksUI();
        saveToLocalStorage();
        showNotification('Todas las tareas han sido eliminadas', 'success');
    }
}

function clearChat() {
    if (confirm('¿Estás seguro de que quieres limpiar el chat?')) {
        appState.messages = [];
        elements.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="message-bubble assistant">
                    <div class="message-content">
                        <strong>👋 ¡Chat limpiado!</strong>
                        <p>¿En qué puedo ayudarte ahora?</p>
                    </div>
                    <div class="message-time">Ahora</div>
                </div>
            </div>
        `;
        saveToLocalStorage();
        showNotification('Chat limpiado correctamente', 'success');
    }
}

// Notificaciones
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">×</button>
    `;
    
    // Estilos para la notificación
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : '#17a2b8'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        display: flex;
        align-items: center;
        gap: 10px;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remover después de 3 segundos
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 3000);
}

// Loading
function showLoading() {
    elements.loading.classList.remove('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

// Local Storage
function saveToLocalStorage() {
    try {
        localStorage.setItem('telecomCopilot_messages', JSON.stringify(appState.messages));
        localStorage.setItem('telecomCopilot_tasks', JSON.stringify(appState.tasks));
    } catch (e) {
        console.error('Error guardando en localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        const savedMessages = localStorage.getItem('telecomCopilot_messages');
        const savedTasks = localStorage.getItem('telecomCopilot_tasks');
        
        if (savedMessages) {
            const messages = JSON.parse(savedMessages);
            // Solo cargar los últimos 20 mensajes para no saturar
            appState.messages = messages.slice(-20);
            
            // Re-renderizar mensajes
            elements.chatMessages.innerHTML = '';
            appState.messages.forEach(msg => {
                addMessage(msg.role, msg.content);
            });
        }
        
        if (savedTasks) {
            appState.tasks = JSON.parse(savedTasks);
        }
    } catch (e) {
        console.error('Error cargando desde localStorage:', e);
    }
}

// Estilos CSS adicionales para las notificaciones
const notificationStyles = `
@keyframes slideInRight {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.notification button {
    background: none;
    border: none;
    color: white;
    font-size: 18px;
    cursor: pointer;
    padding: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.task-item {
    position: relative;
    background: white;
    border-left: 3px solid #e53935;
    padding: 8px;
    margin: 5px 0;
    border-radius: 4px;
    font-size: 0.8rem;
}

.task-content {
    margin-bottom: 2px;
}

.task-time {
    font-size: 0.7rem;
    color: #666;
}

.task-delete {
    position: absolute;
    top: 5px;
    right: 5px;
    background: none;
    border: none;
    color: #dc3545;
    cursor: pointer;
    font-size: 0.7rem;
    padding: 2px;
    border-radius: 3px;
}

.task-delete:hover {
    background: #dc3545;
    color: white;
}
`;

// Agregar estilos al documento
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);