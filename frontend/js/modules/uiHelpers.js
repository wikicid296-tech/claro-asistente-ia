// ==================== UI HELPERS ====================

// ==================== MOSTRAR ALERTA MODAL ====================
export function showAlert({icon, title, message, actionText, onAction, cancelText = 'Cerrar'}) {
    // Remover alerta anterior si existe
    const existingAlert = document.querySelector('.alert-modal');
    if (existingAlert) {
        existingAlert.remove();
    }

    const alertHtml = `
        <div class="alert-modal active">
            <div class="alert-content">
                <div class="alert-icon">
                    <span class="material-symbols-outlined">${icon}</span>
                </div>
                <h3 class="alert-title">${title}</h3>
                <p class="alert-message">${message}</p>
                <div class="alert-actions">
                    ${actionText ? `<button class="alert-btn alert-btn-primary" id="alertActionBtn">${actionText}</button>` : ''}
                    <button class="alert-btn alert-btn-secondary" id="alertCancelBtn">${cancelText}</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', alertHtml);

    const alertModal = document.querySelector('.alert-modal');
    const actionBtn = document.getElementById('alertActionBtn');
    const cancelBtn = document.getElementById('alertCancelBtn');

    if (actionBtn && onAction) {
        actionBtn.addEventListener('click', () => {
            onAction();
            alertModal.remove();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            alertModal.remove();
        });
    }

    // Click fuera para cerrar
    alertModal.addEventListener('click', (e) => {
        if (e.target === alertModal) {
            alertModal.remove();
        }
    });
}

// ==================== MOSTRAR MENSAJE DE ÉXITO ====================
export function showSuccessMessage(message) {
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

// ==================== MOSTRAR MENSAJE DE ERROR ====================
export function showErrorMessage(message) {
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

// ==================== MOSTRAR LOADING ====================
export function showLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.classList.add('active');
    }
}

// ==================== OCULTAR LOADING ====================
export function hideLoading() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.classList.remove('active');
    }
}

// ==================== MOSTRAR MODAL PREMIUM ====================
export function showPremiumModal() {
    const overlay = document.getElementById('premiumOverlay');
    if (overlay) {
        overlay.classList.add('active');
    }
}

// ==================== CERRAR MODAL PREMIUM ====================
export function closePremiumModal() {
    const overlay = document.getElementById('premiumOverlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

// ==================== TOAST PARA BÚSQUEDA WEB AUTO ====================
export function showAutoWebSearchToast() {
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

// ==================== TOAST PARA ADVERTENCIA DE USO ====================
export function showUsageWarningToast(remaining) {
    const existingWarning = document.querySelector('.usage-warning-toast');
    if (existingWarning) {
        existingWarning.remove();
    }

    const warningMsg = document.createElement('div');
    warningMsg.className = 'usage-warning-toast';
    warningMsg.innerHTML = `
        <span style="font-size: 20px;">⚠️</span>
        <div>
            <strong>Casi alcanzas el límite</strong>
            <br>
            <small>Quedan $${remaining.toFixed(2)} de tu límite mensual</small>
        </div>
    `;

    document.body.appendChild(warningMsg);

    setTimeout(() => {
        warningMsg.style.opacity = '0';
        setTimeout(() => warningMsg.remove(), 300);
    }, 5000);
}
