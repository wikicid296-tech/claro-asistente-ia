// ==================== CONFIGURACIÓN ====================
const CALENDAR_API_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://claro-asistente-ia.onrender.com';

// ==================== MODAL HTML ====================
function createCalendarModal() {
    const modalHTML = `
        <div class="calendar-modal-overlay" id="calendarModalOverlay">
            <div class="calendar-modal">
                <div class="calendar-modal-header">
                    <h2>📅 Crear Evento de Calendario</h2>
                    <button class="calendar-modal-close" id="closeCalendarModal">✕</button>
                </div>
                
                <div class="calendar-modal-body">
                    <form id="calendarForm">
                        <div class="calendar-form-group">
                            <label for="eventTitle">📝 Título del evento *</label>
                            <input type="text" id="eventTitle" placeholder="Ej: Reunión con cliente" required>
                        </div>
                        
                        <div class="calendar-form-group">
                            <label for="eventDescription">📄 Descripción</label>
                            <textarea id="eventDescription" placeholder="Describe el evento..." rows="3"></textarea>
                        </div>
                        
                        <div class="calendar-form-row">
                            <div class="calendar-form-group">
                                <label for="eventDate">📆 Fecha *</label>
                                <input type="date" id="eventDate" required>
                            </div>
                            
                            <div class="calendar-form-group">
                                <label for="eventTime">🕐 Hora *</label>
                                <input type="time" id="eventTime" required>
                            </div>
                        </div>
                        
                        <div class="calendar-form-group">
                            <label for="eventDuration">⏱️ Duración</label>
                            <select id="eventDuration">
                                <option value="0.5">30 minutos</option>
                                <option value="1" selected>1 hora</option>
                                <option value="1.5">1.5 horas</option>
                                <option value="2">2 horas</option>
                                <option value="3">3 horas</option>
                            </select>
                        </div>
                        
                        <div class="calendar-form-group">
                            <label for="eventLocation">📍 Lugar</label>
                            <input type="text" id="eventLocation" placeholder="Ej: Oficina Central">
                        </div>
                        
                        <div class="calendar-modal-footer">
                            <button type="button" class="calendar-btn-cancel" id="cancelCalendarBtn">
                                Cancelar
                            </button>
                            <button type="submit" class="calendar-btn-create" id="createCalendarBtn">
                                📅 Crear Evento
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    `;
    
    // Agregar al body si no existe
    if (!document.getElementById('calendarModalOverlay')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
}

// ==================== MOSTRAR MODAL ====================
function showCalendarModal(prefilledData = null) {
    createCalendarModal();
    
    const overlay = document.getElementById('calendarModalOverlay');
    overlay.classList.add('active');
    
    // Pre-llenar datos si vienen del chat
    if (prefilledData) {
        if (prefilledData.title) document.getElementById('eventTitle').value = prefilledData.title;
        if (prefilledData.description) document.getElementById('eventDescription').value = prefilledData.description;
        if (prefilledData.location) document.getElementById('eventLocation').value = prefilledData.location;
        if (prefilledData.date) document.getElementById('eventDate').value = prefilledData.date;
        if (prefilledData.time) document.getElementById('eventTime').value = prefilledData.time;
    } else {
        // Establecer fecha y hora actual por defecto
        const now = new Date();
        const dateStr = now.toISOString().split('T')[0];
        const timeStr = now.toTimeString().slice(0, 5);
        
        document.getElementById('eventDate').value = dateStr;
        document.getElementById('eventTime').value = timeStr;
    }
    
    // Event listeners
    document.getElementById('closeCalendarModal').addEventListener('click', closeCalendarModal);
    document.getElementById('cancelCalendarBtn').addEventListener('click', closeCalendarModal);
    document.getElementById('calendarForm').addEventListener('submit', handleCreateEvent);
    
    // Cerrar al hacer clic fuera del modal
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            closeCalendarModal();
        }
    });
}

// ==================== CERRAR MODAL ====================
function closeCalendarModal() {
    const overlay = document.getElementById('calendarModalOverlay');
    if (overlay) {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 300);
    }
}

// ==================== CREAR EVENTO ====================
async function handleCreateEvent(e) {
    e.preventDefault();
    
    const submitBtn = document.getElementById('createCalendarBtn');
    const originalText = submitBtn.innerHTML;
    
    try {
        // Deshabilitar botón
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Creando...';
        
        // Obtener datos del formulario
        const eventData = {
            title: document.getElementById('eventTitle').value.trim(),
            description: document.getElementById('eventDescription').value.trim() || 'Evento creado desde Claro Assistant',
            location: document.getElementById('eventLocation').value.trim() || 'Sin ubicación',
            date: document.getElementById('eventDate').value,
            time: document.getElementById('eventTime').value,
            duration: parseFloat(document.getElementById('eventDuration').value)
        };
        
        // Validar datos
        if (!eventData.title || !eventData.date || !eventData.time) {
            throw new Error('Por favor completa todos los campos requeridos');
        }
        
        console.log('📤 Enviando datos:', eventData);
        
        // Enviar petición al backend
        const response = await fetch(`${CALENDAR_API_URL}/calendar/create-event`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(eventData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al crear el evento');
        }
        
        // Descargar archivo .ics
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `evento_${eventData.date}_${eventData.time.replace(':', '')}.ics`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        console.log('✅ Evento creado y descargado');
        
        // Mostrar mensaje de éxito
        showSuccessMessage(`✅ Evento "${eventData.title}" creado exitosamente. El archivo se descargó automáticamente.`);
        
        // Cerrar modal
        closeCalendarModal();
        
    } catch (error) {
        console.error('❌ Error al crear evento:', error);
        showErrorMessage(`❌ Error: ${error.message}`);
        
        // Restaurar botón
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// ==================== EXTRACTOR DE DATOS DEL MENSAJE ====================
// En calendar.js

// Frontend no interpreta texto ni genera ICS: backend provee el ICS ya listo.


// ==================== MENSAJES DE ÉXITO/ERROR ====================
function showSuccessMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'calendar-alert calendar-alert-success';
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10001;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 4000);
}

function showErrorMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'calendar-alert calendar-alert-error';
    alertDiv.textContent = message;
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: #dc3545;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10001;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', function() {
    // Botón de prueba (si existe)
    const testBtn = document.getElementById('testCalendarBtn');
    if (testBtn) {
        testBtn.addEventListener('click', function() {
            showCalendarModal();
        });
    }
});

function downloadICS(icsContent, fileName = 'evento') {
    if (!icsContent) return;

    console.log('📥 Iniciando flujo de descarga ICS');

    const blob = new Blob([icsContent], {
        type: 'text/calendar;charset=utf-8'
    });

    const url = URL.createObjectURL(blob);
    const finalFileName = `${fileName}.ics`;

    const a = document.createElement('a');
    a.href = url;
    a.download = finalFileName;
    a.style.display = 'none';

    document.body.appendChild(a);

    let autoDownloadSucceeded = true;

    try {
        // 🔥 Intento de autodescarga (best effort)
        a.click();
    } catch (err) {
        autoDownloadSucceeded = false;
        console.warn('⚠️ Autodescarga bloqueada por el navegador', err);
    }

    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // 🟡 Fallback UX: toast solo si no se descargó automáticamente
        if (!autoDownloadSucceeded) {
            showICSDownloadToast(finalFileName, url, finalFileName);
        }
    }, 150);
}


function autoOpenICSFile(icsDataUrl) {
    try {
        console.log('🚀 Ejecutando protocolo de apertura automática...');
        
        // 1. LIMPIEZA
        let base64Content = icsDataUrl.includes(',') 
            ? icsDataUrl.split(',')[1] 
            : icsDataUrl;

        base64Content = base64Content.replace(/\s/g, '');

        // 2. Decodificar
        const binary = atob(base64Content);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        
        const blob = new Blob([bytes], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const filename = `evento_${Date.now()}.ics`;

        // 3. Intentar descarga/apertura
        let opened = window.open(url, '_blank');
        
        if (!opened || opened.closed || typeof opened.closed == 'undefined') {
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        // 4. TOAST EDUCATIVO (Aquí está el cambio de UX)
        // Verificamos si ya le mostramos el tip antes (para no ser molestos)
        const hasSeenTip = localStorage.getItem('claria_ics_tip_shown');
        
        const toast = document.createElement('div');
        
        // Contenido del Toast: Mensaje de éxito + Tip educativo (solo si no lo ha visto muchas veces)
        let tipHTML = '';
        if (!hasSeenTip) {
            tipHTML = `
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.2); font-size:11px; color:#ffc107;">
                    💡 <strong>Tip Pro:</strong> Al descargar, haz clic en la flecha de la descarga y elige 
                    <em>"Abrir siempre archivos de este tipo"</em> para automatizarlo.
                </div>
            `;
            // Marcar que ya vio el tip (opcional: quitar esta línea si quieres que salga siempre)
            localStorage.setItem('claria_ics_tip_shown', 'true');
        }

        toast.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:4px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <span style="font-size:20px;">📅</span>
                    <div style="flex:1;">
                        <div style="font-weight:bold; font-size:14px;">Evento Descargado</div>
                        <div style="font-size:11px; opacity:0.9;">Haz clic para agregarlo a tu calendario</div>
                    </div>
                    <button id="manualOpenBtn" style="background:white; color:#333; border:none; padding:6px 12px; border-radius:12px; font-weight:bold; cursor:pointer; font-size:12px; box-shadow:0 2px 5px rgba(0,0,0,0.2);">
                        ABRIR
                    </button>
                </div>
                ${tipHTML}
            </div>
        `;

        toast.style.cssText = `
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            background: #212529; color: white; padding: 16px 20px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4); z-index: 10000;
            animation: slideUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            min-width: 320px; max-width: 90%; font-family: sans-serif;
        `;
        
        document.body.appendChild(toast);
        
        // Botón manual
        document.getElementById('manualOpenBtn').onclick = () => {
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            toast.remove();
        };

        // Tiempo de visualización extendido si hay tip
        const duration = hasSeenTip ? 5000 : 10000;

        setTimeout(() => {
            if (toast.style) {
                toast.style.opacity = '0';
                toast.style.transform = 'translate(-50%, 20px)';
                toast.style.transition = 'all 0.5s ease';
            }
            setTimeout(() => { 
                if(toast.parentNode) toast.remove(); 
                window.URL.revokeObjectURL(url);
            }, 500);
        }, duration);

        console.log('✅ Apertura finalizada');
    } catch (err) {
        console.error('❌ Error:', err);
    }
}

// ==================== DESCARGAR ICS DESDE BACKEND ====================
function downloadICSFromBackend(icsPayload) {
    if (!icsPayload || !icsPayload.ics_content) return;

    const blob = new Blob([icsPayload.ics_content], {
        type: 'text/calendar;charset=utf-8',
    });

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = icsPayload.filename || 'evento.ics';

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ==================== EXPORTAR FUNCIONES ====================
window.showCalendarModal = showCalendarModal;
window.closeCalendarModal = closeCalendarModal;
window.downloadICSFile = downloadICSFile;
window.downloadICSFromBackend = downloadICSFromBackend;

console.log('✅ Módulo de calendario cargado');
