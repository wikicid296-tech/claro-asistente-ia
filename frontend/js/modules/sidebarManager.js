// ==================== GESTOR DEL SIDEBAR ====================
import { appState } from './state.js';
import { MODE_PLACEHOLDERS } from './config.js';
import { saveCurrentConversation, resetChat } from './chatstate.js';

// ==================== TOGGLE SIDEBAR ====================
export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');

    if (sidebar && overlay) {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

// ==================== CERRAR SIDEBAR ====================
export function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');

    if (sidebar && overlay) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
    }
}

// ==================== SETUP TASK SECTION TOGGLE ====================
export function setupTasksSectionToggle() {
    const header = document.getElementById('taskSectionHeader');
    const content = document.getElementById('taskSectionContent');

    if (!header || !content) {
        console.warn('⚠️ No se encontró header o content de sección de tareas');
        return;
    }

    header.addEventListener('click', () => {
        const isCollapsed = content.classList.contains('collapsed');

        if (isCollapsed) {
            content.classList.remove('collapsed');
            header.classList.add('expanded');
            console.log('📂 Sección de tareas expandida');
        } else {
            content.classList.add('collapsed');
            header.classList.remove('expanded');
            console.log('📁 Sección de tareas colapsada');
        }
    });

    console.log('✅ Toggle de sección de tareas configurado (colapsada por defecto)');
}

// ==================== SETUP TASK PREVIEW TOGGLES ====================
export function setupTaskPreviewToggles() {
    const navItems = ['reminders', 'notes', 'calendar'];

    navItems.forEach(listType => {
        const navItem = document.getElementById(`nav-${listType}`);
        const preview = document.getElementById(`${listType}-preview`);

        if (navItem && preview) {
            navItem.addEventListener('click', function(e) {
                // Evitar toggle si se clickeó un botón de acción
                if (e.target.closest('.task-preview-btn')) return;

                preview.classList.toggle('active');

                const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
                if (toggleIcon) {
                    toggleIcon.textContent = preview.classList.contains('active')
                        ? 'expand_less'
                        : 'chevron_right';
                }
            });
        }
    });
}

// ==================== SET MODE ====================
export function setMode(mode, { source = 'manual' } = {}) {
    const userInput = document.getElementById('userInput');

    appState.currentMode = mode;
    appState.modeActivatedManually = source === 'manual';

    if (userInput) {
        userInput.placeholder = MODE_PLACEHOLDERS[mode] || MODE_PLACEHOLDERS.descubre;
    }

    if (mode === 'descubre') {
        hideModeChip();
    } else {
        showModeChip(mode);
    }

    // Actualizar nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle(
            'active',
            item.getAttribute('data-section') === mode
        );
    });

    // Actualizar action items
    document.querySelectorAll('.action-item').forEach(item => {
        item.classList.toggle(
            'selected',
            item.getAttribute('data-action') === mode
        );
    });

    console.log(`🔄 Modo activo: ${mode} (source: ${source})`);
}

// ==================== SHOW MODE CHIP ====================
function showModeChip(mode) {
    const modeChipContainer = document.getElementById('modeChipContainer');
    const modeChipText = document.getElementById('modeChipText');
    const modeChipIcon = document.getElementById('modeChipIcon');

    if (!modeChipContainer || !modeChipText) return;

    const modeNames = {
        'aprende': 'Aprende.org',
        'tareas': 'Gestión de tareas',
        'busqueda_web': 'Búsqueda web'
    };

    const icons = {
        'aprende': '<div class="mode-chip-icon-letter">A</div>',
        'tareas': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        'busqueda_web': '<svg class="mode-chip-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>'
    };

    modeChipText.textContent = modeNames[mode] || mode;

    if (modeChipIcon) {
        modeChipIcon.innerHTML = icons[mode] || icons['busqueda_web'];
    }

    modeChipContainer.style.display = 'flex';

    // Ocultar carousel de sugerencias
    const carousel = document.getElementById('suggestionsCarousel');
    if (carousel) {
        carousel.style.display = 'none';
    }
}

// ==================== HIDE MODE CHIP ====================
export function hideModeChip() {
    const modeChipContainer = document.getElementById('modeChipContainer');

    if (!modeChipContainer) return;

    modeChipContainer.style.display = 'none';

    if (appState.currentMode !== 'descubre') {
        setMode('descubre', { source: 'manual' });
    }
}

// ==================== NUEVA CONVERSACIÓN ====================
export function startNewConversation() {
    try {
        // Guardar conversación actual si tiene mensajes
        if (appState.conversationHistory.length > 0) {
            const conversationId = saveCurrentConversation();
            console.log('💾 Conversación guardada:', conversationId);

            // Actualizar lista de conversaciones en el sidebar
            if (window.renderConversationHistory) {
                window.renderConversationHistory();
            }
        }

        // Limpiar chat state
        resetChat();

        appState.conversationHistory = [];
        appState.isLoadedFromHistory = false;

        const newSessionId =
            'session_' +
            Date.now() +
            '_' +
            Math.random().toString(36).substr(2, 9);

        sessionStorage.setItem('claroAssistant_sessionId', newSessionId);
        console.log('🔑 Nueva conversationId generada:', newSessionId);

        const chatHistory = document.getElementById('chatHistory');
        if (chatHistory) {
            chatHistory.innerHTML = '';
        }

        const welcomePage = document.getElementById('welcomePage');
        const chatPage = document.getElementById('chatPage');

        if (welcomePage) {
            welcomePage.style.display = 'flex';
        }
        if (chatPage) {
            chatPage.style.display = 'none';
        }

        const carousel = document.getElementById('suggestionsCarousel');
        if (carousel) {
            carousel.style.display = 'block';
        }

        hideModeChip();

        const userInput = document.getElementById('userInput');
        if (userInput) {
            userInput.placeholder = 'Pregunta lo que quieras';
        }

        appState.currentMode = 'descubre';
        appState.modeActivatedManually = false;

        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));

        const newConversationBtn = document.getElementById('newConversationBtn');
        if (newConversationBtn) {
            newConversationBtn.classList.add('active');
        }

        if (window.innerWidth < 900) {
            closeSidebar();
        }

        console.log('🆕 Nueva conversación iniciada correctamente');

    } catch (error) {
        console.error('❌ Error en startNewConversation:', error);
    }
}
