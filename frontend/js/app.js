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
            
            // Procesar si es una tarea - PASA AMBOS MENSAJES
            if (isTaskMessage(text, response)) {
                processTask(text, response);
            }
        })
        .catch(error => {
            console.error('Error completo:', error);
            
            // Mensaje de error genérico por defecto
            let errorMessage = 'Lo siento, ocurrió un error al procesar tu solicitud. Por favor, intenta nuevamente.';
            
            // Solo mostrar mensaje de tokens si hay evidencia clara
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
    
    // Formatear el contenido
    const formattedContent = formatMessage(content);
    messageDiv.innerHTML = formattedContent;
    
    elements.chatHistory.appendChild(messageDiv);
    
    // Auto-scroll al final
    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
    
    // IMPORTANTE: Guardar el contenido SIN formatear (texto original)
    appState.conversationHistory.push({ 
        type, 
        content: content, // Guardamos el texto original, NO el HTML
        timestamp: new Date().toISOString() 
    });
}

// ==================== FUNCIÓN MEJORADA PARA FORMATEAR MENSAJES CON MARKDOWN ====================
// ==================== FUNCIÓN MEJORADA PARA FORMATEAR MENSAJES CON MARKDOWN INCLUYENDO TABLAS ====================
function formatMessage(content) {
    // PRIMERO: Eliminar comentarios HTML <!-- -->
    content = content.replace(/<!--[\s\S]*?-->/g, '');
    
    // También eliminar etiquetas <! y -> sueltas
    content = content.replace(/<!-+/g, '');
    content = content.replace(/-+>/g, '');
    
    // 1. Escapar HTML básico
    const escapeHtml = (text) => {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
        };
        return text.replace(/[&<>]/g, m => map[m]);
    };
    
    // PROCESAR TABLAS EN MARKDOWN PRIMERO (antes de dividir en líneas)
    content = content.replace(/(?:\|?.+\|.+\n(?:\|?[-:| ]+)+\n(?:\|?.+\|.+\n?)+)/g, (tableMatch) => {
        const rows = tableMatch.trim().split('\n').filter(row => row.trim());
        
        // Verificar si es una tabla válida de markdown
        if (rows.length < 2) return tableMatch;
        
        let tableHtml = '<div class="table-container"><table class="markdown-table">';
        
        rows.forEach((row, rowIndex) => {
            // Limpiar la fila y dividir por pipes
            const cleanRow = row.trim().replace(/^\||\|$/g, '');
            const cells = cleanRow.split('|').map(cell => cell.trim());
            
            if (cells.length === 0) return;
            
            // Determinar si es la fila de encabezado o separador
            const isHeaderRow = rowIndex === 0;
            const isSeparatorRow = rowIndex === 1 && cells.every(cell => cell.replace(/[-:]/g, '').trim() === '');
            
            if (isSeparatorRow) {
                return; // Saltar fila separadora de markdown
            }
            
            tableHtml += '<tr>';
            
            cells.forEach((cell, cellIndex) => {
                let cellContent = escapeHtml(cell);
                
                // Aplicar formato markdown dentro de las celdas
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
    
    // Dividir en líneas después de procesar tablas
    let lines = content.split('\n');
    
    let formatted = lines.map((line) => {
        // Si la línea ya fue procesada como parte de una tabla, saltar
        if (line.includes('</table>') || line.includes('<div class="table-container">')) {
            return line;
        }
        
        // Saltar líneas que son solo separadores ---
        if (line.trim().match(/^-{3,}$/)) {
            return '<hr class="msg-divider" />';
        }
        
        // Líneas vacías
        if (line.trim() === '') {
            return '<div class="msg-spacer"></div>';
        }
        
        // Headers (# Título)
        if (line.startsWith('### ')) {
            return `<h3 class="msg-header">${escapeHtml(line.substring(4))}</h3>`;
        }
        if (line.startsWith('## ')) {
            return `<h2 class="msg-header">${escapeHtml(line.substring(3))}</h2>`;
        }
        if (line.startsWith('# ')) {
            return `<h1 class="msg-header">${escapeHtml(line.substring(2))}</h1>`;
        }
        
        // Blockquotes (> texto) - convertir a texto destacado
        if (line.startsWith('> ')) {
            return `<div class="msg-quote">${escapeHtml(line.substring(2))}</div>`;
        }
        
        // Listas con viñetas (-, *, •)
        if (line.match(/^[\s]*[-\*•]\s+/)) {
            const listContent = line.replace(/^[\s]*[-\*•]\s+/, '');
            return `<li class="msg-list-item">${escapeHtml(listContent)}</li>`;
        }
        
        // Listas numeradas (1., 2., etc.)
        if (line.match(/^[\s]*\d+\.\s+/)) {
            const listContent = line.replace(/^[\s]*\d+\.\s+/, '');
            return `<li class="msg-list-item numbered">${escapeHtml(listContent)}</li>`;
        }
        
        // Texto normal
        return `<p class="msg-paragraph">${escapeHtml(line)}</p>`;
    });
    
    // Unir todo
    let html = formatted.join('');
    
    // APLICAR FORMATOS INLINE EN ORDEN ESPECÍFICO (solo a texto que no sea tabla)
    
    // 1. Primero procesar negritas: **texto** (solo fuera de tablas)
    html = html.replace(/(?![^<]*<\/table>)\*\*([^\*]+)\*\*/g, '<strong>$1</strong>');
    
    // 2. Luego cursivas: *texto* (pero no si ya es parte de **)
    html = html.replace(/(?![^<]*<\/table>)(?<!\*)\*([^\*]+)\*(?!\*)/g, '<em>$1</em>');
    
    // 3. Código inline: `código`
    html = html.replace(/(?![^<]*<\/table>)`([^`]+)`/g, '<code class="msg-code">$1</code>');
    
    // 4. Links markdown: [texto](url) - PRIMERO
    html = html.replace(/(?![^<]*<\/table>)\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" class="msg-link">$1</a>');
    
    // 5. URLs simples - pero NO si ya están dentro de <a> o tienen comillas de atributos cerca
    html = html.replace(/(?![^<]*<\/table>)(?<!href="|">)(https?:\/\/[^\s<>"]+)(?![^<]*<\/a>)/g, function(match) {
        return `<a href="${match}" target="_blank" rel="noopener" class="msg-link">${match}</a>`;
    });
    
    // 6. Emojis con colores
    html = html.replace(/✅/g, '<span style="color: #28a745;">✅</span>');
    html = html.replace(/📝/g, '<span style="color: #17a2b8;">📝</span>');
    html = html.replace(/📅/g, '<span style="color: #ffc107;">📅</span>');
    html = html.replace(/❌/g, '<span style="color: #dc3545;">❌</span>');
    html = html.replace(/⚠️/g, '<span style="color: #ff9800;">⚠️</span>');
    html = html.replace(/😊/g, '<span style="font-size: 1.2em;">😊</span>');
    
    return html;
}







//MEJORA+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++











// ==================== TASK MANAGEMENT ====================
function isTaskMessage(userMsg, botMsg) {
    const lowerUserMsg = userMsg.toLowerCase();
    const lowerBotMsg = botMsg.toLowerCase();
    
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
    
    // DETECCIÓN CON PRIORIDAD CORREGIDA
    let taskType = null;
    
    const lowerUserMsg = userMessage.toLowerCase();
    const lowerBotMsg = botResponse.toLowerCase();
    
    console.log('🔍 Detectando tipo de tarea...');
    console.log('Usuario:', userMessage);
    console.log('Bot:', botResponse);
    
    // PRIORIDAD 1: RECORDATORIOS (verificar PRIMERO)
    // Si dice "recordar", "recuérdame", "avísame" ES un recordatorio
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
    // PRIORIDAD 2: AGENDA/CALENDARIO
    // Solo si dice explícitamente "agendar", "agenda", "programar"
    else if (lowerUserMsg.includes('agendar') || 
             lowerUserMsg.includes('agenda ') || // espacio después para evitar "agendame"
             lowerUserMsg.includes('programar') ||
             lowerUserMsg.includes('agendar') ||
             (lowerUserMsg.includes('cita') && !lowerUserMsg.includes('recordar')) ||
             botResponse.includes('📅') ||
             lowerBotMsg.includes('agendado') ||
             lowerBotMsg.includes('he agendado')) {
        taskType = 'calendar';
    } 
    // PRIORIDAD 3: NOTAS
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
    
    // Si no se detectó nada específico, usar reminders por defecto
    if (!taskType) {
        taskType = 'reminders';
    }
    
    console.log('✅ Tipo detectado:', taskType);
    
    // Agregar a la lista correspondiente
    if (!appState.tasks[taskType]) {
        appState.tasks[taskType] = [];
    }
    
    appState.tasks[taskType].push(task);
    
    // ACTUALIZAR UI
    updateTasksUI();
    
    // Asegurar que el tasks container esté visible
    if (elements.tasksContainer) {
        elements.tasksContainer.classList.add('active');
    }
    
    // Expandir automáticamente la sección correspondiente
    expandTaskSection(taskType);
    
    saveToLocalStorage();
    
    console.log('💾 Tarea guardada en:', taskType);
    console.log('📊 Estado actual:', appState.tasks);
}

// Nueva función para expandir automáticamente la sección de tareas
function expandTaskSection(taskType) {
    // Cerrar todas las secciones primero
    document.querySelectorAll('.task-body').forEach(body => body.classList.remove('open'));
    document.querySelectorAll('.task-header').forEach(header => header.classList.remove('collapsed'));
    
    // Abrir la sección correspondiente
    const targetHeader = document.querySelector(`.task-header[data-task-type="${taskType}"]`);
    if (targetHeader) {
        const targetBody = targetHeader.nextElementSibling;
        targetBody.classList.add('open');
        targetHeader.classList.add('collapsed');
    }
}

function updateTasksUI() {
    console.log('🔄 Actualizando UI de tareas:', appState.tasks);
    
    updateTaskList(elements.remindersList, appState.tasks.reminders, 'reminders', 'No hay recordatorios pendientes');
    updateTaskList(elements.notesList, appState.tasks.notes, 'notes', 'No hay notas');
    updateTaskList(elements.calendarList, appState.tasks.calendar, 'calendar', 'No hay eventos programados');
    
    // Actualizar badges - CON VALIDACIÓN
    updateTaskBadges();
}

// Nueva función para mostrar badges/contadores en el sidebar - CON VALIDACIÓN
function updateTaskBadges() {
    const totalTasks = (appState.tasks.reminders?.length || 0) + 
                      (appState.tasks.notes?.length || 0) + 
                      (appState.tasks.calendar?.length || 0);
    
    // Actualizar el texto del botón de Gestión de tareas - CON VALIDACIÓN
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
    if (!container) {
        console.error('❌ Contenedor no encontrado para:', taskType);
        return;
    }
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `<div class="empty-task-message">${emptyMessage}</div>`;
        return;
    }
    
    console.log(`📝 Renderizando ${tasks.length} tareas de tipo:`, taskType);
    
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



// Función helper para escapar HTML (seguridad)
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}





//MEJORA++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++













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
            currentMode: appState.currentMode,
            sessionId: sessionStorage.getItem('claroAssistant_sessionId')
        };
        localStorage.setItem('claroAssistant_state', JSON.stringify(data));
    } catch (e) {
        console.error('Error guardando en localStorage:', e);
    }
}












//mejora++++++++++++++++++++++++++++++++++++++++++++++++++


function loadFromLocalStorage() {
    try {
        // Generar o recuperar ID de sesión única
        let currentSessionId = sessionStorage.getItem('claroAssistant_sessionId');
        
        if (!currentSessionId) {
            // Nueva sesión: generar ID único
            currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('claroAssistant_sessionId', currentSessionId);
            
            // Limpiar conversación anterior al iniciar nueva sesión
            localStorage.removeItem('claroAssistant_state');
            console.log('Nueva sesion iniciada');
            return;
        }
        
        // Sesión existente: cargar datos
        const saved = localStorage.getItem('claroAssistant_state');
        if (saved) {
            const data = JSON.parse(saved);
            
            // Verificar que sea la misma sesión
            if (data.sessionId === currentSessionId) {
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
                    console.log('Conversacion restaurada');
                }
                
                // ACTUALIZAR UI DE TAREAS AL CARGAR - ESTA ES LA LÍNEA CLAVE
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






//mejora++++++++++++++++++++++++++++++++++++++++++++++++++










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
