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
function extractEventDataFromMessage(message) {
    if (!message || typeof message !== 'string') {
        return null;
    }
    
    const data = {
        title: '',
        date: '',
        time: '',
        location: '',
        duration: 1
    };
    
    // Extraer título (primeras palabras del mensaje)
    const titleMatch = message.match(/^([^.!?]+)[.!?]/);
    if (titleMatch) {
        data.title = titleMatch[1].trim();
    } else {
        // Si no hay punto, tomar las primeras 5-7 palabras
        const words = message.split(' ').slice(0, 7);
        data.title = words.join(' ').trim();
    }
    
    // Extraer fecha
    const today = new Date();
    
    // Patrones de fecha
    if (message.toLowerCase().includes('mañana')) {
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        data.date = tomorrow.toISOString().split('T')[0];
    } else if (message.toLowerCase().includes('hoy')) {
        data.date = today.toISOString().split('T')[0];
    } else if (message.toLowerCase().includes('pasado mañana')) {
        const dayAfterTomorrow = new Date(today);
        dayAfterTomorrow.setDate(dayAfterTomorrow.getDate() + 2);
        data.date = dayAfterTomorrow.toISOString().split('T')[0];
    } else {
        // Buscar patrones de fecha específica (DD/MM/YYYY o YYYY-MM-DD)
        const datePattern1 = /(\d{1,2})\/(\d{1,2})\/(\d{4})/;
        const datePattern2 = /(\d{4})-(\d{1,2})-(\d{1,2})/;
        
        const match1 = message.match(datePattern1);
        const match2 = message.match(datePattern2);
        
        if (match1) {
            const [_, day, month, year] = match1;
            data.date = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
        } else if (match2) {
            data.date = match2[0];
        } else {
            // Si no hay fecha específica, usar hoy
            data.date = today.toISOString().split('T')[0];
        }
    }
    
    // Extraer hora
    const timePatterns = [
        /(\d{1,2}):(\d{2})/, // 14:30, 9:00
        /(\d{1,2})\s*(?:de la|)\s*(mañana|tarde|noche)/i, // 8 de la mañana, 3 tarde, 10 de la noche
        /a las\s*(\d{1,2})/i, // a las 8, a las 14
        /(\d{1,2})\s*(?:am|pm)/i // 8am, 3pm
    ];
    
    let timeFound = false;
    
    for (const pattern of timePatterns) {
        const match = message.match(pattern);
        if (match) {
            if (pattern === timePatterns[0]) {
                // Formato 24h: 14:30
                data.time = match[0];
                timeFound = true;
                break;
            } else if (pattern === timePatterns[1]) {
                // Formato descriptivo: 8 de la mañana
                let hour = parseInt(match[1]);
                const period = match[2].toLowerCase();
                
                if (period === 'tarde' || period === 'noche') {
                    if (hour < 12) hour += 12;
                }
                if (period === 'mañana' && hour === 12) {
                    hour = 0;
                }
                
                data.time = `${hour.toString().padStart(2, '0')}:00`;
                timeFound = true;
                break;
            } else if (pattern === timePatterns[2] || pattern === timePatterns[3]) {
                // Formato simple: a las 8, o 8am
                let hour = parseInt(match[1]);
                const isPM = message.toLowerCase().includes('pm') || 
                            message.toLowerCase().includes('tarde') || 
                            message.toLowerCase().includes('noche');
                
                if (isPM && hour < 12) hour += 12;
                if (!isPM && hour === 12) hour = 0;
                
                data.time = `${hour.toString().padStart(2, '0')}:00`;
                timeFound = true;
                break;
            }
        }
    }
    
    // Si no se encontró hora, usar hora por defecto (09:00)
    if (!timeFound) {
        data.time = '09:00';
    }
    
    // Extraer lugar
    const locationPatterns = [
        /en\s+(?:las?|los?)\s+([^,.!?]+?(?:oficinas|sala|reunión|local|edificio|centro))/i,
        /en\s+([^,.!?]+)/i,
        /ubicado\s+en\s+([^,.!?]+)/i,
        /lugar:\s*([^,.!?]+)/i
    ];
    
    for (const pattern of locationPatterns) {
        const match = message.match(pattern);
        if (match) {
            data.location = match[1].trim();
            break;
        }
    }
    
    // Si no se encontró lugar, usar valor por defecto
    if (!data.location) {
        data.location = 'Sin ubicación específica';
    }
    
    // Extraer duración si se menciona
    if (message.match(/\b(media hora|30 min|30 minutos)\b/i)) {
        data.duration = 0.5;
    } else if (message.match(/\b(una hora|1 hora|60 min)\b/i)) {
        data.duration = 1;
    } else if (message.match(/\b(hora y media|1\.5 horas|90 min)\b/i)) {
        data.duration = 1.5;
    } else if (message.match(/\b(2 horas|120 min)\b/i)) {
        data.duration = 2;
    }
    
    console.log('📋 Datos extraídos del mensaje:', data);
    return data;
}

// ==================== GENERADOR DE ICS PARA TAREAS ====================
async function generateICSForTask(task) {
    try {
        // 1. Extraer datos del mensaje del usuario
        const eventData = extractEventDataFromMessage(task.content);
        
        // 2. Si no hay datos válidos, salir
        if (!eventData || !eventData.title) {
            console.log('❌ No se pudieron extraer datos válidos del mensaje');
            return;
        }
        
        // 3. Preparar datos para el backend
        const requestData = {
            title: eventData.title,
            description: task.content || 'Evento generado desde chat',
            location: eventData.location,
            date: eventData.date,
            time: eventData.time,
            duration: eventData.duration
        };
        
        console.log('📤 Enviando datos para generar .ics:', requestData);
        
        // 4. Enviar request al backend
        const response = await fetch(`${CALENDAR_API_URL}/calendar/create-event`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error al generar el archivo .ics');
        }
        
        // 5. Obtener blob del archivo
        const blob = await response.blob();

        // 6. Convertir blob a Base64
        const reader = new FileReader();
        const base64Promise = new Promise((resolve) => {
             reader.onloadend = () => resolve(reader.result);
             reader.readAsDataURL(blob);
        });
        const base64Data = await base64Promise;

        // 7. Guardar datos en el objeto task
        task.icsFileUrl = base64Data;  // Ahora es Base64 en lugar de blob URL
        task.icsFileName = `evento_${eventData.date}_${eventData.time.replace(':', '')}.ics`;
        
        console.log('✅ Archivo .ics generado para:', task.id);
        console.log('📁 Archivo guardado como:', task.icsFileName);
        
        return true;
        
    } catch (error) {
        console.error('❌ Error generando .ics:', error);
        return false;
    }
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
    
    console.log('🔍 Iniciando descarga/compartir:', filename);
    console.log('📱 User Agent:', navigator.userAgent);
    console.log('🔗 Tipo de URL:', isBase64 ? 'Base64' : 'Blob');
    
    if (!isBase64) {
        // Si no es Base64, usar método legacy
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        console.log('✅ Descarga iniciada (blob URL)');
        return;
    }
    
    // Convertir Base64 a Blob
    try {
        const base64Content = dataUrl.split(',')[1];
        const binaryData = atob(base64Content);
        const arrayBuffer = new Uint8Array(binaryData.length);
        
        for (let i = 0; i < binaryData.length; i++) {
            arrayBuffer[i] = binaryData.charCodeAt(i);
        }
        
        const blob = new Blob([arrayBuffer], { type: 'text/calendar' });
        const blobUrl = URL.createObjectURL(blob);
        
        console.log('✅ Blob creado:', blobUrl);
        
        // OPCIÓN 1: Intentar Web Share API
        if (navigator.share && navigator.canShare) {
            try {
                const file = new File([blob], filename, { type: 'text/calendar' });
                const canShareFiles = navigator.canShare({ files: [file] });
                
                if (canShareFiles) {
                    console.log('📤 Intentando compartir con Share API...');
                    await navigator.share({
                        files: [file],
                        title: 'Evento de calendario',
                        text: 'Agregar evento al calendario'
                    });
                    
                    URL.revokeObjectURL(blobUrl);
                    console.log('✅ Evento compartido exitosamente');
                    return;
                }
            } catch (shareErr) {
                console.log('⚠️ Share API falló:', shareErr.message);
            }
        }
        
        // OPCIÓN 2: Abrir en nueva pestaña (funciona en WebView)
        console.log('📂 Intentando abrir en nueva ventana...');
        const newWindow = window.open(blobUrl, '_blank');
        
        if (newWindow) {
            console.log('✅ Archivo abierto en nueva ventana');
            
            // Limpiar después de 3 segundos
            setTimeout(() => {
                URL.revokeObjectURL(blobUrl);
            }, 3000);
            
            // Mostrar instrucciones al usuario
            showSuccessMessage('✅ Archivo generado. Presiona "Descargar" o "Agregar a calendario" en la nueva ventana.');
            return;
        }
        
        // OPCIÓN 3: Crear enlace de descarga manual
        console.log('🔗 Creando enlace de descarga manual...');
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = filename;
        a.target = '_blank';
        a.style.display = 'none';
        document.body.appendChild(a);
        
        // Simular click con delay para WebView
        setTimeout(() => {
            a.click();
            console.log('✅ Descarga iniciada');
            
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(blobUrl);
            }, 1000);
        }, 100);
        
    } catch (error) {
        console.error('❌ Error al procesar archivo:', error);
        showErrorMessage('❌ Error al descargar el archivo. Intenta nuevamente.');
    }
}

// ==================== EXPORTAR FUNCIONES ====================
window.showCalendarModal = showCalendarModal;
window.closeCalendarModal = closeCalendarModal;
window.extractEventDataFromMessage = extractEventDataFromMessage;
window.generateICSForTask = generateICSForTask;
window.downloadICSFile = downloadICSFile; 

console.log('✅ Módulo de calendario cargado');