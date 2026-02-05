// ==================== GESTOR DE TAREAS MEJORADO ====================
import { taskStore, addTask, removeTask, setTaskStore, appState } from './state.js';
import { API_URL } from './config.js';
import { showAlert, showSuccessMessage, showErrorMessage } from './uiHelpers.js';

export function normalizeTaskPayload(data) {
  const rootIcs = data?.ics || null;

  const nested = data?.task || null;           // { action, ics, task, tasks } o task plano
  const nestedIcs = nested?.ics || null;

  // task plano puede estar en data.task (cuando no hay wrapper) o en data.task.task (wrapper)
  const taskObj =
    (nested && nested.type) ? nested :
    (nested && nested.task) ? nested.task :
    (data?.task && data.task.type) ? data.task :
    null;

  const tasksGrouped =
    data?.tasks ||
    nested?.tasks ||
    null;

  const ics =
    rootIcs ||
    nestedIcs ||
    null;

  const taskType =
    data?.task_type ||
    taskObj?.type ||
    taskObj?.task_type ||
    null;

  return {
    action: data?.action,
    response: data?.response,
    context: data?.context,
    success: data?.success,
    taskType,
    task: taskObj,
    tasks: tasksGrouped,
    ics,      // { filename, ics_content } | null (o string si aún llega así)
    raw: data
  };
}

// ==================== PROCESAR TAREA ====================
// ==================== PROCESAR TAREA (NORMALIZED + FORENSIC LOGS) ====================
export function processTask(userMessage, data) {
    // --------------------------------------------------
    // 0) Entrada: logs de alto nivel
    // --------------------------------------------------
    console.log('🔍 processTask llamado:', {
        userMessage,
        action: data?.action,
        success: data?.success,
        hasTask: !!data?.task,
        hasRootICS: !!data?.ics,
        hasNestedICS: !!data?.task?.ics
    });

    // --------------------------------------------------
    // 1) Normalizar payload (root vs nested contract)
    // --------------------------------------------------
    const norm = normalizeTaskPayload(data);

    // Deducir "contract" para debug (A/B)
    const contract =
        data?.ics ? 'ROOT_CONTRACT' :
        data?.task?.ics ? 'NESTED_CONTRACT' :
        (data?.task?.task ? 'WRAPPED_NO_ICS' : 'UNKNOWN');

    // Deducir "ics source" real (para auditoría)
    const icsSource =
        data?.ics ? 'root.ics' :
        data?.task?.ics ? 'task.ics' :
        (norm?.task?.ics ? 'taskEntity.ics' : 'none');

    // Extraer ICS string + filename (unificado)
    let icsContent = null;
    let icsFilename = null;

    if (norm?.ics) {
        if (typeof norm.ics === 'string') {
            icsContent = norm.ics;
        } else if (typeof norm.ics === 'object') {
            icsContent = norm.ics.ics_content || norm.ics.icsContent || null;
            icsFilename = norm.ics.filename || null;
        }
    }

    // Fallback: si el ICS vive en la entidad task (algunos backends viejos)
    if (!icsContent && norm?.task?.ics) {
        if (typeof norm.task.ics === 'string') {
            icsContent = norm.task.ics;
        } else if (typeof norm.task.ics === 'object') {
            icsContent = norm.task.ics.ics_content || null;
            icsFilename = norm.task.ics.filename || icsFilename;
        }
    }

    // Logs forenses (keys y rutas)
    console.groupCollapsed('🧪 TASK NORMALIZATION DEBUG');
    console.log('contract:', contract);
    console.log('icsSource:', icsSource);
    console.log('norm.action:', norm?.action);
    console.log('norm.taskType:', norm?.taskType);
    console.log('norm.task keys:', norm?.task ? Object.keys(norm.task) : null);
    console.log('raw.data keys:', data ? Object.keys(data) : null);
    console.log('raw.task keys:', data?.task ? Object.keys(data.task) : null);
    console.log('hasICS:', !!icsContent, 'icsLen:', (icsContent || '').length);
    console.log('icsFilename(raw):', icsFilename);
    console.groupEnd();

    // --------------------------------------------------
    // 2) Validación: task resuelta
    // --------------------------------------------------
    const resolvedTask = norm?.task || null;
    if (!resolvedTask) {
        console.warn('⚠️ processTask: No hay task resolvible tras normalización', {
            contract,
            icsSource,
            action: norm?.action
        });
        return null;
    }

    // --------------------------------------------------
    // 3) Resolver taskType (con fallback heurístico)
    // --------------------------------------------------
    let taskType = norm?.taskType || resolvedTask.task_type || resolvedTask.type || null;

    if (!taskType) {
        const content = (resolvedTask.content || userMessage || '').toLowerCase();
        if (content.includes('recuerdame') || content.includes('recuérdame')) {
            taskType = 'reminder';
        } else if (
            content.includes('agenda') ||
            content.includes('reunión') ||
            content.includes('reunion') ||
            content.includes('evento') ||
            content.includes('cita')
        ) {
            taskType = 'calendar';
        } else {
            taskType = 'note';
        }

        console.log('🧠 taskType inferido por heurística:', taskType);
    }

    // --------------------------------------------------
    // 4) Construir preview y objeto task para store
    // --------------------------------------------------
    const previewContent = extractPreviewContent(
        resolvedTask.content || userMessage,
        taskType
    );

    // Preferir ID real del backend si existe (importante para DELETE /tasks/<id>)
    const backendId = resolvedTask.id || null;

    const localId = crypto.randomUUID
        ? crypto.randomUUID()
        : Date.now() + Math.random().toString(36).slice(2);

    const task = {
        id: backendId || localId,
        type: taskType,
        content: resolvedTask.content || userMessage,
        preview: previewContent,
        createdAt: new Date().toISOString(),
        raw: resolvedTask || {},
        status: resolvedTask.status || 'completed',
        fecha: resolvedTask.fecha || '',
        hora: resolvedTask.hora || '',
        meeting_type: resolvedTask.meeting_type || '',

        // Debug meta (útil para ver en store)
        _debug: {
            contract,
            icsSource,
            backendId,
            hasICS: !!icsContent,
            icsLen: (icsContent || '').length
        }
    };

    // --------------------------------------------------
    // 5) Persistir ICS en task.raw (unificado)
    // --------------------------------------------------
    if (icsContent) {
        task.raw.ics = icsContent;

        // Mantener filename si existe (puede venir con .ics incluido)
        if (icsFilename) {
            task.raw.ics_filename = icsFilename;
        }

        console.log('✅ ICS guardado en task.raw.ics', {
            len: icsContent.length,
            filename: task.raw.ics_filename || '(none)',
            contract,
            icsSource
        });
    } else {
        console.log('⚠️ No se encontró ICS (después de normalizar)', {
            contract,
            icsSource,
            rootICS: !!data?.ics,
            nestedICS: !!data?.task?.ics
        });
    }

    // --------------------------------------------------
    // 6) Guardar task en store
    // --------------------------------------------------
    addTask(task);

    console.log('✅ addTask OK', {
        storeSize: taskStore.length,
        id: task.id,
        type: task.type,
        hasICS: !!task.raw?.ics
    });

    // --------------------------------------------------
    // 7) Mostrar alerta informativa si hay ICS y tipo permitido
    // --------------------------------------------------
    if (task.raw?.ics && (task.type === 'calendar' || task.type === 'reminder')) {
        showICSAlert(task);
    }

    // --------------------------------------------------
    // 8) Render + persist
    // --------------------------------------------------
    renderTaskSidebar();
    updateSidebarCounters();
    saveToLocalStorage();
    openTaskSection(task.type);

    return task;
}


// ==================== MOSTRAR ALERTA ICS ====================
function showICSAlert(task) {
    if (!task?.raw?.ics) return;

    console.log('📣 Mostrando alerta informativa ICS', {
        taskId: task.id,
        type: task.type
    });

    showAlert({
        icon: 'calendar_month',
        title: 'Evento creado',
        message: 'Descarga este evento  y abrelo para importarlo en tu app de calendario favorita (Google Calendar, Outlook, Apple Calendar).',
        actionText: 'Descargar archivo',
        onAction: () => {
            console.log('🖱️ Click desde alerta → descargar ICS');
            const rawName = task.raw?.ics_filename || task.content || 'evento';
const safeName = rawName.replace(/\.ics$/i, ''); // evita doble .ics
downloadICS(task.raw.ics, safeName);
        }
    });
}

// ==================== EXTRAER PREVIEW ====================
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

// ==================== RENDERIZADO SIDEBAR ====================
export function renderTaskSidebar() {
    try {
        console.log('🔄 Renderizando sidebar de tareas...', { total: taskStore.length });

        const notes = taskStore.filter(t => t.type === 'note');
        const reminders = taskStore.filter(t => t.type === 'reminder');
        const calendar = taskStore.filter(t => t.type === 'calendar');

        console.log('📊 Distribución de tareas:', {
            notes: notes.length,
            reminders: reminders.length,
            calendar: calendar.length
        });

        renderTaskPreview('notes', notes);
        renderTaskPreview('reminders', reminders);
        renderTaskPreview('calendar', calendar);

        updateSidebarCounters();

        console.log('✅ Sidebar renderizado correctamente');

        setupTaskButtonDelegation();

    } catch (error) {
        console.error('❌ Error en renderTaskSidebar:', error);
    }
}

// ==================== RENDERIZADO PREVIEW NORMALIZADO ====================
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

        if (!tasks || tasks.length === 0) {
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

        if (navItem) {
            navItem.classList.add('has-tasks');
            const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
            if (toggleIcon) {
                toggleIcon.textContent = 'expand_more';
            }
        }

        let html = '';

        const previewTasks = tasks.slice(0, 3);

        previewTasks.forEach((task) => {
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

            // Fecha y hora normalizadas
            let datetimeHtml = '';
            if (task.fecha || task.hora) {
                const fecha = task.fecha || '';
                const hora = task.hora || '';
                const separator = (fecha && hora) ? ' ' : '';
                datetimeHtml = `<div class="task-datetime"><small>${fecha}${separator}${hora}</small></div>`;
            }

            // Tipo de reunión normalizado
            let meetingTypeHtml = '';
            if (task.meeting_type) {
                const typeClass = task.meeting_type === 'virtual' ? 'virtual' : 'presencial';
                const typeText = task.meeting_type === 'virtual' ? 'Virtual' : 'Presencial';
                meetingTypeHtml = `<div class="task-meeting-type ${typeClass}">${typeText}</div>`;
            }

            // Badge para pendientes
            let pendingBadge = '';
            if (task.status === 'pending') {
                pendingBadge = '<div class="task-pending-badge">Pendiente</div>';
            }

            // Botones de acción normalizados
            let actionButtons = '';

            // Botón copiar (solo para notas)
            if (task.type === 'note') {
                actionButtons += `
                    <button class="task-preview-btn copy" data-task-id="${task.id}" title="Copiar nota">
                        <span class="material-symbols-outlined">content_copy</span>
                    </button>
                `;
            }

            // Botón descargar ICS (solo si existe)
            if (task.raw && task.raw.ics) {
                actionButtons += `
                    <button class="task-preview-btn download" data-task-id="${task.id}" title="Descargar evento">
                        <span class="material-symbols-outlined">calendar_month</span>
                    </button>
                `;
            }

            // Botón eliminar (siempre)
            actionButtons += `
                <button class="task-preview-btn delete" data-task-id="${task.id}" title="Eliminar">
                    <span class="material-symbols-outlined">close</span>
                </button>
            `;

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
        });

        if (tasks.length > 3) {
            html += `<div class="task-preview-more">+${tasks.length - 3} más</div>`;
        }

        preview.innerHTML = html;

    } catch (error) {
        console.error(`❌ Error en renderTaskPreview para ${listType}:`, error);
    }
}

function openTaskSection(taskType) {
    const content = document.getElementById('taskSectionContent');
    const header = document.getElementById('taskSectionHeader');
    if (content) {
        content.classList.remove('collapsed');
    }
    if (header) {
        header.classList.add('expanded');
        header.setAttribute('aria-expanded', 'true');
        const headerToggleIcon = header.querySelector('.nav-toggle .material-symbols-outlined');
        if (headerToggleIcon) {
            headerToggleIcon.textContent = 'expand_less';
        }
    }

    const listType =
        taskType === 'note' ? 'notes' :
        taskType === 'reminder' ? 'reminders' :
        'calendar';

    const preview = document.getElementById(`${listType}-preview`);
    const navItem = document.getElementById(`nav-${listType}`);

    if (preview) {
        preview.classList.add('active');
        preview.classList.add('expanded');
    }
    if (navItem) {
        navItem.classList.add('has-tasks');
        const toggleIcon = navItem.querySelector('.nav-toggle .material-symbols-outlined');
        if (toggleIcon) {
            toggleIcon.textContent = 'expand_less';
        }
    }

    try {
        localStorage.setItem('claria_tasks_collapsed', 'false');
    } catch (e) {
        // ignore localStorage issues
    }
}

// ==================== DELEGACIÓN DE EVENTOS PARA BOTONES ====================
let taskDelegationSetup = false;

function setupTaskButtonDelegation() {
    if (taskDelegationSetup) {
        console.log('⏭️ Delegación de eventos ya configurada');
        return;
    }

    const sidebar = document.getElementById('sidebar');
    if (!sidebar) {
        console.warn('⚠️ Sidebar no encontrado para delegación de eventos');
        return;
    }

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

        const button = e.target.closest('.task-preview-btn');
        if (!button) return;

        e.preventDefault();
        e.stopPropagation();

        const taskId = button.dataset.taskId;
        if (!taskId) {
            console.warn('⚠️ Botón sin taskId:', button);
            return;
        }

        if (button.classList.contains('delete')) {
            console.log('🗑️ Click delegado: eliminar tarea', taskId);
            deleteTask(taskId);
        } else if (button.classList.contains('download')) {
            console.log('📥 Click delegado: descargar ICS', taskId);
            const task = taskStore.find(t => t.id === taskId);
            if (task && task.raw && task.raw.ics) {
                downloadICS
            } else {
                showErrorMessage('No se encontró el archivo .ics para esta tarea.');
            }
        } else if (button.classList.contains('copy')) {
            console.log('📋 Click delegado: copiar nota', taskId);
            const task = taskStore.find(t => t.id === taskId);
            if (task) {
                copyNoteToClipboard(task.content || '');
            }
        }
    });

    taskDelegationSetup = true;
    console.log('✅ Delegación de eventos configurada en sidebar');
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

// ==================== BIND EVENT LISTENERS (LEGACY) ====================
function bindICSDownloadButtons() {
    console.log('🔗 Binding ICS download buttons...');
    const icsButtons = document.querySelectorAll('.task-preview-btn.download');
    console.log(`📊 Encontrados ${icsButtons.length} botones de descarga ICS`);

    icsButtons.forEach(btn => {
        if (btn.__icsBound) {
            console.log('⏭️ Botón ICS ya tiene listener:', btn.dataset.taskId);
            return;
        }

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const taskId = btn.dataset.taskId;
            const task = taskStore.find(t => t.id === taskId);

            console.log('🖱️ Click descargar ICS', { taskId, hasICS: !!task?.raw?.ics });

            if (!task || !task.raw || !task.raw.ics) {
                console.warn('❌ No se encontró ICS para la tarea', taskId);
                showErrorMessage('No se encontró el archivo .ics para esta tarea.');
                return;
            }

            const rawName = task.raw?.ics_filename || task.content || 'evento';
            const safeName = rawName.replace(/\.ics$/i, ''); // evita doble .ics
            downloadICS(task.raw.ics, safeName);
        });

        btn.__icsBound = true;
        console.log('✅ Listener ICS añadido a botón:', btn.dataset.taskId);
    });
}

function bindDeleteButtons() {
    console.log('🔗 Binding delete buttons...');
    const deleteButtons = document.querySelectorAll('.task-preview-btn.delete');
    console.log(`📊 Encontrados ${deleteButtons.length} botones de eliminar`);

    deleteButtons.forEach(btn => {
        if (btn.__deleteBound) {
            console.log('⏭️ Botón ya tiene listener:', btn.dataset.taskId);
            return;
        }

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const taskId = btn.dataset.taskId;
            console.log('🖱️ Click eliminar tarea:', taskId);
            deleteTask(taskId);
        });

        btn.__deleteBound = true;
        console.log('✅ Listener añadido a botón:', btn.dataset.taskId);
    });

    const copyButtons = document.querySelectorAll('.task-preview-btn.copy');
    console.log(`📊 Encontrados ${copyButtons.length} botones de copiar`);

    copyButtons.forEach(btn => {
        if (btn.__copyBound) {
            console.log('⏭️ Botón copiar ya tiene listener:', btn.dataset.taskId);
            return;
        }

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const taskId = btn.dataset.taskId;
            const task = taskStore.find(t => t.id === taskId);
            if (task) {
                copyNoteToClipboard(task.content || '');
            }
        });

        btn.__copyBound = true;
        console.log('✅ Listener copiar añadido a botón:', btn.dataset.taskId);
    });
}

// ==================== ELIMINAR TAREA ====================
export async function deleteTask(taskId) {
    console.log('🗑️ Eliminando tarea:', taskId);

    if (!confirm('¿Estás seguro de que quieres eliminar esta tarea?')) {
        console.log('❌ Eliminación cancelada por el usuario');
        return;
    }

    try {
        const userKey = sessionStorage.getItem('claroAssistant_sessionId') || '';

        console.log('📡 Enviando solicitud de eliminación al backend...');

        const response = await fetch(`${API_URL}/api/tasks/${taskId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'X-User-Key': userKey
            }
        });

        const data = await response.json();

        if (!data.success) {
            console.warn('❌ Backend respondió con error:', data);
            showErrorMessage(data.message || 'Error al eliminar la tarea');
            return;
        }

        console.log('✅ Tarea eliminada en el backend, rehidratando store...');

        // Limpiar y rehidratar desde backend
        setTaskStore([]);

        if (data.tasks) {
            const allTasks = [
                ...(data.tasks.calendar || []),
                ...(data.tasks.reminder || []),
                ...(data.tasks.note || [])
            ];

            allTasks.forEach(backendTask => {
                const taskType = backendTask.type || 'note';
                const task = {
                    id: backendTask.id,
                    type: taskType,
                    content: backendTask.content || '',
                    preview: backendTask.content || '',
                    createdAt: backendTask.created_at || new Date().toISOString(),
                    raw: backendTask,
                    status: backendTask.status || 'active',
                    fecha: backendTask.fecha || '',
                    hora: backendTask.hora || '',
                    meeting_type: backendTask.meeting_type || ''
                };
                addTask(task);
            });

            console.log('📊 Store rehidratado:', taskStore.length, 'tareas');
        }

        renderTaskSidebar();
        updateSidebarCounters();
        saveToLocalStorage();

        showSuccessMessage('Tarea eliminada correctamente');
        console.log('✅ Tarea eliminada y vista actualizada');

    } catch (err) {
        console.error('❌ Error en deleteTask():', err);
        showErrorMessage('Error de conexión al eliminar la tarea');
    }
}

// ==================== DESCARGAR ICS ====================
export function downloadICS(icsContent, filename = 'evento') {
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
    showSuccessMessage('Evento descargado. Ábrelo para agregarlo a tu calendario.');
}

// ==================== COPIAR NOTA ====================
async function copyNoteToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        console.log('📝 Nota copiada al portapapeles');
        showSuccessMessage('Nota copiada al portapapeles');
    } catch (err) {
        console.error('❌ Error copiando nota:', err);
        showErrorMessage('No se pudo copiar la nota');
    }
}

// ==================== ACTUALIZAR CONTADORES ====================
export function updateSidebarCounters() {
    try {
        const noteCount = taskStore.filter(t => t.type === 'note').length;
        const reminderCount = taskStore.filter(t => t.type === 'reminder').length;
        const calendarCount = taskStore.filter(t => t.type === 'calendar').length;
        const totalCount = taskStore.length;

        console.log('🔢 Actualizando contadores:', { noteCount, reminderCount, calendarCount, totalCount });

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

        // Actualizar el contador total en el título "Gestión de tareas"
        const tasksSectionHeader = document.querySelector('.tasks-section-header .section-title');
        if (tasksSectionHeader) {
            const baseText = 'Gestión de tareas';
            tasksSectionHeader.textContent = totalCount > 0 ? `${baseText} (${totalCount})` : baseText;
        } else {
            // Si no existe el header (todavía no se ha inicializado), actualizar el título original
            const originalTitle = document.querySelector('.section-title.title-text');
            if (originalTitle && originalTitle.textContent.includes('Gestión de tareas')) {
                const baseText = 'Gestión de tareas';
                originalTitle.textContent = totalCount > 0 ? `${baseText} (${totalCount})` : baseText;
            }
        }

    } catch (error) {
        console.error('❌ Error en updateSidebarCounters:', error);
    }
}

// ==================== HELPERS ====================
function escapeHtml(text) {
    if (!text) return '';

    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML
        .replace(/'/g, "&#39;")
        .replace(/"/g, "&quot;")
        .replace(/\n/g, '<br>');
}

function saveToLocalStorage() {
    try {
        const data = {
            conversationHistory: appState.conversationHistory.slice(-50),
            taskStore: taskStore,
            currentMode: appState.currentMode,
            sessionId: sessionStorage.getItem('claroAssistant_sessionId'),
            lastUpdated: new Date().toISOString()
        };

        localStorage.setItem('claroAssistant_state', JSON.stringify(data));
        console.log('💾 Estado guardado en localStorage');
    } catch (e) {
        console.error('❌ Error guardando en localStorage:', e);
    }
}

// ==================== RENDERIZAR DESDE BACKEND ====================
export function renderSidebarTasks(tasksByType) {
    setTaskStore([]);
    const calendar = tasksByType.calendar || [];
    const reminders = tasksByType.reminder || tasksByType.reminders || [];
    const notes = tasksByType.note || tasksByType.notes || [];

    calendar.forEach(t => addTask({ ...t, type: 'calendar', preview: extractPreviewContent(t.content || '', 'calendar') }));
    reminders.forEach(t => addTask({ ...t, type: 'reminder', preview: extractPreviewContent(t.content || '', 'reminder') }));
    notes.forEach(t => addTask({ ...t, type: 'note', preview: extractPreviewContent(t.content || '', 'note') }));

    renderTaskSidebar();
}
