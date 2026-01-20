// ==================== CONFIGURACIÓN Y VARIABLES GLOBALES ====================
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'  // Desarrollo local
    : 'https://claro-asistente-ia.onrender.com';  // Producción


// ==================== CONFIGURACIÓN DE LÍMITE DE MENSAJES ====================
const MESSAGE_LIMIT = {
    FREE: 5,  // Límite de mensajes gratis (solo cuenta mensajes del usuario)
    PRO: Infinity
};

// Estado del usuario
const userState = {
    isPro: false,
    messageCount: 0
};

// Configuración de tokens
const TOKEN_CONFIG = {
    MAX_TOKENS: 1000,
    CHARS_PER_TOKEN: 3.5 // Promedio fijo entre 3 y 4
};

// Estado global de la aplicación
const appState = {
    currentMode: 'descubre', // Cambiado de 'busqueda' a 'descubre' para consistencia
    conversationHistory: [],
    tasks: {
        reminders: [],
        notes: [],
        calendar: []
    },
    mediaViewer: {
        isActive: false,
        currentMedia: null,
        mediaType: null
    },
    lastAprendeResource: null,
    // 🆕 AGREGAR ESTA LÍNEA
    modeActivatedManually: false,  // Flag para saber si el modo fue activado manualmente
    isLoadedFromHistory: false  // Flag para saber si la conversación actual fue cargada desde el historial
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
    tasksSection: document.getElementById('tasksSection'),
    taskCategoryHeaders: document.querySelectorAll('.task-category-header'),
    tasksNavBtn: document.getElementById('tasksNavBtn'),
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
    calendarList: document.getElementById('calendar-list'),

    // Mode Chip - NUEVO
    modeChipContainer: document.getElementById('modeChipContainer'),
    modeChipText: document.getElementById('modeChipText'),
    modeChipClose: document.getElementById('modeChipClose')
};

// 🆕 ELEMENTOS DE CONSUMO
elements.usageMeter = document.getElementById('usageMeter');
elements.usageFill = document.getElementById('usageFill');
elements.usageText = document.getElementById('usageText');

// 🆕 ESTADO DE CONSUMO
const usageState = {
    consumed: 0,
    limit: 10,
    percentage: 0,
    blocked: false,
    warning: false
};

// ==================== MODE CONTROLLER ====================
function setMode(mode, { source = 'manual' } = {}) {
    const placeholders = {
        descubre: 'Pregunta lo que quieras',
        aprende: 'Pregunta sobre cursos de aprende.org',
        busqueda_web: 'Busca cualquier información en la web...'
    };

    const modeNames = {
        descubre: 'Descubre',
        aprende: 'Aprende.org',
        busqueda_web: 'Búsqueda web'
    };

    // 1️⃣ Estado
    appState.currentMode = mode;
    appState.modeActivatedManually = source === 'manual';

    // 2️⃣ Placeholder
    if (elements.userInput) {
        elements.userInput.placeholder = placeholders[mode] || placeholders.descubre;
    }

    // 3️⃣ Chip
    if (mode === 'descubre') {
        hideModeChip();
    } else {
        showModeChip(modeNames[mode], mode);
    }

    // 4️⃣ Sidebar
    elements.navItems.forEach(item => {
        item.classList.toggle(
            'active',
            item.getAttribute('data-section') === mode
        );
    });

    // 5️⃣ Action menu
    elements.actionItems.forEach(item => {
        item.classList.toggle(
            'selected',
            item.getAttribute('data-action') === mode
        );
    });

    console.log(`🔄 Modo activo: ${mode} (source: ${source})`);
}

// ==================== FUNCIONES DE CONSUMO ====================
/**
 * Consulta el endpoint /usage y actualiza el estado
 */
async function fetchUsageStatus() {
    try {
        const response = await fetch(`${API_URL}/usage`);
        
        if (!response.ok) {
            console.error('Error consultando /usage:', response.status);
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            usageState.consumed = data.consumed;
            usageState.limit = data.limit;
            usageState.percentage = data.percentage;
            usageState.blocked = data.blocked;
            usageState.warning = data.warning;
            
            updateUsageMeter();
            
            // Si está bloqueado, deshabilitar input
            if (usageState.blocked) {
                blockInputDueToUsage();
            }
        }
    } catch (error) {
        console.error('Error fetching usage:', error);
    }
}

/**
 * Actualiza la barra visual de consumo
 */
function updateUsageMeter() {
    if (!elements.usageMeter || !elements.usageFill || !elements.usageText) return;
    
    // Mostrar el medidor
    elements.usageMeter.style.display = 'flex';
    
    // Actualizar ancho de la barra
    elements.usageFill.style.width = `${usageState.percentage}%`;
    
    // Actualizar texto
    elements.usageText.textContent = `$${usageState.consumed}/$${usageState.limit}`;
    
    // Cambiar color según porcentaje
    elements.usageFill.classList.remove('warning', 'danger');
    
    if (usageState.percentage >= 100) {
        elements.usageFill.classList.add('danger');
    } else if (usageState.percentage >= 90) {
        elements.usageFill.classList.add('warning');
    }
    
    console.log(`💰 Consumo: $${usageState.consumed}/$${usageState.limit} (${usageState.percentage}%)`);
}

/**
 * Bloquea el input cuando se alcanza el límite
 */
function blockInputDueToUsage() {
    elements.userInput.value = '';
    elements.userInput.placeholder = '🚫 Límite mensual alcanzado ($10 USD)';
    elements.userInput.disabled = true;
    elements.userInput.style.cursor = 'not-allowed';
    elements.userInput.style.color = '#dc3545';
    elements.sendBtn.disabled = true;
    elements.sendBtn.style.opacity = '0.5';
    elements.sendBtn.style.cursor = 'not-allowed';
    
    console.warn('🚫 Input bloqueado: Límite de $10 alcanzado');
}

/**
 * Muestra advertencia cuando está cerca del límite
 */
function showUsageWarning() {
    if (usageState.warning && !usageState.blocked) {
        // Mostrar notificación temporal
        const warningMsg = document.createElement('div');
        warningMsg.className = 'usage-warning-toast';
        warningMsg.innerHTML = `
            <span style="font-size: 20px;">⚠️</span>
            <div>
                <strong>Casi alcanzas el límite</strong>
                <br>
                <small>Quedan $${(usageState.limit - usageState.consumed).toFixed(2)} de tu límite mensual</small>
            </div>
        `;
        
        document.body.appendChild(warningMsg);
        
        setTimeout(() => {
            warningMsg.style.opacity = '0';
            setTimeout(() => warningMsg.remove(), 300);
        }, 5000);
    }
}

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


// ==================== DETECCIÓN AUTOMÁTICA DE MODO ====================
/**
 * Detecta palabras clave en el texto y activa el modo correspondiente automáticamente
 */
function detectModeFromText(text) {
    const lowerText = text ? text.toLowerCase().trim() : '';
    
    // Palabras clave para cada modo
    const modeKeywords = {
        'aprende': ['aprende', 'aprende.org', 'aprender', 'curso', 'cursos', 'estudio'],
        'busqueda_web': ['google', 'buscar', 'internet', 'web', 'información', 'investigar', 'investigación']
    };
    
    // Helper: detecta si una palabra clave aparece como token completo
    function matchesKeywordStrict(haystack, keyword) {
        if (!haystack || !keyword) return false;
        // Escape regex special chars
        const esc = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        // Match cuando aparece como token separado
        const pattern = '(^|\\W)' + esc + '(\\W|$)';
        return new RegExp(pattern, 'i').test(haystack);
    }
    
    // Si está en modo manual, no cambiar automáticamente
    if (appState.modeActivatedManually) {
        return;
    }
    
    // No detectar si el texto es muy corto o está vacío
    if (!text || text.length < 3) {
        return;
    }
    
    // Buscar coincidencias en cada modo
    for (const [mode, keywords] of Object.entries(modeKeywords)) {
        for (const keyword of keywords) {
            if (matchesKeywordStrict(lowerText, keyword)) {
                // Si detectamos la palabra clave y no estamos ya en ese modo, cambiar
                if (appState.currentMode !== mode) {
                    activateModeAutomatically(mode);
                }
                return;
            }
        }
    }
    
    // Si no detecta ninguna palabra clave y no está en "descubre", volver a descubre
    if (appState.currentMode !== 'descubre' && !appState.modeActivatedManually) {
        deactivateAutoMode();
    }
}

/**
 * Activa un modo automáticamente y actualiza la UI
 */
function activateModeAutomatically(mode) {
    setMode(mode, { source: 'auto' });
}


/**
 * Desactiva el modo automático y vuelve a "descubre"
 */
function deactivateAutoMode() {
    setMode('descubre', { source: 'auto' });
}


// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', async function() {
    initializeEventListeners();
    loadFromLocalStorage();
    
    // Actualizar UI de tareas al cargar
    updateTasksUI();
    
    // Inicializar módulo de conversaciones (esperar a que cargue)
    await initConversationStorage();
    
    // Inicializar contador de tokens
    if (elements.maxTokens) {
        elements.maxTokens.textContent = TOKEN_CONFIG.MAX_TOKENS;
    }
    updateTokenCounter(0);
    
    // 🆕 CARGAR HISTORIAL DE CONVERSACIONES (ahora que están cargadas las funciones)
    setTimeout(() => {
        updateConversationHistoryUI();
    }, 500);
    
    // 🆕 CONSULTAR CONSUMO AL CARGAR
    fetchUsageStatus();
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

    // Task category headers (NEW STYLE)
    elements.taskCategoryHeaders.forEach(header => {
        header.addEventListener('click', toggleTaskCategory);
    });

    // Task headers (old style) - ESTILO ORIGINAL QUE QUEREMOS RECUPERAR
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

    // Mode Chip Close Button - NUEVO
    if (elements.modeChipClose) {
    elements.modeChipClose.addEventListener('click', hideModeChip);
    }
    
    // Input de usuario - actualizar tokens Y detectar modo
elements.userInput.addEventListener('input', function() {
    const tokens = estimateTokens(this.value);
    updateTokenCounter(tokens);
    
    // 🆕 DETECTAR MODO AUTOMÁTICAMENTE
    detectModeFromText(this.value);
});

    // ===== NUEVO: Detectar clic en input cuando está en límite =====
elements.userInput.addEventListener('click', function() {
    if (this.classList.contains('limit-reached')) {
        showPremiumModal();
    }
});


// ===== NUEVO: Detectar focus en input cuando está en límite =====
elements.userInput.addEventListener('focus', function() {
    if (this.classList.contains('limit-reached')) {
        this.blur(); // Quitar el focus
        showPremiumModal();
    }
});

    // Enter para enviar
    elements.userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && this.value.trim() && !elements.sendBtn.disabled && !this.disabled) {
        sendMessage(this.value.trim());
        this.value = '';
        updateTokenCounter(0);
    }
});
    
    // Cerrar menú al hacer clic fuera
    document.addEventListener('click', handleOutsideClick);
    
    // 🆕 Botón para limpiar historial
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearAllConversationHistory);
    }
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

    if (['descubre', 'aprende', 'busqueda_web'].includes(section)) {
        setMode(section, { source: 'manual' });
    }

    if (section === 'tasks') {
        if (elements.tasksSection) {
            elements.tasksSection.classList.toggle('active');
            elements.tasksSection.style.display = elements.tasksSection.classList.contains('active') ? 'flex' : 'none';
        }
        if (elements.tasksContainer) {
            elements.tasksContainer.classList.toggle('active');
        }
    } else {
        if (elements.tasksSection) {
            elements.tasksSection.classList.remove('active');
            elements.tasksSection.style.display = 'none';
        }
        if (elements.tasksContainer) {
            elements.tasksContainer.classList.remove('active');
        }
    }

    if (window.innerWidth < 900) {
        closeSidebar();
    }
}


function generateNewConversationId() {
    const newId =
        'session_' +
        Date.now() +
        '_' +
        Math.random().toString(36).substr(2, 9);

    sessionStorage.setItem('claroAssistant_sessionId', newId);
    return newId;
}

function startNewConversation() {
    try {
        // 🔑 0️⃣ Guardar conversación anterior en el historial
        if (appState.conversationHistory.length >= 2) {
            saveCurrentConversation();
        }

        // 🆕 1️⃣ Resetear flag de historial
        appState.isLoadedFromHistory = false;

        // 🔑 2️⃣ Generar NUEVO conversationId
        const newSessionId = generateNewConversationId();
        console.log('🔑 Nueva conversationId generada:', newSessionId);

        // 🧹 3️⃣ Reset de estado interno
        appState.conversationHistory = [];
        userState.messageCount = 0;

        // Limpiar UI del chat
        if (elements.chatHistory) {
            elements.chatHistory.innerHTML = '';
        }

        // 🧭 4️⃣ Reset de vistas
        if (elements.welcomePage) {
            elements.welcomePage.style.display = 'flex';
        }
        if (elements.chatPage) {
            elements.chatPage.style.display = 'none';
        }

        // 🎠 5️⃣ Mostrar carrusel de sugerencias (si existe)
        const carousel = document.getElementById('suggestionsCarousel');
        if (carousel) {
            carousel.style.display = 'block';
        }

        // 🚦 6️⃣ Reset de límites y UI
        if (typeof removeLimitWarning === 'function') {
            removeLimitWarning();
        }
        if (typeof hideModeChip === 'function') {
            hideModeChip();
        }

        // 🆕 7️⃣ Reset de modo y placeholder
        if (elements.userInput) {
            elements.userInput.placeholder = 'Pregunta lo que quieras';
        }
        appState.currentMode = 'descubre';
        appState.modeActivatedManually = false;

        // 🧩 8️⃣ Reset visual del menú de acciones
        if (elements.actionItems) {
            elements.actionItems.forEach(item => {
                item.classList.toggle(
                    'selected',
                    item.getAttribute('data-action') === 'descubre'
                );
            });
        }

        // 💾 9️⃣ Persistencia limpia
        saveToLocalStorage();

        // 📌 🔟 Navegación sidebar
        if (elements.navItems) {
            elements.navItems.forEach(item => item.classList.remove('active'));
        }

        if (elements.newConversationBtn) {
            elements.newConversationBtn.classList.add('active');
        }

        // 📱 1️⃣1️⃣ Responsive
        if (window.innerWidth < 900 && typeof closeSidebar === 'function') {
            closeSidebar();
        }

        // 🔄 Actualizar historial de conversaciones
        updateConversationHistoryUI();

        console.log('🆕 Nueva conversación iniciada correctamente');

    } catch (error) {
        console.error('❌ Error en startNewConversation:', error);
    }
}
/**
 * Guarda la conversación actual en el historial
 */
function saveCurrentConversation() {
    // No guardar si la conversación fue cargada desde el historial
    if (appState.isLoadedFromHistory) {
        console.log('ℹ️ Conversación saltada (fue cargada desde historial)');
        appState.isLoadedFromHistory = false;
        return null;
    }
    
    // Verificar que saveConversation esté disponible
    if (typeof saveConversation !== 'function') {
        console.error('❌ saveConversation no está disponible');
        return null;
    }
    
    // Solo guardar si hay más de 1 mensaje (al menos 1 usuario + 1 bot)
    if (appState.conversationHistory.length >= 2) {
        const userMessages = appState.conversationHistory.filter(m => (m.type || m.role) === 'user');
        const botMessages = appState.conversationHistory.filter(m => (m.type || m.role) === 'bot');
        
        // Solo guardar si hay al menos 1 mensaje del usuario Y 1 respuesta del bot
        if (userMessages.length > 0 && botMessages.length > 0) {
            const firstMessage = userMessages[0];
            const title = firstMessage ? firstMessage.content.substring(0, 50) : 'Conversación sin título';
            
            const conversationId = saveConversation(appState.conversationHistory, title);
            
            // Actualizar UI después de guardar
            setTimeout(() => {
                updateConversationHistoryUI();
            }, 100);
            
            console.log('💾 Conversación guardada en historial:', conversationId);
            return conversationId;
        }
    }
    
    return null;
}

// ==================== TASK MANAGEMENT (ESTILO ORIGINAL) ====================
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

function toggleTaskCategory(e) {
    e.stopPropagation();
    const header = e.currentTarget;
    const category = header.closest('.task-category');
    if (!category) return;

    const taskList = category.querySelector('.task-list');
    const toggleIcon = header.querySelector('.task-category-toggle .material-symbols-outlined');

    if (!taskList) return;

    const isVisible = taskList.style.display !== 'none' && taskList.style.display !== '';

    if (isVisible) {
        taskList.style.display = 'none';
        if (toggleIcon) {
            toggleIcon.style.transform = 'rotate(-90deg)';
        }
    } else {
        taskList.style.display = 'flex';
        if (toggleIcon) {
            toggleIcon.style.transform = 'rotate(0deg)';
        }
    }
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

function expandTaskCategory(taskType) {
    const categoryMap = {
        'reminders': 'reminders',
        'notes': 'notes',
        'calendar': 'calendar'
    };

    const category = categoryMap[taskType];
    if (!category) return;

    const targetHeader = document.querySelector(`.task-category-header[data-category="${category}"]`);
    if (targetHeader) {
        const taskCategory = targetHeader.closest('.task-category');
        if (taskCategory) {
            const taskList = taskCategory.querySelector('.task-list');
            const toggleIcon = targetHeader.querySelector('.task-category-toggle .material-symbols-outlined');

            if (taskList) {
                taskList.style.display = 'flex';
                if (toggleIcon) {
                    toggleIcon.style.transform = 'rotate(0deg)';
                }
            }
        }
    }
}

// 🆕 Función para mostrar la sección de tareas (estilo original)
function showTasksSection(taskType) {
    // Mostrar la sección de tareas
    if (elements.tasksSection) {
        elements.tasksSection.classList.add('active');
        elements.tasksSection.style.display = 'flex';
    }

    // Mostrar el contenedor de tareas (estilo antiguo, por compatibilidad)
    if (elements.tasksContainer) {
        elements.tasksContainer.classList.add('active');
    }

    // Expandir la categoría correspondiente
    if (taskType) {
        expandTaskCategory(taskType);
    }

    // Actualizar navegación
    elements.navItems.forEach(item => item.classList.remove('active'));
    const tasksNavBtn = document.getElementById('tasksNavBtn');
    if (tasksNavBtn) {
        tasksNavBtn.classList.add('active');
    }
}

// ==================== ACTION MENU FUNCTIONS ====================
function toggleActionMenu(e) {
    e.stopPropagation();
    elements.actionMenu.classList.toggle('active');
}

function selectAction(e) {
    const action = this.getAttribute('data-action');

    setMode(action, { source: 'manual' });
    elements.actionMenu.classList.remove('active');
}


// ==================== MODE CHIP FUNCTIONS ====================
/**
 * Muestra el chip de modo activo
 */
/**
 * Muestra el chip de modo activo con ícono dinámico
 */
function showModeChip(modeName, modeAction) {
    if (!elements.modeChipContainer || !elements.modeChipText) return;
    
    // Actualizar texto del chip
    elements.modeChipText.textContent = modeName;
    
    // Obtener contenedor del ícono
    const iconContainer = document.getElementById('modeChipIcon');
    if (iconContainer) {
        // Limpiar ícono anterior
        iconContainer.innerHTML = '';
        
        // Definir íconos según el modo
        const icons = {
            'aprende': '<div class="mode-chip-icon-letter">A</div>',
            'tareas': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            'busqueda_web': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>'
        };
        
        // Insertar el ícono correspondiente
        iconContainer.innerHTML = icons[modeAction] || icons['busqueda'];
    }
    
    // Mostrar contenedor con animación
    elements.modeChipContainer.style.display = 'flex';
    
    // 🆕 OCULTAR CARRUSEL cuando hay chip activo
    const carousel = document.getElementById('suggestionsCarousel');
    if (carousel) {
        carousel.style.display = 'none';
    }
    
    // Guardar modo activo
    appState.currentMode = modeAction;
    
    console.log(`✅ Chip activado: ${modeName} (${modeAction})`);
}

/**
 * Oculta el chip de modo activo y resetea al modo búsqueda
 */
function hideModeChip() {
    if (!elements.modeChipContainer) return;
    
    elements.modeChipContainer.style.display = 'none';
    if (appState.currentMode !== 'descubre') {
        setMode('descubre', { source: 'manual' });
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
    
    // ===== VALIDACIÓN DE LÍMITE DE MENSAJES =====
if (!userState.isPro && userState.messageCount >= MESSAGE_LIMIT.FREE) {
    showPremiumModal();
    return;
}
    
    showChatView();
    addMessage('user', text);

    // 🔹 Ya NO tocar modeActivatedManually aquí (se controla al activar el modo/manualmente en la UI)
    
    // Incrementar contador de mensajes del usuario
    if (!userState.isPro) {
        userState.messageCount++;
        console.log(`Mensajes enviados: ${userState.messageCount}/${MESSAGE_LIMIT.FREE}`);
        
        // NUEVO: Deshabilitar si alcanza el límite
        if (userState.messageCount >= MESSAGE_LIMIT.FREE) {
            showLimitWarning();
        }
    }
    
    showLoading();
    
    callAPI(text)
    .then(response => {
        addMessage('bot', response);
        
        if (isTaskMessage(text, response)) {
            processTask(text, response);
        }
        
        // 🆕 ACTUALIZAR CONSUMO DESPUÉS DE CADA MENSAJE
        fetchUsageStatus();
        
        // 🆕 MOSTRAR ADVERTENCIA SI ESTÁ CERCA DEL LÍMITE
        setTimeout(() => {
            showUsageWarning();
        }, 500);
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
    const conversationId = sessionStorage.getItem('claroAssistant_sessionId');

    const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Conversation-Id': conversationId   // 👈 CLAVE
        },
        body: JSON.stringify({
            message: message,
            action: appState.currentMode
        })
    });
        
        // ===== MANEJAR ERROR 429 (RATE LIMIT) =====
        if (response.status === 429) {
            const errorData = await response.json();
            throw new Error(errorData.message || '⏱️ Por favor espera unos segundos antes de enviar otro mensaje');
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // 🆕 NUEVA LÓGICA: Priorizar Video > PDF > Página completa
            if (data.aprende_ia_used) {
                // PRIORIDAD 1: Si hay video, usar el video
                if (data.url_video) {
                    appState.lastAprendeResource = {
                        url: data.url_video,
                        tipo: 'video'  // Forzar tipo video
                    };
                    console.log('🎥 Video de Aprende.org detectado:', appState.lastAprendeResource);
                } 
                // PRIORIDAD 2: Si hay PDF, usar el PDF
                else if (data.url_pdf) {
                    appState.lastAprendeResource = {
                        url: data.url_pdf,
                        tipo: 'pdf'  // Forzar tipo PDF
                    };
                    console.log('📄 PDF de Aprende.org detectado:', appState.lastAprendeResource);
                } 
                // PRIORIDAD 3: Si no hay ni video ni PDF, usar la página completa
                else if (data.url_recurso) {
                    appState.lastAprendeResource = {
                        url: data.url_recurso,
                        tipo: data.tipo_recurso || 'curso'  // Página completa del curso
                    };
                    console.log('📚 Página de Aprende.org detectada:', appState.lastAprendeResource);
                }
            } else {
                appState.lastAprendeResource = null;
            }
            
            // =====================================================
            // 🆕 TELCEL: detectar URL de buscador y añadir link (sin iframe)
            // =====================================================
            if (data.action === 'telcel' && Array.isArray(data.relevant_urls)) {
                const telcelSearchUrl = data.relevant_urls.find(
                    url => typeof url === 'string' && url.includes('telcel.com/buscador?')
                );

                if (telcelSearchUrl) {
                    console.log('🔎 Telcel buscador detectado:', telcelSearchUrl);

                    // Añadir enlace al texto de respuesta si no está presente
                    if (!data.response.includes(telcelSearchUrl)) {
                        data.response += `\n\n🔗 **Consulta directa en Telcel:** ` +
                            `[Abrir buscador de Telcel](${telcelSearchUrl})`;
                    }
                }
            }
            
            return data.response;
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

async function initConversationStorage() {
    return new Promise((resolve) => {
        import('./chatStorage.js').then(module => {
            saveConversation = module.saveConversation;
            loadConversations = module.loadConversations;
            loadConversationById = module.loadConversationById;
            deleteConversation = module.deleteConversation;
            clearConversations = module.clearConversations;
            console.log('✅ Módulo de almacenamiento de conversaciones cargado');
            resolve();
        }).catch(e => {
            console.error('❌ Error cargando módulo de conversaciones:', e);
            // Definir funciones vacías como fallback
            saveConversation = () => null;
            loadConversations = () => [];
            loadConversationById = () => null;
            deleteConversation = () => {};
            clearConversations = () => {};
            resolve();
        });
    });
}

function showChatView() {
    elements.welcomePage.style.display = 'none';
    elements.chatPage.style.display = 'flex';

    // Ocultar carrusel cuando hay chat activo
    const carousel = document.getElementById('suggestionsCarousel');
    if (carousel) {
        carousel.style.display = 'none';
    }
}

function addMessage(type, content) {
    // Crear contenedor principal del mensaje
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container ' + type;
    
    // Crear avatar
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar ' + type;
    
    if (type === 'bot') {
        // Avatar del bot (logo de Claro)
        avatarDiv.innerHTML = '<img src="images/logo_claro.png" alt="Claro Assistant">';
    } else {
        // Avatar del usuario (Material Icon)
        avatarDiv.innerHTML = '<span class="material-symbols-outlined">account_circle</span>';
    }
    
    // Crear contenedor del contenido
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Crear el mensaje
    const messageDiv = document.createElement('div');
    messageDiv.className = 'msg ' + type;
    
    const formattedContent = formatMessage(content);
    messageDiv.innerHTML = formattedContent;
    
    // Ensamblar estructura
    contentDiv.appendChild(messageDiv);
    messageContainer.appendChild(avatarDiv);
    messageContainer.appendChild(contentDiv);

    // 🆕 AGREGAR VISOR SI HAY RECURSO DE APRENDE.ORG
if (type === 'bot' && appState.lastAprendeResource) {
    const { url, tipo } = appState.lastAprendeResource;
    
    console.log('📺 Creando visor para:', url, '- Tipo:', tipo);
    
    const mediaViewer = createMediaViewer(url, tipo);
    contentDiv.appendChild(mediaViewer);
    
    // Limpiar después de usar para no mostrarlo en mensajes posteriores
    appState.lastAprendeResource = null;
}
    
    
    
    // Agregar al chat
    elements.chatHistory.appendChild(messageContainer);
    
    // Scroll automático
    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
    
    // Guardar en historial
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
            if (line.startsWith('#### ')) {
        return `<h4 class="msg-header">${escapeHtml(line.substring(5))}</h4>`;
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


// ==================== CREAR VISOR DE MEDIOS ====================
function createMediaViewer(url, type) {
    const viewerDiv = document.createElement('div');
    viewerDiv.className = 'message-media-viewer';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'media-content';
    
    if (type === 'video') {
    const video = document.createElement('video');
    video.src = url;
    video.controls = true;
    video.controlsList = 'nodownload';
    video.disablePictureInPicture = true;
    video.preload = 'metadata';
    video.style.width = '100%';
    video.style.maxHeight = '500px';
    video.style.borderRadius = '8px';
    video.style.backgroundColor = '#000';
    
    // 🆕 Event listeners para debugging
    video.addEventListener('loadstart', () => {
        console.log('🎬 Video: Iniciando carga...');
    });
    
    video.addEventListener('loadedmetadata', () => {
        console.log('✅ Video: Metadata cargada');
    });
    
    video.addEventListener('error', (e) => {
        console.error('❌ Error cargando video:', e);
        console.error('Error code:', video.error?.code);
        console.error('Error message:', video.error?.message);
    });
    
    video.addEventListener('canplay', () => {
        console.log('✅ Video: Listo para reproducir');
    });
    
    contentDiv.appendChild(video);

    // ✅ Aplicar solo protección anti-clic derecho (SIN overlay)
    applyMediaProtection(video);
    
    // ❌ ELIMINADO: Ya no crear overlay que bloquea clics
    // const overlay = document.createElement('div');
    // overlay.className = 'media-protection-overlay';
    // contentDiv.appendChild(overlay);

        
    } else if (type === 'pdf') {
        const iframe = document.createElement('iframe');
        iframe.src = url + '#toolbar=0&navpanes=0&scrollbar=0';
        iframe.setAttribute('sandbox', 'allow-same-origin');
        
        contentDiv.appendChild(iframe);
        
    } else if (type === 'image') {
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Contenido de Aprende.org';
        
        // Protección
        img.addEventListener('contextmenu', (e) => e.preventDefault());
        img.addEventListener('dragstart', (e) => e.preventDefault());
        
        contentDiv.appendChild(img);
    }
    
    // 🆕 NUEVO: SOPORTE PARA CURSOS DE APRENDE.ORG
    else if (type === 'curso' || type === 'diplomado' || type === 'ruta' || type === 'especialidad') {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.className = 'aprende-iframe';
        iframe.style.width = '100%';
        iframe.style.height = '600px';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.setAttribute('allowfullscreen', 'true');
        iframe.setAttribute('loading', 'lazy');
        
        // Log para debugging
        console.log('✅ Iframe de curso creado:', url);
        
        contentDiv.appendChild(iframe);
    }

    // CASO GENÉRICO: PÁGINAS WEB
    else if (type === 'webpage') {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.className = 'webpage-iframe';
        iframe.style.width = '100%';
        iframe.style.height = '600px';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.setAttribute('allowfullscreen', 'true');
        iframe.setAttribute('loading', 'lazy');
        
        contentDiv.appendChild(iframe);
    }
    
    // CASO POR DEFECTO: Si no coincide con ningún tipo, crear iframe genérico
    else {
        console.warn('⚠️ Tipo desconocido:', type, '- Creando iframe genérico');
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.className = 'generic-iframe';
        iframe.style.width = '100%';
        iframe.style.height = '600px';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.setAttribute('allowfullscreen', 'true');
        iframe.setAttribute('loading', 'lazy');
        
        contentDiv.appendChild(iframe);
    }
    
    viewerDiv.appendChild(contentDiv);
    return viewerDiv;
}


// ==================== PROTECCIÓN ANTI-DESCARGA AVANZADA ====================
function applyMediaProtection(mediaElement) {
    if (!mediaElement) return;
    
    // 1. Prevenir clic derecho
    mediaElement.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });
    
    // 2. Prevenir arrastre
    mediaElement.addEventListener('dragstart', (e) => {
        e.preventDefault();
        return false;
    });
    
    // 3. Deshabilitar selección
    mediaElement.style.userSelect = 'none';
    mediaElement.style.webkitUserSelect = 'none';
    
    // 4. Bloquear combinaciones de teclado
    document.addEventListener('keydown', (e) => {
        // Bloquear Ctrl+S, Ctrl+P, PrtScn, F12
        if (
            (e.ctrlKey && (e.key === 's' || e.key === 'p')) ||
            e.key === 'PrintScreen' ||
            e.keyCode === 44 ||
            e.keyCode === 123
        ) {
            e.preventDefault();
            return false;
        }
    });
    
    console.log('🔒 Protección anti-descarga activada');
}

// ==================== TASK MANAGEMENT ====================
function isTaskMessage(userMsg, botMsg) {
    const lowerUserMsg = userMsg.toLowerCase().trim();
    const lowerBotMsg = botMsg.toLowerCase();
    
    // ============ PASO 1: EXCLUIR MENSAJES CORTOS Y PALABRAS SUELTAS ============
    if (lowerUserMsg.length < 15 || !lowerUserMsg.includes(' ')) {
        return false;
    }
    
    // ============ PASO 2: EXCLUIR PREGUNTAS ============
    const questionWords = ['qué', 'que', 'cómo', 'como', 'cuál', 'cual', 'cuáles', 
                          'cuales', 'dónde', 'donde', 'cuándo', 'cuando', 'por qué', 
                          'porque', 'quién', 'quien'];
    
    if (questionWords.some(q => lowerUserMsg.includes(q)) && 
        !botMsg.includes('✅') && !botMsg.includes('📝') && !botMsg.includes('📅')) {
        return false;
    }
    
    // ============ PASO 3: EXCLUIR PALABRAS DE CONSULTA ============
    const consultaWords = ['dime', 'dimelo', 'dame', 'muestra', 'explica', 'explicame',
                           'ayuda', 'ayudame', 'busca', 'encuentra', 'hablame', 'háblame'];
    
    if (consultaWords.some(w => lowerUserMsg.startsWith(w)) && 
        !botMsg.includes('✅') && !botMsg.includes('📝') && !botMsg.includes('📅')) {
        return false;
    }
    
    // ============ PASO 4: VERBOS / FRASES DE TAREA ============
    const taskVerbs = {
        // Frases típicas de recordatorios
        reminders: [
            'recuerdame', 'recuérdame', 'recordarme', 'avisame', 'avísame',
            'recordatorio', 'no olvides', 'que no se me olvide'
        ],
        // Frases típicas de notas
        notes: [
            'nota', 'toma nota', 'anota', 'apunta',
            'guarda esto', 'guardar esto', 'guarda la nota'
        ],
        // Frases típicas de agenda / calendario
        calendar: [
            'agendar', 'agenda ', 'agrega a la agenda',
            'pon en la agenda', 'programar', 'programa ',
            'cita para', 'agenda una cita'
        ]
    };
    
    let hasTaskVerb = false;
    for (const category in taskVerbs) {
        if (taskVerbs[category].some(verb => lowerUserMsg.includes(verb))) {
            hasTaskVerb = true;
            break;
        }
    }
    
    // ============ PASO 5: O SI EL BOT CONFIRMA CON EMOJIS ============
    const hasBotEmoji = botMsg.includes('✅') || botMsg.includes('📝') || botMsg.includes('📅');
    const botConfirms = lowerBotMsg.includes('he creado') || 
                       lowerBotMsg.includes('he guardado') || 
                       lowerBotMsg.includes('he agendado');
    
    // ============ DECISIÓN FINAL ============
    return hasTaskVerb || (hasBotEmoji && botConfirms);
}


async function processTask(userMessage, botResponse) {
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
    
    // 🔹 1) PRIORIZAR AGENDA / CALENDARIO
    if (
        lowerUserMsg.includes('agendar') || 
        lowerUserMsg.includes('agenda ') ||
        lowerUserMsg.includes('agrega a la agenda') ||
        lowerUserMsg.includes('pon en la agenda') ||
        lowerUserMsg.includes('programar') ||
        lowerUserMsg.includes('programa ') ||
        (lowerUserMsg.includes('cita') && !lowerUserMsg.includes('recordar')) ||
        botResponse.includes('📅') ||
        lowerBotMsg.includes('agendado') ||
        lowerBotMsg.includes('he agendado')
    ) {
        taskType = 'calendar';
    } 
    
    // 🔹 2) LUEGO RECORDATORIOS
    else if (
        lowerUserMsg.includes('recordar') || 
        lowerUserMsg.includes('recuerdame') || 
        lowerUserMsg.includes('recuérdame') ||
        lowerUserMsg.includes('avisame') ||
        lowerUserMsg.includes('avísame') ||
        lowerUserMsg.includes('recordatorio') ||
        lowerUserMsg.includes('no olvides') ||
        lowerUserMsg.includes('que no se me olvide') ||
        (botResponse.includes('✅') && !lowerUserMsg.includes('agendar')) ||
        (lowerBotMsg.includes('recordatorio') && !lowerBotMsg.includes('agendado'))
    ) {
        taskType = 'reminders';
    } 
    
    // 🔹 3) POR ÚLTIMO, NOTAS
    else if (
        lowerUserMsg.includes('nota') || 
        lowerUserMsg.includes('toma nota') ||
        lowerUserMsg.includes('anota') || 
        lowerUserMsg.includes('apunta') ||
        lowerUserMsg.includes('guardar') ||
        lowerUserMsg.includes('guarda esto') ||
        lowerUserMsg.includes('guarda la nota') ||
        botResponse.includes('📝') ||
        lowerBotMsg.includes('nota guardada') ||
        lowerBotMsg.includes('he guardado')
    ) {
        taskType = 'notes';
    }
    
    // 🔹 4) SI NO SE DETECTÓ TIPO, CAE COMO RECORDATORIO
    if (!taskType) {
        taskType = 'reminders';
    }
    
    if (!appState.tasks[taskType]) {
        appState.tasks[taskType] = [];
    }

    // Si es evento de calendario, generar archivo .ics
    if (taskType === 'calendar') {
        await generateICSForTask(task);
    }

    appState.tasks[taskType].push(task);
    updateTasksUI();

    // Si es calendario, actualizar UI después de generar el archivo
    if (taskType === 'calendar') {
        setTimeout(() => {
            updateTasksUI();
        }, 100);
    }
    
    // Mostrar sección de tareas (estilo original)
    showTasksSection(taskType);
    
    saveToLocalStorage();

    // Debug opcional
    console.log('[TASK CREADA]', { taskType, userMessage });
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

    // Actualizar badge en navegación
    const tasksCountNav = document.getElementById('tasksCountNav');
    if (tasksCountNav) {
        tasksCountNav.textContent = `(${totalTasks})`;
    }

    console.log(`📊 Tareas actualizadas: ${totalTasks} en total`);
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
        ${false && taskType === 'calendar' && task.icsFileUrl ? `
        <button class="task-download" onclick="downloadICSFile('${task.icsFileUrl}', '${task.icsFileName}')" title="Descargar evento">
            <span class="material-symbols-outlined">download</span>
        </button>
        ` : ''}
        <button class="task-delete" onclick="deleteTask('${taskType}', ${idx})" title="Eliminar">
            <span class="material-symbols-outlined">close</span>
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
            sessionId: sessionStorage.getItem('claroAssistant_sessionId'),
            messageCount: userState.messageCount,  // NUEVO
            isPro: userState.isPro  // NUEVO
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
                appState.currentMode = data.currentMode || 'descubre';
                userState.messageCount = data.messageCount || 0;
                userState.isPro = data.isPro || false;
                
                // NUEVO: Deshabilitar input si ya alcanzó el límite
                if (!userState.isPro && userState.messageCount >= MESSAGE_LIMIT.FREE) {
                    showLimitWarning();
                }
                
                if (appState.conversationHistory.length > 0) {
                    showChatView();
                    elements.chatHistory.innerHTML = '';
                    
                    appState.conversationHistory.forEach(msg => {
                        const messageContainer = document.createElement('div');
                        messageContainer.className = 'message-container ' + msg.type;
                        
                        const avatarDiv = document.createElement('div');
                        avatarDiv.className = 'message-avatar ' + msg.type;
                        
                        if (msg.type === 'bot') {
                            avatarDiv.innerHTML = '<img src="images/logo_claro.png" alt="Claro Assistant">';
                        } else {
                            avatarDiv.innerHTML = '<span class="material-symbols-outlined">account_circle</span>';
                        }
                        
                        const contentDiv = document.createElement('div');
                        contentDiv.className = 'message-content';
                        
                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'msg ' + msg.type;
                        messageDiv.innerHTML = formatMessage(msg.content);
                        
                        contentDiv.appendChild(messageDiv);
                        messageContainer.appendChild(avatarDiv);
                        messageContainer.appendChild(contentDiv);
                        
                        elements.chatHistory.appendChild(messageContainer);
                    });
                    
                    console.log('Conversacion restaurada');
                }
                
                updateTasksUI();
                console.log('Tareas cargadas:', appState.tasks);
                console.log(`Mensajes usados: ${userState.messageCount}/${MESSAGE_LIMIT.FREE}`);
            } else {
                console.log('Nueva pestana - chat limpio');
            }
        }
    } catch (e) {
        console.error('Error cargando desde localStorage:', e);
    }
}


// ==================== FUNCIONES DEL MODAL PREMIUM ====================
function showPremiumModal() {
    const overlay = document.getElementById('premiumOverlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

function closePremiumModal() {
    const overlay = document.getElementById('premiumOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ==================== FUNCIONES DE HISTORIAL DE CONVERSACIONES ====================
/**
 * Importa las funciones necesarias de chatStorage
 */
let saveConversation, loadConversations, loadConversationById, deleteConversation, clearConversations;

// Carga inmediata del módulo de chatStorage
(async function() {
    try {
        // Intenta cargar las funciones del módulo ES6
        const module = await import('./chatStorage.js');
        saveConversation = module.saveConversation;
        loadConversations = module.loadConversations;
        loadConversationById = module.loadConversationById;
        deleteConversation = module.deleteConversation;
        clearConversations = module.clearConversations;
        console.log('✅ Módulo de almacenamiento de conversaciones cargado');
    } catch (e) {
        console.error('❌ Error cargando módulo de conversaciones:', e);
        
        // Fallback: definir funciones básicas si falla la importación
        saveConversation = (messages, title) => {
            console.warn('Fallback: saveConversation llamado');
            return null;
        };
        loadConversations = () => [];
        loadConversationById = () => null;
        deleteConversation = () => {};
        clearConversations = () => {};
    }
})();

/**
 * Actualiza la UI del listado de conversaciones en el sidebar
 */
function updateConversationHistoryUI() {
    const historyList = document.getElementById('conversationHistoryList');
    if (!historyList) return;
    
    // Validar que las funciones de almacenamiento estén cargadas
    if (typeof loadConversations !== 'function') {
        console.warn('⚠️ Las funciones de almacenamiento aún no están cargadas');
        return;
    }
    
    const conversations = loadConversations();
    
    if (conversations.length === 0) {
        historyList.innerHTML = '<div class="no-conversations">Sin conversaciones</div>';
        return;
    }
    
    historyList.innerHTML = '';
    
    conversations.forEach(conversation => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.dataset.conversationId = conversation.id;
        
        const title = document.createElement('span');
        title.className = 'history-item-title';
        title.textContent = conversation.title;
        title.addEventListener('click', () => loadConversationFromHistory(conversation.id));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'history-item-delete';
        deleteBtn.innerHTML = '✕';
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conversation.id);
            updateConversationHistoryUI();
            console.log('🗑️ Conversación eliminada');
        });
        
        item.appendChild(title);
        item.appendChild(deleteBtn);
        historyList.appendChild(item);
    });
}
/**
 * Carga una conversación del historial
 */
function loadConversationFromHistory(conversationId) {
    if (typeof loadConversationById !== 'function') {
        console.error('❌ loadConversationById no está disponible');
        return;
    }
    
    const conversation = loadConversationById(conversationId);
    
    if (conversation) {
        // Guardar conversación actual antes de cargar una nueva
        saveCurrentConversation();
        
        // Generar nuevo session ID para esta conversación
        const newSessionId = generateNewConversationId();
        
        // Cargar los mensajes
        appState.conversationHistory = conversation.messages || [];
        
        // 🆕 MARCAR que fue cargada desde el historial
        appState.isLoadedFromHistory = true;
        
        // Mostrar vista de chat
        showChatView();
        elements.chatHistory.innerHTML = '';
        
        // Renderizar mensajes
        appState.conversationHistory.forEach(msg => {
            const messageContainer = document.createElement('div');
            messageContainer.className = 'message-container ' + (msg.type || msg.role);
            
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'message-avatar ' + (msg.type || msg.role);
            
            if ((msg.type || msg.role) === 'bot') {
                avatarDiv.innerHTML = '<img src="images/logo_claro.png" alt="Claro Assistant">';
            } else {
                avatarDiv.innerHTML = '<span class="material-symbols-outlined">account_circle</span>';
            }
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            const messageDiv = document.createElement('div');
            messageDiv.className = 'msg ' + (msg.type || msg.role);
            messageDiv.innerHTML = formatMessage(msg.content);
            
            contentDiv.appendChild(messageDiv);
            messageContainer.appendChild(avatarDiv);
            messageContainer.appendChild(contentDiv);
            
            elements.chatHistory.appendChild(messageContainer);
        });
        
        // Scroll al final
        setTimeout(() => {
            elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
        }, 100);
        
        saveToLocalStorage();
        updateConversationHistoryUI();
        console.log('📂 Conversación cargada desde historial:', conversationId);
    } else {
        console.error('❌ No se pudo cargar la conversación:', conversationId);
    }
}
/**
 * Limpia todo el historial de conversaciones
 */
function clearAllConversationHistory() {
    if (confirm('¿Eliminar todo el historial de conversaciones? Esta acción no se puede deshacer.')) {
        clearConversations();
        updateConversationHistoryUI();
        console.log('🗑️ Todo el historial fue eliminado');
    }
}

// Exponer funciones globalmente
window.saveCurrentConversation = saveCurrentConversation;
window.loadConversationFromHistofry = loadConversationFromHistory;
window.clearAllConversationHistory = clearAllConversationHistory;


// ==================== CARRUSEL DE SUGERENCIAS ====================
document.addEventListener('DOMContentLoaded', function() {
    // Solo funcionalidad de scroll con arrastre (SIN clics)
    const carouselContainer = document.querySelector('.carousel-container');
    if (carouselContainer) {
        let isDown = false;
        let startX;
        let scrollLeft;
        
        carouselContainer.addEventListener('mousedown', (e) => {
            isDown = true;
            startX = e.pageX - carouselContainer.offsetLeft;
            scrollLeft = carouselContainer.scrollLeft;
            carouselContainer.style.cursor = 'grabbing';
        });
        
        carouselContainer.addEventListener('mouseleave', () => {
            isDown = false;
            carouselContainer.style.cursor = 'grab';
        });
        
        carouselContainer.addEventListener('mouseup', () => {
            isDown = false;
            carouselContainer.style.cursor = 'grab';
        });
        
        carouselContainer.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - carouselContainer.offsetLeft;
            const walk = (x - startX) * 2;
            carouselContainer.scrollLeft = scrollLeft - walk;
        });
    }
});


// ==================== FUNCIONES PARA DESHABILITAR INPUT ====================
function showLimitWarning() {
    elements.userInput.value = '';
    elements.userInput.placeholder = '⚠️ Límite alcanzado - Hazte Pro';
    elements.userInput.readOnly = true; // Cambiar a solo lectura en lugar de disabled
    elements.userInput.style.cursor = 'pointer';
    elements.userInput.style.fontWeight = '500';
    elements.userInput.style.color = '#DA291C';
    elements.sendBtn.disabled = true;
    elements.sendBtn.style.opacity = '0.5';
    elements.sendBtn.style.cursor = 'not-allowed';
    
    // Agregar clase para identificar estado de límite
    elements.userInput.classList.add('limit-reached');
}

function removeLimitWarning() {
    elements.userInput.placeholder = 'Pregunta lo que quieras';
    elements.userInput.readOnly = false;
    elements.userInput.style.cursor = 'text';
    elements.userInput.style.fontWeight = 'normal';
    elements.userInput.style.color = '';
    elements.sendBtn.disabled = false;
    elements.sendBtn.style.opacity = '1';
    elements.sendBtn.style.cursor = 'pointer';
    
    // Remover clase de límite
    elements.userInput.classList.remove('limit-reached');
}

function upgradeToPro() {
    // Solo cerrar el modal sin mostrar alerta
    closePremiumModal();
    
    // OPCIONAL: Si quieres redirigir a una página real de upgrade:
    // window.location.href = '/upgrade';
    
    // OPCIONAL: Para testing, puedes activar Pro temporalmente descomentando estas líneas:
    /*
    userState.isPro = true;
    userState.messageCount = 0;
    enableInput();
    saveToLocalStorage();
    console.log('✅ Modo Pro activado (testing)');
    */
}

// Event Listeners para el modal
document.addEventListener('DOMContentLoaded', function() {
    const btnUpgradePro = document.getElementById('btnUpgradePro');
    const btnClosePremium = document.getElementById('btnClosePremium');
    const premiumOverlay = document.getElementById('premiumOverlay');
    
    if (btnUpgradePro) {
        btnUpgradePro.addEventListener('click', upgradeToPro);
    }
    
    if (btnClosePremium) {
        btnClosePremium.addEventListener('click', closePremiumModal);
    }
    
    // Cerrar al hacer clic fuera del modal
    if (premiumOverlay) {
        premiumOverlay.addEventListener('click', function(e) {
            if (e.target === premiumOverlay) {
                closePremiumModal();
            }
        });
    }
});

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
