const CHAT_STORAGE_KEY = "claria_chat_history_v1";
const CONVERSATIONS_KEY = "claria_conversations_v1";

// ==================== HISTORIAL ACTUAL ====================
export function loadChatHistory() {
  try {
    const raw = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (e) {
    console.error("Error loading chat history", e);
    return [];
  }
}

export function saveChatHistory(messages) {
  try {
    localStorage.setItem(
      CHAT_STORAGE_KEY,
      JSON.stringify(messages)
    );
  } catch (e) {
    console.error("Error saving chat history", e);
  }
}

export function clearChatHistory() {
  localStorage.removeItem(CHAT_STORAGE_KEY);
}

// ==================== CONVERSACIONES HISTÓRICAS ====================
/**
 * Carga todas las conversaciones guardadas
 */
export function loadConversations() {
  try {
    const raw = localStorage.getItem(CONVERSATIONS_KEY);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (e) {
    console.error("Error loading conversations", e);
    return [];
  }
}

/**
 * Guarda una conversación completa con metadata
 * @param {Array} messages - Mensajes de la conversación
 * @param {String} title - Título de la conversación (primera línea del usuario o auto-generado)
 * @returns {String} - ID de la conversación guardada
 */
export function saveConversation(messages, title = null) {
  try {
    const conversations = loadConversations();
    
    // Auto-generar título si no se proporciona
    let conversationTitle = title;
    if (!conversationTitle) {
      const firstUserMessage = messages.find(m => m.role === 'user' || m.type === 'user');
      if (firstUserMessage) {
        conversationTitle = firstUserMessage.content.substring(0, 50);
        if (firstUserMessage.content.length > 50) {
          conversationTitle += '...';
        }
      } else {
        conversationTitle = 'Conversación sin título';
      }
    }
    
    const conversation = {
      id: 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
      title: conversationTitle,
      messages: messages,
      timestamp: new Date().toISOString(),
      messageCount: messages.length
    };
    
    conversations.unshift(conversation); // Agregar al inicio
    
    // Limitar a últimas 20 conversaciones
    const limited = conversations.slice(0, 20);
    
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(limited));
    console.log('✅ Conversación guardada:', conversation.id);
    
    return conversation.id;
  } catch (e) {
    console.error("Error saving conversation", e);
    return null;
  }
}

/**
 * Carga una conversación específica por ID
 */
export function loadConversationById(conversationId) {
  try {
    const conversations = loadConversations();
    return conversations.find(c => c.id === conversationId);
  } catch (e) {
    console.error("Error loading conversation by ID", e);
    return null;
  }
}

/**
 * Elimina una conversación por ID
 */
export function deleteConversation(conversationId) {
  try {
    const conversations = loadConversations();
    const filtered = conversations.filter(c => c.id !== conversationId);
    localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(filtered));
    console.log('🗑️ Conversación eliminada:', conversationId);
  } catch (e) {
    console.error("Error deleting conversation", e);
  }
}

/**
 * Limpia todo el historial de conversaciones
 */
export function clearConversations() {
  try {
    localStorage.removeItem(CONVERSATIONS_KEY);
    console.log('🗑️ Todo el historial de conversaciones fue eliminado');
  } catch (e) {
    console.error("Error clearing conversations", e);
  }
}
