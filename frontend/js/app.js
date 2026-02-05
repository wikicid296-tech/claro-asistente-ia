// ==================== CONFIGURACIÓN Y VARIABLES GLOBALES ====================
const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://claro-asistente-ia.onrender.com';

const MESSAGE_LIMIT = {
    FREE: 20,
    PRO: Infinity
};

const userState = {
    isPro: false,
    messageCount: 0
};

const TOKEN_CONFIG = {
    MAX_TOKENS: 1000,
    CHARS_PER_TOKEN: 3.5
};

const appState = {
    currentMode: 'descubre',
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
    modeActivatedManually: false,
    isLoadedFromHistory: false
};
import { showAlert } from './modules/uiHelpers.js';
import {
    processTask,
    renderSidebarTasks,
    normalizeTaskPayload
} from './modules/taskManager.js';
import { taskStore as taskStoreModule, setTaskStore } from './modules/state.js';

let taskStore = [];

// Elementos del DOM
const elements = {
    sidebar: document.getElementById('sidebar'),
    overlay: document.getElementById('overlay'),
    menuToggle: document.getElementById('menuToggle'),
    navItems: document.querySelectorAll('.nav-item'),
    newConversationBtn: document.getElementById('newConversationBtn'),
    welcomePage: document.getElementById('welcomePage'),
    chatPage: document.getElementById('chatPage'),
    chatHistory: document.getElementById('chatHistory'),
    userInput: document.getElementById('userInput'),
    sendBtn: document.getElementById('sendBtn'),
    addBtn: document.getElementById('addBtn'),
    actionMenu: document.getElementById('actionMenu'),
    actionItems: document.querySelectorAll('.action-item'),
    tokenCounter: document.getElementById('tokenCounter'),
    currentTokens: document.getElementById('currentTokens'),
    maxTokens: document.getElementById('maxTokens'),
    suggestionCards: document.querySelectorAll('.suggestion-card'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    modeChipContainer: document.getElementById('modeChipContainer'),
    modeChipText: document.getElementById('modeChipText'),
    modeChipClose: document.getElementById('modeChipClose'),
    usageMeter: document.getElementById('usageMeter'),
    usageFill: document.getElementById('usageFill'),
    usageText: document.getElementById('usageText')
};

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
        tareas: 'Gestiona tus tareas',
        aprende: 'Pregunta sobre cursos de aprende.org',
        busqueda_web: 'Busca cualquier información en la web...'
    };

    const modeNames = {
        descubre: 'Descubre',
        tareas: 'Gestión de tareas',
        aprende: 'Aprende.org',
        busqueda_web: 'Búsqueda web'
    };

    appState.currentMode = mode;
    appState.modeActivatedManually = source === 'manual';

    if (elements.userInput) {
        elements.userInput.placeholder = placeholders[mode] || placeholders.descubre;
    }

    if (mode === 'descubre') {
        hideModeChip();
    } else {
        showModeChip(modeNames[mode], mode);
    }

    elements.navItems.forEach(item => {
        item.classList.toggle(
            'active',
            item.getAttribute('data-section') === mode
        );
    });

    elements.actionItems.forEach(item => {
        item.classList.toggle(
            'selected',
            item.getAttribute('data-action') === mode
        );
    });

    console.log(`🔄 Modo activo: ${mode} (source: ${source})`);
}

// ==================== FUNCIONES DE CONSUMO ====================
async function fetchUsageStatus() {
    try {
        const response = await fetch(`${API_URL}/usage`);

        if (!response.ok) {
            console.error('Error consultando /usage:', response.status);
            return;
        }

        const data = await response.json();

        if (data.auto_triggered === true && data.action === 'busqueda_web_auto') {
            handleAutoWebSearchUX();
        }

        if (data.success) {
            usageState.consumed = data.consumed;
            usageState.limit = data.limit;
            usageState.percentage = data.percentage;
            usageState.blocked = data.blocked;
            usageState.warning = data.warning;

            updateUsageMeter();

            if (usageState.blocked) {
                blockInputDueToUsage();
            }
        }
    } catch (error) {
        console.error('Error fetching usage:', error);
    }
}

function handleAutoWebSearchUX() {
    setMode('busqueda_web', { source: 'auto' });
    showAutoWebSearchToast();
}

function updateUsageMeter() {
    if (!elements.usageMeter || !elements.usageFill || !elements.usageText) return;

    elements.usageMeter.style.display = 'flex';
    elements.usageFill.style.width = `${usageState.percentage}%`;
    elements.usageText.textContent = `$${usageState.consumed}/$${usageState.limit}`;

    elements.usageFill.classList.remove('warning', 'danger');

    if (usageState.percentage >= 100) {
        elements.usageFill.classList.add('danger');
    } else if (usageState.percentage >= 90) {
        elements.usageFill.classList.add('warning');
    }

    console.log(`💰 Consumo: $${usageState.consumed}/$${usageState.limit} (${usageState.percentage}%)`);
}

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

function showUsageWarning() {
    if (usageState.warning && !usageState.blocked) {
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
function estimateTokens(text) {
    if (!text || text.length === 0) {
        return 0;
    }
    return Math.ceil(text.length / TOKEN_CONFIG.CHARS_PER_TOKEN);
}

function updateTokenCounter(tokens) {
    if (!elements.currentTokens) return;

    elements.currentTokens.textContent = tokens;

    const percentage = (tokens / TOKEN_CONFIG.MAX_TOKENS) * 100;
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
function detectModeFromText(text) {
    const lowerText = text ? text.toLowerCase().trim() : '';

    const modeKeywords = {
        'aprende': ['aprende', 'aprende.org', 'aprender', 'curso', 'cursos', 'estudio'],
        'busqueda_web': ['google', 'buscar', 'internet', 'web', 'información', 'investigar', 'investigación']
    };

    function matchesKeywordStrict(haystack, keyword) {
        if (!haystack || !keyword) return false;
        const esc = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const pattern = '(^|\\W)' + esc + '(\\W|$)';
        return new RegExp(pattern, 'i').test(haystack);
    }

    if (appState.modeActivatedManually) {
        return;
    }

    if (!text || text.length < 3) {
        return;
    }

    for (const [mode, keywords] of Object.entries(modeKeywords)) {
        for (const keyword of keywords) {
            if (matchesKeywordStrict(lowerText, keyword)) {
                if (appState.currentMode !== mode) {
                    activateModeAutomatically(mode);
                }
                return;
            }
        }
    }

    if (appState.currentMode !== 'descubre' && !appState.modeActivatedManually) {
        deactivateAutoMode();
    }
}

function activateModeAutomatically(mode) {
    setMode(mode, { source: 'auto' });
}

function deactivateAutoMode() {
    setMode('descubre', { source: 'auto' });
}

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', async function() {
    initializeEventListeners();
    loadFromLocalStorage();

    renderTaskSidebar();

    await initConversationStorage();

    if (elements.maxTokens) {
        elements.maxTokens.textContent = TOKEN_CONFIG.MAX_TOKENS;
    }
    updateTokenCounter(0);

    setTimeout(() => {
        updateConversationHistoryUI();
    }, 500);

    fetchUsageStatus();
});

function initializeEventListeners() {
    elements.menuToggle.addEventListener('click', toggleSidebar);
    elements.overlay.addEventListener('click', closeSidebar);

    elements.navItems.forEach(item => {
        item.addEventListener('click', handleNavigation);
    });

    if (elements.newConversationBtn) {
        elements.newConversationBtn.addEventListener('click', startNewConversation);
    }

    elements.addBtn.addEventListener('click', toggleActionMenu);

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

    elements.actionItems.forEach(item => {
        item.addEventListener('click', selectAction);
    });

    elements.suggestionCards.forEach(card => {
        card.addEventListener('click', handleSuggestionClick);
    });

    if (elements.modeChipClose) {
        elements.modeChipClose.addEventListener('click', hideModeChip);
    }

    elements.userInput.addEventListener('input', function() {
        const tokens = estimateTokens(this.value);
        updateTokenCounter(tokens);
        detectModeFromText(this.value);
    });

    elements.userInput.addEventListener('click', function() {
        if (this.classList.contains('limit-reached')) {
            showPremiumModal();
        }
    });

    elements.userInput.addEventListener('focus', function() {
        if (this.classList.contains('limit-reached')) {
            this.blur();
            showPremiumModal();
        }
    });

    elements.userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && this.value.trim() && !elements.sendBtn.disabled && !this.disabled) {
            sendMessage(this.value.trim());
            this.value = '';
            updateTokenCounter(0);
        }
    });

    if (elements.chatHistory) {
        elements.chatHistory.addEventListener('click', handleAprendeLinkClick);
    }

    document.addEventListener('click', handleOutsideClick);

    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', clearAllConversationHistory);
    }

    // Las interacciones de la sección de tareas (tanto el header como cada categoría)
    // se configuran en setupTasksSectionToggle() para evitar manejadores duplicados.
    setupTasksSectionToggle();

    // Configurar toggles de categorías individuales (si aún se usan)
    setupCategoryToggles();
}

// ==================== TOGGLE TASK PREVIEW ====================
function toggleTaskPreview(taskType) {
    const preview = document.getElementById(`${taskType}-preview`);
    if (preview) {
        preview.classList.toggle('active');
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
        if (appState.conversationHistory.length >= 2) {
            saveCurrentConversation();
        }

        appState.isLoadedFromHistory = false;

        const newSessionId = generateNewConversationId();
        console.log('🔑 Nueva conversationId generada:', newSessionId);

        appState.conversationHistory = [];
        userState.messageCount = 0;

        if (elements.chatHistory) {
            elements.chatHistory.innerHTML = '';
        }

        if (elements.welcomePage) {
            elements.welcomePage.style.display = 'flex';
        }
        if (elements.chatPage) {
            elements.chatPage.style.display = 'none';
        }

        const carousel = document.getElementById('suggestionsCarousel');
        if (carousel) {
            carousel.style.display = 'block';
        }

        if (typeof removeLimitWarning === 'function') {
            removeLimitWarning();
        }
        if (typeof hideModeChip === 'function') {
            hideModeChip();
        }

        if (elements.userInput) {
            elements.userInput.placeholder = 'Pregunta lo que quieras';
        }
        appState.currentMode = 'descubre';
        appState.modeActivatedManually = false;

        if (elements.actionItems) {
            elements.actionItems.forEach(item => {
                item.classList.toggle(
                    'selected',
                    item.getAttribute('data-action') === 'descubre'
                );
            });
        }

        saveToLocalStorage();

        if (elements.navItems) {
            elements.navItems.forEach(item => item.classList.remove('active'));
        }

        if (elements.newConversationBtn) {
            elements.newConversationBtn.classList.add('active');
        }

        if (window.innerWidth < 900 && typeof closeSidebar === 'function') {
            closeSidebar();
        }

        updateConversationHistoryUI();

        console.log('🆕 Nueva conversación iniciada correctamente');

    } catch (error) {
        console.error('❌ Error en startNewConversation:', error);
    }
}

function saveCurrentConversation() {
    if (appState.isLoadedFromHistory) {
        console.log('ℹ️ Conversación saltada (fue cargada desde historial)');
        appState.isLoadedFromHistory = false;
        return null;
    }

    if (typeof saveConversation !== 'function') {
        console.error('❌ saveConversation no está disponible');
        return null;
    }

    if (appState.conversationHistory.length >= 2) {
        const userMessages = appState.conversationHistory.filter(m => (m.type || m.role) === 'user');
        const botMessages = appState.conversationHistory.filter(m => (m.type || m.role) === 'bot');

        if (userMessages.length > 0 && botMessages.length > 0) {
            const firstMessage = userMessages[0];
            const title = firstMessage ? firstMessage.content.substring(0, 50) : 'Conversación sin título';

            const conversationId = saveConversation(appState.conversationHistory, title);

            setTimeout(() => {
                updateConversationHistoryUI();
            }, 100);

            console.log('💾 Conversación guardada en historial:', conversationId);
            return conversationId;
        }
    }

    return null;
}

function handleOutsideClick(e) {
    if (elements.actionMenu && elements.actionMenu.classList.contains('active')) {
        const clickedInsideMenu = elements.actionMenu.contains(e.target);
        const clickedAddBtn = elements.addBtn && elements.addBtn.contains(e.target);

        if (!clickedInsideMenu && !clickedAddBtn) {
            elements.actionMenu.classList.remove('active');
        }
    }

    if (
        elements.sidebar &&
        elements.sidebar.classList.contains('active') &&
        !elements.sidebar.contains(e.target) &&
        elements.menuToggle &&
        !elements.menuToggle.contains(e.target)
    ) {
        closeSidebar();
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
function showModeChip(modeName, modeAction) {
    if (!elements.modeChipContainer || !elements.modeChipText) return;

    elements.modeChipText.textContent = modeName;

    const iconContainer = document.getElementById('modeChipIcon');
    if (iconContainer) {
        iconContainer.innerHTML = '';

        const icons = {
            'aprende': '<div class="mode-chip-icon-letter">A</div>',
            'tareas': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
            'busqueda_web': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'
        };

        iconContainer.innerHTML = icons[modeAction] || icons['busqueda'];
    }

    elements.modeChipContainer.style.display = 'flex';

    const carousel = document.getElementById('suggestionsCarousel');
    if (carousel) {
        carousel.style.display = 'none';
    }

    appState.currentMode = modeAction;

    console.log(`✅ Chip activado: ${modeName} (${modeAction})`);
}

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

    showChatView();
    addMessage('user', text);

    if (!userState.isPro) {
        userState.messageCount++;
        console.log(`Mensajes enviados: ${userState.messageCount}/${MESSAGE_LIMIT.FREE}`);

        if (userState.messageCount === MESSAGE_LIMIT.FREE) {
            showPremiumModal();
        }
    }

    showLoading();

    callAPI(text)
        .then(data => {
            // Normalizar payload (root/nested) para estabilizar flujo ICS
            const normalized = normalizeTaskPayload(data);

            let botMessage = normalized.response || data.response;
            if (data.aprende_ia_used) {
                const aprendeMessage = buildAprendeResponse(data);
                if (aprendeMessage) {
                    botMessage = aprendeMessage;
                }
            }

            addMessage('bot', botMessage);

            // 1) Si backend manda tasks agrupadas, refrescar sidebar desde backend
            if (normalized.tasks) {
                try {
                    renderSidebarTasks(normalized.tasks);
                } catch (err) {
                    console.warn('No se pudo renderizar sidebar desde backend:', err);
                }
            }

            // 2) SOLO procesar task cuando sea cierre real (action === 'task')
            //    (evita guardar tareas incompletas y disparar ICS en followup)
            if (normalized.action === 'task' && normalized.task) {
                processTask(text, normalized);
            }

            fetchUsageStatus();

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

function buildAprendeResponse(data) {
    const candidates = Array.isArray(data?.candidates) ? data.candidates : [];
    if (!candidates.length) return null;

    const query = data?.query || '';
    const topCandidate = (Array.isArray(data?.top) && data.top[0]) ? data.top[0] : candidates[0];

    const uniqueById = new Map();
    const pushUnique = (item) => {
        if (!item) return;
        const key = item.courseId || item.metadata?.courseId || item.courseName;
        if (!uniqueById.has(key)) {
            uniqueById.set(key, item);
        }
    };

    pushUnique(topCandidate);
    candidates.forEach(pushUnique);

    const topFive = Array.from(uniqueById.values()).slice(0, 5);

    const sanitizeCell = (value) => {
        if (!value) return 'Curso disponible';
        return String(value).replace(/\|/g, ' / ').replace(/\n+/g, ' ').trim();
    };

    const getCourseUrl = (item) => {
        return (
            item?.resourceRedirection ||
            item?.metadata?.resourceRedirection ||
            item?.url ||
            item?.metadata?.url ||
            item?.resourceUrl ||
            item?.metadata?.resourceUrl ||
            (item?.courseId ? `https://aprende.org/cursos/${item.courseId}` : 'https://aprende.org')
        );
    };

    let message = `🎓 Encontré ${topFive.length} cursos relacionados con '${query}':\n\n`;
    message += `| Titulo del curso | Enlace  |\n`;
    message += `| --- | --- |\n`;

    topFive.forEach((course) => {
        const name = sanitizeCell(course?.courseName || course?.metadata?.courseName);
        const url = getCourseUrl(course);
        const linkLabel = 'Click para ver';
        message += `| ${name} | [${linkLabel}](${url}) |\n`;
    });

    return message.trim();
}

// ==================== API CALLS ====================
async function callAPI(message) {
    try {
        const conversationId = sessionStorage.getItem('claroAssistant_sessionId');

        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Conversation-Id': conversationId
            },
            body: JSON.stringify({
                message: message,
                action: appState.currentMode,
                macro_intent: detectMacroIntent(message),
                task_type: detectTaskType(message)
            })
        });

        if (response.status === 429) {
            const errorData = await response.json();
            throw new Error(errorData.message || '⏱️ Por favor espera unos segundos antes de enviar otro mensaje');
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            if (data.aprende_ia_used) {
                if (data.url_video) {
                    appState.lastAprendeResource = {
                        url: data.url_video,
                        tipo: 'video'
                    };
                    console.log('🎥 Video de Aprende.org detectado:', appState.lastAprendeResource);
                } else if (data.url_pdf) {
                    appState.lastAprendeResource = {
                        url: data.url_pdf,
                        tipo: 'pdf'
                    };
                    console.log('📄 PDF de Aprende.org detectado:', appState.lastAprendeResource);
                } else if (data.url_recurso) {
                    appState.lastAprendeResource = {
                        url: data.url_recurso,
                        tipo: data.tipo_recurso || 'curso'
                    };
                    console.log('📚 Página de Aprende.org detectada:', appState.lastAprendeResource);
                }
            } else {
                appState.lastAprendeResource = null;
            }

            if (data.action === 'telcel' && Array.isArray(data.relevant_urls)) {
                const telcelSearchUrl = data.relevant_urls.find(
                    url => typeof url === 'string' && url.includes('telcel.com/buscador?')
                );

                if (telcelSearchUrl) {
                    console.log('🔎 Telcel buscador detectado:', telcelSearchUrl);

                    if (!data.response.includes(telcelSearchUrl)) {
                        data.response += `\n\n🔗 **Consulta directa en Telcel:** ` +
                            `[Abrir buscador de Telcel](${telcelSearchUrl})`;
                    }
                }
            }

            return data;
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error en la llamada a la API:', error);
        return {
            success: false,
            response: 'Error al comunicarse con el servidor.'
        };
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
            saveConversation = () => null;
            loadConversations = () => [];
            loadConversationById = () => null;
            deleteConversation = () => { };
            clearConversations = () => { };
            resolve();
        });
    });
}

function showChatView() {
    elements.welcomePage.style.display = 'none';
    elements.chatPage.style.display = 'flex';

    const carousel = document.getElementById('suggestionsCarousel');
    if (carousel) {
        carousel.style.display = 'none';
    }
}

function addMessage(type, content) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container ' + type;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar ' + type;

    if (type === 'bot') {
        avatarDiv.innerHTML = '<img src="images/logo_claro.png" alt="Claro Assistant">';
    } else {
        avatarDiv.innerHTML = '<span class="material-symbols-outlined">account_circle</span>';
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'msg ' + type;

    const formattedContent = formatMessage(content);
    messageDiv.innerHTML = formattedContent;

    contentDiv.appendChild(messageDiv);
    messageContainer.appendChild(avatarDiv);
    messageContainer.appendChild(contentDiv);

    if (type === 'bot' && appState.lastAprendeResource) {
        const { url, tipo } = appState.lastAprendeResource;

        console.log('📺 Creando visor para:', url, '- Tipo:', tipo);

        const renderZone = document.createElement('div');
        renderZone.className = 'aprende-render-zone';

        const mediaViewer = createMediaViewer(url, tipo);
        renderZone.appendChild(mediaViewer);
        contentDiv.appendChild(renderZone);

        appState.lastAprendeResource = null;
    }

    elements.chatHistory.appendChild(messageContainer);

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
                    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => buildMessageLinkHtml(label, url));

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
    html = html.replace(/(?![^<]*<\/table>)\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => buildMessageLinkHtml(label, url));
    html = html.replace(/(?![^<]*<\/table>)(?<!href="|">)(https?:\/\/[^\s<>"]+)(?![^<]*<\/a>)/g, function (match) {
        return buildMessageLinkHtml(match, match);
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

        applyMediaProtection(video);

    } else if (type === 'pdf') {
        const iframe = document.createElement('iframe');
        iframe.src = url + '#toolbar=0&navpanes=0&scrollbar=0';
        iframe.setAttribute('sandbox', 'allow-same-origin');

        contentDiv.appendChild(iframe);

    } else if (type === 'image') {
        const img = document.createElement('img');
        img.src = url;
        img.alt = 'Contenido de Aprende.org';

        img.addEventListener('contextmenu', (e) => e.preventDefault());
        img.addEventListener('dragstart', (e) => e.preventDefault());

        contentDiv.appendChild(img);
    } else if (type === 'curso' || type === 'diplomado' || type === 'ruta' || type === 'especialidad') {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.className = 'aprende-iframe';
        iframe.style.width = '100%';
        iframe.style.height = '600px';
        iframe.style.border = 'none';
        iframe.style.borderRadius = '8px';
        iframe.setAttribute('allowfullscreen', 'true');
        iframe.setAttribute('loading', 'lazy');

        console.log('✅ Iframe de curso creado:', url);

        contentDiv.appendChild(iframe);
    } else if (type === 'webpage') {
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
    } else {
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

// ==================== NOTAS: COPIAR / COMPARTIR ====================
async function copyNoteToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        console.log('📝 Nota copiada al portapapeles');
        showSuccessMessage('📝 Nota copiada. Puedes pegarla en tu app de notas.');
    } catch (err) {
        console.error('❌ Error copiando nota:', err);
        showErrorMessage('No se pudo copiar la nota');
    }
}

async function shareNoteIfAvailable(text) {
    if (!navigator.share) {
        console.log('ℹ️ Web Share API no disponible');
        await copyNoteToClipboard(text);
        return;
    }

    try {
        await navigator.share({
            title: 'Nota de Claria',
            text
        });
        console.log('📤 Nota compartida');
    } catch (err) {
        console.log('ℹ️ Share cancelado o no disponible, copiando nota');
        await copyNoteToClipboard(text);
    }
}

function applyMediaProtection(mediaElement) {
    if (!mediaElement) return;

    mediaElement.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });

    mediaElement.addEventListener('dragstart', (e) => {
        e.preventDefault();
        return false;
    });

    mediaElement.style.userSelect = 'none';
    mediaElement.style.webkitUserSelect = 'none';

    document.addEventListener('keydown', (e) => {
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


function bindDeleteButtons() {
    document.querySelectorAll('.task-preview-btn.delete').forEach(btn => {
        if (btn.__deleteBound) return; // evita duplicados
        btn.__deleteBound = true;

        btn.addEventListener('click', () => {
            const taskId = btn.dataset.taskId;
            console.log('🖱️ Click eliminar tarea:', taskId);
            deleteTask(taskId); // 👉 llama al backend
        });
    });
}


function extractPreviewContent(fullContent, taskType) {
    let content = fullContent || '';

    const cleanContent = content
        .replace(/^(anota|apunta|nota|escribe)\s*/i, '')
        .replace(/^(recuerdame|recuérdame|recordatorio|recordar)\s*/i, '')
        .replace(/^(agenda|agendar|evento|cita|reunión|reunion)\s*/i, '')
        .replace(/^(que|qué|para|sobre|acerca de)\s*/i, '')
        .trim();

    if (taskType === 'calendar' || taskType === 'reminder') {
        let preview = cleanContent;

        preview = preview
            .replace(/\b(manana|hoy|el lunes|el martes|el miercoles|el jueves|el viernes|el sabado|el domingo)\b/i, '')
            .replace(/\b(a las|a la|en|para)\b/gi, '')
            .replace(/\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)?)\b/gi, '')
            .replace(/\s{2,}/g, ' ')
            .trim();

        if (preview.length > 40) {
            preview = preview.substring(0, 37) + '...';
        }

        return preview || 'Evento sin titulo';
    }

    if (cleanContent.length > 50) {
        return cleanContent.substring(0, 47) + '...';
    }

    return cleanContent || 'Nota sin contenido';
}
function showICSInfoAlert(task) {
    if (!task?.raw?.ics) return;

    console.log('📣 Mostrando alerta informativa ICS', {
        taskId: task.id,
        type: task.type
    });

    showAlert({
        icon: 'calendar_month',
        title: 'Evento creado',
        message: 'Puedes importar este evento en tu app de calendario favorita (Google Calendar, Outlook, Apple Calendar).',
        actionText: 'Descargar archivo',
        onAction: () => {
            console.log('🖱️ Click desde alerta → descargar ICS');
            downloadICS(task.raw.ics, task.content || 'evento');
        }
    });
}


// ==================== RENDERIZADO COMPLETO DEL SIDEBAR ====================
function renderTaskSidebar() {
    try {
        console.log('🔄 Renderizando sidebar de tareas...', { total: taskStore.length });
        
        // Filtrar tareas por tipo
        const notes = taskStore.filter(t => t.type === 'note');
        const reminders = taskStore.filter(t => t.type === 'reminder');
        const calendar = taskStore.filter(t => t.type === 'calendar');
        
        console.log('📊 Distribución de tareas:', {
            notes: notes.length,
            reminders: reminders.length,
            calendar: calendar.length
        });
        
        // Renderizar cada categoría
        renderTaskPreview('notes', notes);
        renderTaskPreview('reminders', reminders);
        renderTaskPreview('calendar', calendar);
        
        // Actualizar contadores
        updateSidebarCounters();
        
        // Actualizar visibilidad según estado de contracción
        updateTasksVisibility();
        
        console.log('✅ Sidebar renderizado correctamente');
        // Bind download handlers for ICS buttons rendered in the sidebar
        try {
            bindICSDownloadButtons();
        } catch (e) {
            console.warn('⚠️ bindICSDownloadButtons fallo:', e);
        }
        try {
            setupTaskPreviewDelegation();
        } catch (e) {
            console.warn('⚠️ setupTaskPreviewDelegation fallo:', e);
        }
    } catch (error) {
        console.error('❌ Error en renderTaskSidebar:', error);
    }
}

// Asociar handlers a botones de descarga ICS del sidebar (sin inline JS)
function bindICSDownloadButtons() {
    document.querySelectorAll('.task-preview-btn.download').forEach(btn => {
        // Avoid binding multiple times
        if (btn.__icsBound) return;

        btn.addEventListener('click', () => {
            const taskId = btn.dataset.taskId;
            const task = taskStore.find(t => t.id === taskId);

            console.log('🖱️ Click descargar ICS (sidebar)', { taskId, hasICS: !!task?.raw?.ics });

            if (!task || !task.raw || !task.raw.ics) {
                console.warn('❌ No se encontró ICS para la tarea', taskId);
                showErrorMessage('No se encontró el archivo .ics para esta tarea.');
                return;
            }

            // Llamada centralizada a la función de descarga (gesto de usuario)
            downloadICS(task.raw.ics, task.content || 'evento');
        });

        btn.__icsBound = true;
    });
}

function isAprendeLink(url) {
    return typeof url === 'string' && url.toLowerCase().includes('aprende.org');
}

function escapeHtmlAttribute(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function buildMessageLinkHtml(label, url) {
    const safeUrl = escapeHtmlAttribute(url);
    const safeLabel = label;
    const aprendeLink = isAprendeLink(url);
    const baseClass = aprendeLink ? 'msg-link aprende-link' : 'msg-link';
    const targetAttr = aprendeLink ? '' : ' target="_blank" rel="noopener"';
    const dataAttr = aprendeLink ? ` data-aprende-url="${safeUrl}"` : '';

    return `<a href="${safeUrl}"${targetAttr} class="${baseClass}"${dataAttr}>${safeLabel}</a>`;
}

function buildAprendeActions(url) {
    const actions = document.createElement('div');
    actions.className = 'media-actions aprende-actions';
    actions.innerHTML = `
        <a class="media-action-btn" href="${escapeHtmlAttribute(url)}" target="_blank" rel="noopener">
            Abrir en plataforma
        </a>
    `;
    return actions;
}

function renderAprendeInlineViewer(linkElement, url) {
    if (!linkElement) return;

    const messageContent = linkElement.closest('.message-content');
    if (!messageContent) return;

    let renderZone = messageContent.querySelector('.aprende-render-zone');
    let existingViewer = messageContent.querySelector('.message-media-viewer');

    if (!renderZone) {
        renderZone = document.createElement('div');
        renderZone.className = 'aprende-render-zone';

        if (existingViewer && existingViewer.parentElement) {
            existingViewer.parentElement.insertBefore(renderZone, existingViewer);
            renderZone.appendChild(existingViewer);
        } else {
            messageContent.appendChild(renderZone);
        }
    }

    let viewer = renderZone.querySelector('.message-media-viewer');
    if (!viewer) {
        viewer = createMediaViewer(url, 'curso');
        renderZone.appendChild(viewer);
    }

    viewer.classList.add('aprende-inline-viewer');

    const iframe = viewer.querySelector('iframe');
    if (iframe) {
        iframe.src = url;
    }

    let actions = renderZone.querySelector('.media-actions.aprende-actions');
    if (!actions) {
        actions = buildAprendeActions(url);
        renderZone.appendChild(actions);
    } else {
        const link = actions.querySelector('.media-action-btn');
        if (link) {
            link.href = url;
        }
    }
}

function handleAprendeLinkClick(e) {
    const link = e.target.closest('a.aprende-link');
    if (!link) return;

    const url = link.getAttribute('data-aprende-url') || link.getAttribute('href');
    if (!url) return;

    e.preventDefault();

    renderAprendeInlineViewer(link, url);
}

// ==================== MODAL DETALLE TAREA (SIDEBAR) ====================
let taskPreviewDelegationSetup = false;

function setupTaskPreviewDelegation() {
    if (taskPreviewDelegationSetup) return;

    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;

    sidebar.addEventListener('click', (e) => {
        const previewItem = e.target.closest('.task-preview-item');
        if (previewItem && !e.target.closest('.task-preview-btn')) {
            const taskId = previewItem.dataset.taskId;
            const task = taskStore.find(t => t.id === taskId);
            if (task) {
                showTaskDetailsModal(task);
            }
            return;
        }
    });

    taskPreviewDelegationSetup = true;
}

function showTaskDetailsModal(task) {
    const existing = document.querySelector('.event-modal-overlay');
    if (existing) {
        existing.remove();
    }

    const isNote = task.type === 'note';
    const rawTitle =
        (task.raw && (task.raw.title || task.raw.titulo || task.raw.summary || task.raw.event_title)) || '';
    const titleSource = isNote
        ? (rawTitle || task.content || 'Detalle')
        : (extractPreviewContent(task.content || '', task.type) || task.content || 'Detalle');
    const title = escapeHtml(titleSource);
    const fecha = escapeHtml(task.fecha || '');
    const hora = escapeHtml(task.hora || '');
    const location = escapeHtml(task.location || '');
    const meetingType = escapeHtml(task.meeting_type || '');
    const meetingLink = escapeHtml(task.meeting_link || task.raw?.meeting_link || '');
    const rawName = task.raw?.ics_filename || task.content || 'evento';
    const safeName = rawName.replace(/\.ics$/i, '');

    const dateLine = [fecha, hora].filter(Boolean).join(' ');
    const hasIcs = !!task.raw?.ics;
    const noteContent = escapeHtml(task.content || '');
    const headerIcon = isNote ? 'note' : 'event';
    const headerLabel = isNote ? 'Nota' : 'Evento';

    const modalHtml = `
        <div class="event-modal-overlay active" id="eventModalOverlay">
            <div class="event-modal">
                <div class="event-modal-header">
                    <div class="event-modal-title">
                        <span class="material-symbols-outlined">${headerIcon}</span>
                        <span>${headerLabel}: ${title}</span>
                    </div>
                    <button class="event-modal-close" id="eventModalClose" aria-label="Cerrar">
                        <span class="material-symbols-outlined">close</span>
                    </button>
                </div>
                <div class="event-modal-body">
                    ${isNote ? `<div class="event-modal-row full"><span class="label">Contenido</span><span class="value">${noteContent}</span></div>` : ''}
                    ${!isNote && dateLine ? `<div class="event-modal-row"><span class="label">Fecha y hora</span><span class="value">${dateLine}</span></div>` : ''}
                    ${!isNote && location ? `<div class="event-modal-row"><span class="label">Ubicación</span><span class="value">${location}</span></div>` : ''}
                    ${!isNote && meetingType ? `<div class="event-modal-row"><span class="label">Tipo</span><span class="value">${meetingType}</span></div>` : ''}
                    ${!isNote && meetingLink ? `<div class="event-modal-row"><span class="label">Liga</span><span class="value"><a class="event-modal-link" href="${meetingLink}" target="_blank" rel="noopener noreferrer">${meetingLink}</a></span></div>` : ''}
                </div>
                <div class="event-modal-actions">
                    ${!isNote && hasIcs ? `<button class="event-modal-btn primary" id="eventModalDownload">Descargar ICS</button>` : ''}
                    <button class="event-modal-btn secondary" id="eventModalCloseBtn">Cerrar</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    const overlay = document.getElementById('eventModalOverlay');
    const closeBtn = document.getElementById('eventModalClose');
    const closeBtnFooter = document.getElementById('eventModalCloseBtn');
    const downloadBtn = document.getElementById('eventModalDownload');

    const close = () => overlay?.remove();

    closeBtn?.addEventListener('click', close);
    closeBtnFooter?.addEventListener('click', close);
    overlay?.addEventListener('click', (ev) => {
        if (ev.target === overlay) close();
    });

    if (downloadBtn && hasIcs) {
        downloadBtn.addEventListener('click', () => {
            downloadICS(task.raw.ics, safeName);
        });
    }
}

// ==================== RENDERIZADO DE PREVIEWS CON ESTILO ====================
function renderTaskPreview(listType, tasks) {
    try {
        const preview = document.getElementById(`${listType}-preview`);
        const navItem = document.getElementById(`nav-${listType}`);
        
        if (!preview) {
            console.error(`❌ Elemento preview no encontrado: ${listType}-preview`);
            return;
        }
        
        const emptyMessages = {
            'notes': 'Sin notas',
            'reminders': 'Sin recordatorios',
            'calendar': 'Sin eventos'
        };
        
        // Si no hay tareas
        if (!tasks || tasks.length === 0) {
            console.log(`ℹ️ No hay tareas para: ${listType}`);
            preview.innerHTML = `<div class="task-preview-empty">${emptyMessages[listType]}</div>`;
            if (navItem) {
                navItem.classList.remove('has-tasks');
                const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
                if (toggleIcon) {
                    toggleIcon.textContent = 'chevron_right';
                }
            }
            return;
        }
        
        console.log(`📝 Renderizando ${tasks.length} tareas para: ${listType}`);
        
        // Marcar que tiene tareas
        if (navItem) {
            navItem.classList.add('has-tasks');
            const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
            if (toggleIcon) {
                toggleIcon.textContent = 'expand_more';
            }
        }
        
        let html = '';
        
        // Mostrar hasta 3 tareas en preview (máximo)
        const previewTasks = tasks.slice(0, 3);
        
        previewTasks.forEach((task, index) => {
            try {
            const rawTitle =
                task?.raw?.title ||
                task?.raw?.titulo ||
                task?.raw?.summary ||
                task?.raw?.event_title ||
                '';

            const inferredText = (task.type === 'calendar' || task.type === 'reminder')
                ? extractPreviewContent(task.content || '', task.type)
                : (task.preview || extractPreviewContent(task.content || '', task.type) || task.content || '');

            let displayText = (inferredText || '').trim();
            if (!displayText || displayText.toLowerCase() === 'evento sin titulo') {
                displayText = (rawTitle || '').trim() || (task.content || '').trim() || 'Evento sin titulo';
            }

            if (task.type === 'note' && !displayText) {
                displayText = 'Nota sin contenido';
            }
                const escapedText = escapeHtml(displayText);
                const escapedContent = escapeHtml(task.content || '');
                
                // Extraer fecha y hora si existen
                let datetimeHtml = '';
                if (task.fecha || task.hora) {
                    const fecha = task.fecha || '';
                    const hora = task.hora || '';
                    const separator = (fecha && hora) ? ' ' : '';
                    datetimeHtml = `
                        <div class="task-preview-time">
                            <small>${fecha}${separator}${hora}</small>
                        </div>
                    `;
                }
                
                // Determinar tipo de reunión si existe
                let meetingTypeHtml = '';
                if (task.meeting_type) {
                    const typeClass = task.meeting_type === 'virtual' ? 'virtual' : 'presencial';
                    const typeText = task.meeting_type === 'virtual' ? 'Virtual' : 'Presencial';
                    meetingTypeHtml = `
                        <div class="task-preview-badge ${typeClass}">
                            ${typeText}
                        </div>
                    `;
                }
                
                // Botones de acción
                let actionButtons = '';
                
                // Botón para copiar notas
                if (task.type === 'note') {
                    actionButtons += `
                        <button class="task-preview-btn copy" onclick="copyNoteToClipboard('${escapedContent.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')" title="Copiar nota">
                            <span class="material-symbols-outlined">content_copy</span>
                        </button>
                    `;
                }
                
                // Botón para descargar ICS (sin inline JS)
                if (task.raw && task.raw.ics) {
                    actionButtons += `
                        <button
                            class="task-preview-btn download"
                            data-task-id="${task.id}"
                            title="Descargar evento">
                            <span class="material-symbols-outlined">calendar_month</span>
                        </button>
                    `;
                }
                
                // Botón para eliminar (siempre presente)
                            actionButtons += `
            
                <button class="task-preview-btn delete"
                        data-task-id="${task.id}"
                        title="Eliminar">
                    <span class="material-symbols-outlined">close</span>
                </button>
            `;

                
                // Badge para tareas pendientes
                let pendingBadge = '';
                if (task.status === 'pending') {
                    pendingBadge = '<div class="task-pending-badge">Pendiente</div>';
                }
                
                html += `
<div class="task-preview-item" data-task-id="${task.id}">
    <div class="task-preview-content">${escapedText}</div>
    ${datetimeHtml}
    ${meetingTypeHtml}
    ${pendingBadge}
    <div class="task-preview-actions">
        ${actionButtons}
    </div>
</div>
                `;
                
            } catch (taskError) {
                console.error(`❌ Error renderizando tarea ${index}:`, taskError);
            }
        });
        
        // Si hay más de 3 tareas, mostrar indicador
        if (tasks.length > 3) {
            html += `<div class="task-preview-more" onclick="expandAllTasks('${listType}')">+${tasks.length - 3} más</div>`;
        }
        
        preview.innerHTML = html;
        
        // Aplicar estilos dinámicos si es necesario
        applyTaskPreviewStyles(preview, listType);
        
    } catch (error) {
        console.error(`❌ Error en renderTaskPreview para ${listType}:`, error);
        const preview = document.getElementById(`${listType}-preview`);
        if (preview) {
            preview.innerHTML = `<div class="task-preview-empty error">Error al cargar tareas</div>`;
        }
    }
}
async function deleteTask(taskId) {
    console.log('🗑️ Eliminando tarea:', taskId);

    try {
        const res = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE',
            headers: {
                'X-User-Key': userKey   // 🔑 usa el mismo userKey del chat
            }
        });

        const data = await res.json();

        if (!data.success) {
            console.warn('❌ Error eliminando tarea', data);
            return;
        }

        console.log('✅ Tarea eliminada, actualizando sidebar');

        // 🔁 Reemplazar fuente de verdad
        taskStore = [];
        hydrateTaskStoreFromBackend(data.tasks);

        renderTaskSidebar();
        updateSidebarCounters();
        bindDeleteButtons();


    } catch (err) {
        console.error('❌ Error en deleteTask()', err);
    }
}
function hydrateTaskStoreFromBackend(tasks) {
    if (!tasks) return;

    const { calendar = [], reminder = [], note = [] } = tasks;

    calendar.forEach(t => taskStore.push({ ...t, type: 'calendar', raw: t }));
    reminder.forEach(t => taskStore.push({ ...t, type: 'reminder', raw: t }));
    note.forEach(t => taskStore.push({ ...t, type: 'note', raw: t }));
}

// ==================== FUNCIONES AUXILIARES ====================
function expandAllTasks(listType) {
    const navItem = document.getElementById(`nav-${listType}`);
    const preview = document.getElementById(`${listType}-preview`);
    
    if (navItem && preview) {
        preview.classList.add('expanded');
        const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
        if (toggleIcon) {
            toggleIcon.textContent = 'expand_less';
        }
        
        // Si hay más de 3 tareas, cargar todas
        const tasks = taskStore.filter(t => t.type === listType.replace('s', ''));
        if (tasks.length > 3) {
            renderFullTaskList(listType, tasks);
        }
    }
}

function renderFullTaskList(listType, tasks) {
    const preview = document.getElementById(`${listType}-preview`);
    if (!preview) return;
    
    // Similar a renderTaskPreview pero muestra todas las tareas
    let html = '';
    
    tasks.forEach(task => {
        const displayText = task.preview || extractPreviewContent(task.content || '', task.type) || task.content || 'Sin título';
        const escapedText = escapeHtml(displayText);
        const escapedContent = escapeHtml(task.content || '');
        
        // ... código similar para construir cada tarea ...
        // (puedes reutilizar la lógica de renderTaskPreview)
    });
    
    preview.innerHTML = html;
}

function applyTaskPreviewStyles(previewElement, listType) {
    // Aplicar colores según el tipo de tarea
    const colorMap = {
        'notes': '#00BCD4',
        'reminders': '#FF9800',
        'calendar': '#4CAF50'
    };
    
    const color = colorMap[listType] || '#00BCD4';
    
    // Aplicar borde izquierdo con color específico
    previewElement.querySelectorAll('.task-preview-item').forEach(item => {
        item.style.borderLeftColor = color;
    });
}

function updateSidebarCounters() {
    try {
        const noteCount = taskStore.filter(t => t.type === 'note').length;
        const reminderCount = taskStore.filter(t => t.type === 'reminder').length;
        const calendarCount = taskStore.filter(t => t.type === 'calendar').length;
        const totalTasks = noteCount + reminderCount + calendarCount;
        
        console.log('🔢 Actualizando contadores:', { noteCount, reminderCount, calendarCount, totalTasks });
        
        // Actualizar contadores individuales
        const noteCounter = document.querySelector('#noteCount');
        const reminderCounter = document.querySelector('#reminderCount');
        const calendarCounter = document.querySelector('#calendarCount');
        
        if (noteCounter) {
            noteCounter.textContent = noteCount > 0 ? `(${noteCount})` : '';
            noteCounter.style.color = noteCount > 0 ? '#DA291C' : '#999';
        }
        
        if (reminderCounter) {
            reminderCounter.textContent = reminderCount > 0 ? `(${reminderCount})` : '';
            reminderCounter.style.color = reminderCount > 0 ? '#DA291C' : '#999';
        }
        
        if (calendarCounter) {
            calendarCounter.textContent = calendarCount > 0 ? `(${calendarCount})` : '';
            calendarCounter.style.color = calendarCount > 0 ? '#DA291C' : '#999';
        }
        
        // Actualizar contador total en el header
        const tasksHeader = document.querySelector('.tasks-section-header');
        if (tasksHeader) {
            // Eliminar contador anterior si existe
            const existingTotal = tasksHeader.querySelector('.tasks-total-count');
            if (existingTotal) existingTotal.remove();
            
            // Agregar nuevo contador si hay tareas
            if (totalTasks > 0) {
                const totalSpan = document.createElement('span');
                totalSpan.className = 'tasks-total-count';
                totalSpan.textContent = totalTasks;
                totalSpan.style.cssText = `
                    background: #DA291C;
                    color: white;
                    font-size: 11px;
                    padding: 2px 6px;
                    border-radius: 10px;
                    margin-left: 8px;
                    font-weight: 600;
                    animation: pulse 2s infinite;
                `;
                
                const titleText = tasksHeader.querySelector('.title-text');
                if (titleText) {
                    titleText.appendChild(totalSpan);
                }
                
                // Marcar que tiene tareas
                tasksHeader.classList.add('has-tasks');
            } else {
                tasksHeader.classList.remove('has-tasks');
            }
        }
        
    } catch (error) {
        console.error('❌ Error en updateSidebarCounters:', error);
    }
}

function updateTasksVisibility() {
    const tasksContent = document.getElementById('taskSectionContent');
    if (!tasksContent) return;

    const isCollapsed = tasksContent.classList.contains('collapsed');

    // Mostrar/ocultar elementos dentro de la sección de tareas
    const elementsToToggle = [
        ...tasksContent.querySelectorAll('.nav-item'),
        ...tasksContent.querySelectorAll('.task-preview-list')
    ];

    elementsToToggle.forEach(el => {
        if (isCollapsed) {
            el.style.display = 'none';
            el.style.opacity = '0';
            el.style.height = '0';
            el.style.overflow = 'hidden';
        } else {
            el.style.display = '';
            setTimeout(() => {
                el.style.opacity = '1';
                el.style.height = '';
                el.style.overflow = '';
            }, 10);
        }
    });
}

// ==================== FUNCIÓN PARA ESCAPAR HTML ====================
function escapeHtml(text) {
    if (!text) return '';
    
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML
        .replace(/'/g, "&#39;")
        .replace(/"/g, "&quot;")
        .replace(/\n/g, '<br>');
}

// ==================== FUNCIONES PARA CONTRACCIÓN/EXPANSIÓN DE TAREAS ====================
function setupTasksSectionToggle() {
    const header = document.getElementById('taskSectionHeader');
    const content = document.getElementById('taskSectionContent');

    if (!header || !content) return;

    // Icono dentro del header
    const headerToggleIcon = header.querySelector('.nav-toggle .material-symbols-outlined');

    // Estado inicial: si hay preferencia en localStorage úsala, si no, colapsada por defecto
    const storedPref = localStorage.getItem('claria_tasks_collapsed');
    const isCollapsed = storedPref !== null ? storedPref === 'true' : true;

    header.classList.toggle('expanded', !isCollapsed);
    content.classList.toggle('collapsed', isCollapsed);

    // Sincronizar icono
    if (headerToggleIcon) {
        headerToggleIcon.textContent = content.classList.contains('collapsed') ? 'chevron_right' : 'expand_less';
    }

    // Aplicar visibilidad inicial y atributos ARIA
    header.setAttribute('role', 'button');
    header.setAttribute('aria-expanded', String(!content.classList.contains('collapsed')));
    updateTasksVisibility();

    // Toggle al hacer clic en el header
    header.addEventListener('click', function(e) {
        e.stopPropagation();

        const nowCollapsed = content.classList.toggle('collapsed');
        header.classList.toggle('expanded', !nowCollapsed);

        if (headerToggleIcon) {
            headerToggleIcon.textContent = nowCollapsed ? 'chevron_right' : 'expand_less';
        }

        header.setAttribute('aria-expanded', String(!nowCollapsed));
        localStorage.setItem('claria_tasks_collapsed', nowCollapsed ? 'true' : 'false');
        updateTasksVisibility();
    });

    // Configurar toggles individuales para recordatorios, notas y agenda
    ['reminders', 'notes', 'calendar'].forEach(listType => {
        const navItem = document.getElementById(`nav-${listType}`);
        const preview = document.getElementById(`${listType}-preview`);

        if (!navItem || !preview) return;

        // estado inicial
        preview.classList.remove('active');

        navItem.addEventListener('click', function(e) {
            // Evitar toggle si se clickeó un botón de acción dentro del nav
            if (e.target.closest('.task-preview-btn')) return;

            preview.classList.toggle('active');
            const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
            if (toggleIcon) {
                toggleIcon.textContent = preview.classList.contains('active') ? 'expand_less' : 'chevron_right';
            }
        });
    });
}

// ==================== TOGGLE DE CATEGORÍAS INDIVIDUALES ====================
function setupCategoryToggles() {
    document.querySelectorAll('.task-nav-item').forEach(navItem => {
        navItem.addEventListener('click', function(e) {
            // Solo toggle si no estamos en un botón de acción
            if (e.target.closest('.task-preview-btn')) return;
            
            const listType = this.id.replace('nav-', '');
            const preview = document.getElementById(`${listType}-preview`);
            const toggleIcon = this.querySelector('.nav-toggle .material-symbols-outlined');
            
            if (preview && toggleIcon) {
                preview.classList.toggle('expanded');
                toggleIcon.textContent = preview.classList.contains('expanded') 
                    ? 'expand_less' 
                    : 'expand_more';
            }
        });
    });
}

window.deleteTaskFromStore = function(taskId) {
    if (confirm('¿Eliminar esta tarea?')) {
        taskStore = taskStore.filter(t => t.id !== taskId);
        renderTaskSidebar();
        saveToLocalStorage();
        console.log('🗑️ Tarea eliminada:', taskId);
        
        // Mostrar notificación
        showSuccessMessage('Tarea eliminada');
    }
};

function showSuccessMessage(message) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10001;
        font-size: 14px;
        animation: slideInRight 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function showErrorMessage(message) {
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #dc3545;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10001;
        font-size: 14px;
        animation: slideInRight 0.3s ease;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ✅ FUNCIÓN MEJORADA PARA DESCARGAR ICS CON MEJOR UX
function downloadICS(icsContent, filename = 'evento') {
    console.log('⬇️ downloadICS ejecutado');

    if (!icsContent) {
        console.warn('❌ downloadICS: contenido vacío');
        return;
    }

    const blob = new Blob([icsContent], {
        type: 'text/calendar;charset=utf-8'
    });

    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.ics`;

    document.body.appendChild(a);
    a.click();

    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    console.log('✅ Descarga ICS disparada');
}

// ✅ NOTIFICACIÓN DE DESCARGA MEJORADA
function showICSDownloadToast(eventName, blobUrl, filename, downloadElement) {
    const toast = document.createElement('div');
    toast.className = 'ics-download-toast';
    toast.innerHTML = `
        <div style="display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:24px;">📅</span>
                <div style="flex:1;">
                    <div style="font-weight:bold; font-size:14px;">Evento de Calendario Listo</div>
                    <div style="font-size:12px; opacity:0.9;">"${eventName.substring(0, 40)}${eventName.length > 40 ? '...' : ''}"</div>
                </div>
            </div>
            <div style="display:flex; gap:8px; margin-top:4px;">
                <button id="icsDownloadBtn" style="flex:1; background:#DA291C; color:white; border:none; padding:8px 16px; border-radius:8px; font-weight:bold; cursor:pointer; font-size:13px;">
                    📥 Descargar .ICS
                </button>
                <button id="icsCancelBtn" style="background:#f5f5f5; color:#666; border:1px solid #ddd; padding:8px 12px; border-radius:8px; cursor:pointer; font-size:13px;">
                    Cancelar
                </button>
            </div>
            <div style="font-size:11px; color:#666; margin-top:4px; padding-top:4px; border-top:1px solid #eee;">
                <strong>💡 Tip:</strong> El archivo .ics se puede importar en Google Calendar, Outlook o Apple Calendar
            </div>
        </div>
    `;
    
    toast.style.cssText = `
        position: fixed; bottom: 20px; right: 20px;
        background: white; padding: 16px; border-radius: 12px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3); z-index: 10000;
        animation: slideInRight 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        min-width: 300px; max-width: 90%; border-left: 4px solid #DA291C;
    `;
    
    document.body.appendChild(toast);
    
    // Event listeners para los botones
    document.getElementById('icsDownloadBtn').addEventListener('click', () => {
        downloadElement.click();
        setTimeout(() => {
            document.body.removeChild(downloadElement);
            URL.revokeObjectURL(blobUrl);
            toast.remove();
            showSuccessMessage('✅ Evento descargado. Ábrelo para agregarlo a tu calendario.');
        }, 100);
    });
    
    document.getElementById('icsCancelBtn').addEventListener('click', () => {
        document.body.removeChild(downloadElement);
        URL.revokeObjectURL(blobUrl);
        toast.remove();
    });
    
    // Auto-eliminar después de 15 segundos
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            toast.style.transition = 'all 0.5s ease';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                    document.body.removeChild(downloadElement);
                    URL.revokeObjectURL(blobUrl);
                }
            }, 500);
        }
    }, 15000);
}



function restoreChatHistory() {
    if (!elements.chatHistory || appState.conversationHistory.length === 0) return;

    elements.chatHistory.innerHTML = '';

    appState.conversationHistory.forEach(msg => {
        const type = msg.type || 'user';
        addMessageToUI(type, msg.content);
    });

    setTimeout(() => {
        elements.chatHistory.scrollTop = elements.chatHistory.scrollHeight;
    }, 100);
}

function addMessageToUI(type, content) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container ' + type;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar ' + type;

    if (type === 'bot') {
        avatarDiv.innerHTML = '<img src="images/logo_claro.png" alt="Claro Assistant">';
    } else {
        avatarDiv.innerHTML = '<span class="material-symbols-outlined">account_circle</span>';
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'msg ' + type;
    messageDiv.innerHTML = formatMessage(content);

    contentDiv.appendChild(messageDiv);
    messageContainer.appendChild(avatarDiv);
    messageContainer.appendChild(contentDiv);

    elements.chatHistory.appendChild(messageContainer);
}

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
        const persistedTasks = (taskStoreModule && taskStoreModule.length)
            ? taskStoreModule
            : taskStore;
        const data = {
            conversationHistory: appState.conversationHistory.slice(-50),
            taskStore: persistedTasks,
            currentMode: appState.currentMode,
            sessionId: sessionStorage.getItem('claroAssistant_sessionId'),
            messageCount: userState.messageCount,
            isPro: userState.isPro,
            lastUpdated: new Date().toISOString()
        };

        localStorage.setItem('claroAssistant_state', JSON.stringify(data));
        console.log('💾 Estado guardado en localStorage');
    } catch (e) {
        console.error('❌ Error guardando en localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        let currentSessionId = sessionStorage.getItem('claroAssistant_sessionId');

        if (!currentSessionId) {
            currentSessionId = generateNewConversationId();
            sessionStorage.setItem('claroAssistant_sessionId', currentSessionId);
            console.log('🆕 Nueva sesión iniciada:', currentSessionId);
            return;
        }

        const saved = localStorage.getItem('claroAssistant_state');
        if (saved) {
            const data = JSON.parse(saved);
            const savedTasks = data.taskStore || data.tasks || [];
            if (savedTasks.length) {
                taskStore = savedTasks;
                setTaskStore(savedTasks);
            }

            if (data.sessionId === currentSessionId) {
                appState.conversationHistory = data.conversationHistory || [];

                appState.currentMode = data.currentMode || 'descubre';
                userState.messageCount = data.messageCount || 0;
                userState.isPro = data.isPro || false;

                console.log('📂 Estado cargado desde localStorage:', {
                    messages: appState.conversationHistory.length,
                    tasks: taskStore.length,
                    mode: appState.currentMode
                });

                if (appState.conversationHistory.length > 0) {
                    showChatView();
                    restoreChatHistory();
                }

                renderTaskSidebar();

            } else {
                console.log('📱 Nueva pestaña - estado limpio');
                sessionStorage.setItem('claroAssistant_sessionId', currentSessionId);
                if (savedTasks.length) {
                    renderTaskSidebar();
                }
            }
        }
    } catch (e) {
        console.error('❌ Error cargando desde localStorage:', e);
        localStorage.removeItem('claroAssistant_state');
        taskStore = [];
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
let saveConversation, loadConversations, loadConversationById, deleteConversation, clearConversations;

(async function () {
    try {
        const module = await import('./chatStorage.js');
        saveConversation = module.saveConversation;
        loadConversations = module.loadConversations;
        loadConversationById = module.loadConversationById;
        deleteConversation = module.deleteConversation;
        clearConversations = module.clearConversations;
        console.log('✅ Módulo de almacenamiento de conversaciones cargado');
    } catch (e) {
        console.error('❌ Error cargando módulo de conversaciones:', e);

        saveConversation = (messages, title) => {
            console.warn('Fallback: saveConversation llamado');
            return null;
        };
        loadConversations = () => [];
        loadConversationById = () => null;
        deleteConversation = () => { };
        clearConversations = () => { };
    }
})();

function updateConversationHistoryUI() {
    const historyList = document.getElementById('conversationHistoryList');
    if (!historyList) return;

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

function loadConversationFromHistory(conversationId) {
    if (typeof loadConversationById !== 'function') {
        console.error('❌ loadConversationById no está disponible');
        return;
    }

    const conversation = loadConversationById(conversationId);

    if (conversation) {
        saveCurrentConversation();

        const newSessionId = generateNewConversationId();

        appState.conversationHistory = conversation.messages || [];

        appState.isLoadedFromHistory = true;

        showChatView();
        elements.chatHistory.innerHTML = '';

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

function clearAllConversationHistory() {
    if (confirm('¿Eliminar todo el historial de conversaciones? Esta acción no se puede deshacer.')) {
        clearConversations();
        updateConversationHistoryUI();
        console.log('🗑️ Todo el historial fue eliminado');
    }
}

window.saveCurrentConversation = saveCurrentConversation;
window.loadConversationFromHistory = loadConversationFromHistory;
window.clearAllConversationHistory = clearAllConversationHistory;

// ==================== FUNCIONES PARA DESHABILITAR INPUT ====================
function showLimitWarning() {
    elements.userInput.value = '';
    elements.userInput.placeholder = '⚠️ Límite alcanzado - Hazte Pro';
    elements.userInput.readOnly = true;
    elements.userInput.style.cursor = 'pointer';
    elements.userInput.style.fontWeight = '500';
    elements.userInput.style.color = '#DA291C';
    elements.sendBtn.disabled = true;
    elements.sendBtn.style.opacity = '0.5';
    elements.sendBtn.style.cursor = 'not-allowed';

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

    elements.userInput.classList.remove('limit-reached');
}

function upgradeToPro() {
    closePremiumModal();
}

document.addEventListener('DOMContentLoaded', function () {
    const btnUpgradePro = document.getElementById('btnUpgradePro');
    const btnClosePremium = document.getElementById('btnClosePremium');
    const premiumOverlay = document.getElementById('premiumOverlay');

    if (btnUpgradePro) {
        btnUpgradePro.addEventListener('click', upgradeToPro);
    }

    if (btnClosePremium) {
        btnClosePremium.addEventListener('click', closePremiumModal);
    }

    if (premiumOverlay) {
        premiumOverlay.addEventListener('click', function (e) {
            if (e.target === premiumOverlay) {
                closePremiumModal();
            }
        });
    }
});

function showAutoWebSearchToast() {
    const toast = document.createElement('div');
    toast.className = 'auto-web-toast';
    toast.innerHTML = `
        <span>🌐</span>
        <div>
            <strong>Búsqueda web activada automáticamente</strong><br>
            <small>La pregunta requiere información actualizada</small>
        </div>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function detectMacroIntent(message) {
    const t = (message || '').toLowerCase();
    const taskKeywords = [
        'anota', 'apunta', 'nota',
        'recuerdame', 'recuérdame', 'recordatorio',
        'agenda', 'agendar', 'evento', 'cita', 'reunión', 'junta'
    ];
    return taskKeywords.some(k => t.includes(k)) ? 'task' : 'chat';
}

function detectTaskType(message) {
    const t = (message || '').toLowerCase();
    if (t.includes('agenda') || t.includes('agendar') || t.includes('evento') || t.includes('cita')) {
        return 'calendar';
    }
    if (t.includes('recuerdame') || t.includes('recuérdame') || t.includes('recordatorio')) {
        return 'reminder';
    }
    return 'note';
}

window.addEventListener('resize', function () {
    if (window.innerWidth >= 900) {
        elements.sidebar.classList.remove('active');
        elements.overlay.classList.remove('active');
    }
});

window.copyNoteToClipboard = copyNoteToClipboard;
window.shareNoteIfAvailable = shareNoteIfAvailable;
window.downloadICS = downloadICS;

console.log('%c🚀 Claro·Assistant Initialized', 'color: #DA291C; font-size: 16px; font-weight: bold;');
console.log('%cAPI URL:', 'color: #00BCD4; font-weight: bold;', API_URL);
console.log('%cToken Limit:', 'color: #28a745; font-weight: bold;', TOKEN_CONFIG.MAX_TOKENS);
console.log('%cReady to chat!', 'color: #28a745;');
