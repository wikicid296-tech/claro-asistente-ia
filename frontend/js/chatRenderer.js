import { getMessages } from "./chatState.js";

export function renderChat(container) {
  container.innerHTML = "";

  getMessages().forEach(msg => {
    const el = document.createElement("div");
    el.className = `msg ${msg.role}`;
    el.textContent = msg.content;
    container.appendChild(el);
  });
}
