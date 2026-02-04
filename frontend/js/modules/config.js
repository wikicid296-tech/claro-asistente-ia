// ==================== CONFIGURACIÓN Y CONSTANTES ====================
export const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://claro-asistente-ia.onrender.com';

export const MESSAGE_LIMIT = {
    FREE: 20,
    PRO: Infinity
};

export const TOKEN_CONFIG = {
    MAX_TOKENS: 1000,
    CHARS_PER_TOKEN: 3.5
};

export const MODE_NAMES = {
    descubre: 'Descubre',
    tareas: 'Gestión de tareas',
    aprende: 'Aprende.org',
    busqueda_web: 'Búsqueda web'
};

export const MODE_PLACEHOLDERS = {
    descubre: 'Pregunta lo que quieras',
    tareas: 'Gestiona tus tareas',
    aprende: 'Pregunta sobre cursos de aprende.org',
    busqueda_web: 'Busca cualquier información en la web...'
};
