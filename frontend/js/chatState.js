import {
  loadChatHistory,
  saveChatHistory,
  saveConversation,
  loadConversations,
  loadConversationById,
  deleteConversation,
  clearConversations
} from "./chatStorage.js";

let messages = loadChatHistory();

export function getMessages() {
  return messages;
}

export function addMessage(role, content) {
  const msg = {
    id: crypto.randomUUID(),
    role,
    content,
    timestamp: new Date().toISOString()
  };

  messages.push(msg);
  saveChatHistory(messages);

  return msg;
}

export function resetChat() {
  messages = [];
  saveChatHistory(messages);
}

// ==================== NUEVA API: Manejo de conversaciones ====================
export function saveCurrentConversation(title = null) {
  return saveConversation(messages, title);
}

export function getAllConversations() {
  return loadConversations();
}

export function loadConversation(conversationId) {
  const conversation = loadConversationById(conversationId);
  if (conversation) {
    messages = conversation.messages;
    saveChatHistory(messages);
  }
  return conversation;
}

export function removeConversation(conversationId) {
  deleteConversation(conversationId);
}

export function clearAllConversations() {
  clearConversations();
}
