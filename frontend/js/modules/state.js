export const appState = {
  // Conversación / UI
  conversationId: null,
  conversationHistory: [],
  messages: [],

  // Modo
  currentMode: 'descubre', // descubre | aprende | busqueda_web
  modeActivatedManually: false,
  isLoadedFromHistory: false,

  // Task flow
  pendingTask: null
};

export const userState = {
  messageCount: 0,
  isPremium: false
};

// =========================================================
// TASK STORE (source of truth para taskManager.js)
// =========================================================
// Nota: usamos "let" para permitir setTaskStore(reasignación).
export let taskStore = [];

export function setTaskStore(newStore) {
  taskStore = Array.isArray(newStore) ? newStore : [];
  return taskStore;
}

export function addTask(task) {
  if (!task) return taskStore;
  const signature = getTaskSignature(task);
  const existingIndex = taskStore.findIndex((t) => {
    if (task.id && t?.id === task.id) return true;
    if (!task.id && t && getTaskSignature(t) === signature) return true;
    return t?._sig && t._sig === signature;
  });

  if (existingIndex >= 0) {
    taskStore[existingIndex] = { ...taskStore[existingIndex], ...task, _sig: signature };
    return taskStore;
  }

  taskStore.push({ ...task, _sig: signature });
  return taskStore;
}

function getTaskSignature(task) {
  const type = task?.type || '';
  const content = task?.content || '';
  const fecha = task?.fecha || '';
  const hora = task?.hora || '';
  const meetingType = task?.meeting_type || '';
  const location = task?.location || '';
  return `${type}|${content}|${fecha}|${hora}|${meetingType}|${location}`.toLowerCase();
}

export function removeTask(taskId) {
  if (!taskId) return taskStore;
  taskStore = taskStore.filter(t => t?.id !== taskId);
  return taskStore;
}
