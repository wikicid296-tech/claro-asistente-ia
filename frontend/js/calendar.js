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

// ==================== PARSER DE FECHAS AVANZADO ====================
function extractEventDataFromMessage(message) {
    if (!message || typeof message !== 'string') return null;
    
    // 1. Helper para obtener fecha LOCAL formato YYYY-MM-DD (Evita bugs de zona horaria UTC)
    const getLocalDateStr = (dateObj) => {
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    };

    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    // Configuración por defecto: "Mañana a las 9:00 AM" (Mejor default que 'hoy')
    const data = {
        title: 'Evento Agendado', 
        date: getLocalDateStr(tomorrow), 
        time: '09:00',
        location: 'Sin ubicación',
        duration: 1
    };
    
    const lowerMsg = message.toLowerCase();

    // 2. Extracción de Título (Mejorada para limpiar días de la semana)
    const intentRegex = /(?:agendar|agenda|programar|cita|reunión|evento|recordatorio|nota|apunta|anota|avisame|avísame|recuerdame|recuérdame)\s+(?:con|de|para|sobre)?\s+([^,.!?\n]+)/i;
    const intentMatch = message.match(intentRegex);
    
    if (intentMatch && intentMatch[1]) {
        // Quitamos palabras temporales del título para que no quede "Reunión el viernes"
        let cleanTitle = intentMatch[1]
            .replace(/\b(mañana|pasado mañana|hoy|ayer|el lunes|el martes|el miercoles|el miércoles|el jueves|el viernes|el sabado|el sábado|el domingo|a las|a la)\b.*/gi, '')
            .trim();
            
        if (cleanTitle.length > 2) {
            data.title = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
        }
    } else {
        // Fallback simple
        const simpleWords = message.split(' ').slice(0, 5).join(' ').replace(/agendar|agenda/gi, '').trim();
        if (simpleWords.length > 0) data.title = simpleWords;
    }

    // 3. LÓGICA DE FECHAS (Aquí está la magia para interpretar "mañana" y días)
    let dateFound = false;

    // A. "Hoy", "Mañana", "Pasado mañana"
    if (lowerMsg.includes('hoy')) {
        data.date = getLocalDateStr(today);
        dateFound = true;
    } else if (lowerMsg.includes('pasado mañana')) {
        const dayAfter = new Date(today);
        dayAfter.setDate(today.getDate() + 2);
        data.date = getLocalDateStr(dayAfter);
        dateFound = true;
    } else if (lowerMsg.includes('mañana')) {
        data.date = getLocalDateStr(tomorrow);
        dateFound = true;
    } 
    
    // B. Días de la semana ("el viernes", "el lunes")
    if (!dateFound) {
        const daysOfWeek = {
            'domingo': 0, 'lunes': 1, 'martes': 2, 'miércoles': 3, 'miercoles': 3,
            'jueves': 4, 'viernes': 5, 'sábado': 6, 'sabado': 6
        };

        for (const [dayName, dayIndex] of Object.entries(daysOfWeek)) {
            if (lowerMsg.includes(dayName)) {
                const targetDate = new Date(today);
                const currentDay = today.getDay(); // 0-6
                
                // Calcular cuántos días faltan
                let daysUntil = dayIndex - currentDay;
                if (daysUntil <= 0) {
                    daysUntil += 7; // Si es hoy o ya pasó esta semana, agendar para la próxima
                }
                
                targetDate.setDate(today.getDate() + daysUntil);
                data.date = getLocalDateStr(targetDate);
                dateFound = true;
                break;
            }
        }
    }

    // C. Fechas específicas (25/12 o 2024-01-01)
    if (!dateFound) {
        const dateMatch = message.match(/(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?/);
        if (dateMatch) {
            const day = parseInt(dateMatch[1]);
            const month = parseInt(dateMatch[2]) - 1; // Meses en JS son 0-11
            const year = dateMatch[3] ? parseInt(dateMatch[3]) : today.getFullYear();
            
            // Ajustar año si es corto (e.g. 24 -> 2024)
            const fullYear = year < 100 ? 2000 + year : year;
            
            const specificDate = new Date(fullYear, month, day);
            data.date = getLocalDateStr(specificDate);
        }
    }
    
    // 4. Extracción de Hora (Soporte AM/PM y 24h)
    // Regex mejorado para capturar "10", "10:30", "10am", "10 de la noche"
    const timeMatch = message.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|de la (?:mañana|tarde|noche))?/i);
    
    if (timeMatch) {
        let hour = parseInt(timeMatch[1]);
        let minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
        const period = timeMatch[3] ? timeMatch[3].toLowerCase() : '';
        
        // Ajuste 12h -> 24h
        if ((period.includes('pm') || period.includes('tarde') || period.includes('noche')) && hour < 12) {
            hour += 12;
        }
        if ((period.includes('am') || period.includes('mañana')) && hour === 12) {
            hour = 0;
        }
        
        data.time = `${hour.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }

    console.log('📅 Datos procesados:', { msg: message, extracted: data });
    return data;
}
// ==================== GENERADOR DE ICS PARA TAREAS ====================
function buildICS({ title, description, location, date, time, duration }) {
    const start = `${date.replace(/-/g, '')}T${time.replace(':', '')}00`;
    const endDate = new Date(`${date}T${time}`);
    endDate.setMinutes(endDate.getMinutes() + duration * 60);

    const end =
        endDate.toISOString()
            .replace(/[-:]/g, '')
            .split('.')[0];

    return `
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Claria//ES
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:${crypto.randomUUID()}
DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').split('.')[0]}Z
SUMMARY:${title}
DESCRIPTION:${description}
LOCATION:${location}
DTSTART:${start}
DTEND:${end}
END:VEVENT
END:VCALENDAR
`.trim();
}

async function generateICSForTask(task) {
    console.group('📅 generateICSForTask');

    const eventData = extractEventDataFromMessage(task.content);

    if (!eventData || !eventData.title) {
        console.warn('No se pudieron extraer datos del evento');
        console.groupEnd();
        return false;
    }

    const icsContent = buildICS({
        title: eventData.title,
        description: task.content,
        location: eventData.location,
        date: eventData.date,
        time: eventData.time,
        duration: eventData.duration
    });

    const blob = new Blob([icsContent], { type: 'text/calendar' });

    const base64 = await new Promise(resolve => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
    });

    task.icsFileUrl = base64;
    task.icsFileName = `evento_${eventData.date}_${eventData.time.replace(':', '')}.ics`;

    console.log('ICS generado:', task.icsFileName);
    console.groupEnd();

    return true;
}


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

async function downloadICSFile(dataUrl, filename) {
    const isBase64 = dataUrl.startsWith('data:');
    
    // OPCIÓN 1: Intentar Web Share API (nativo en móvil)
    if (isBase64 && navigator.share) {
        try {
            // Extraer el contenido Base64
            const base64Content = dataUrl.split(',')[1];
            const binaryData = atob(base64Content);
            const arrayBuffer = new Uint8Array(binaryData.length);
            
            for (let i = 0; i < binaryData.length; i++) {
                arrayBuffer[i] = binaryData.charCodeAt(i);
            }
            
            const blob = new Blob([arrayBuffer], { type: 'text/calendar' });
            const file = new File([blob], filename, { type: 'text/calendar' });
            
            // Intentar compartir (nativo en móvil)
            await navigator.share({
                files: [file],
                title: 'Evento de calendario',
                text: 'Agregar evento al calendario'
            });
            
            console.log('✅ Evento compartido:', filename);
            return;
        } catch (err) {
            console.log('ℹ️ Share API no disponible, usando descarga estándar');
        }
    }
    
    // OPCIÓN 2: Descarga estándar (fallback)
    if (isBase64) {
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        
        setTimeout(() => {
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
            }, 100);
        }, 100);
    } else {
        // Método legacy para blob URLs (web)
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }
    
    console.log('✅ Descargando:', filename);
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

// ==================== EXPORTAR FUNCIONES ====================
window.showCalendarModal = showCalendarModal;
window.closeCalendarModal = closeCalendarModal;
window.extractEventDataFromMessage = extractEventDataFromMessage;
window.generateICSForTask = generateICSForTask;
window.downloadICSFile = downloadICSFile; 

console.log('✅ Módulo de calendario cargado');
