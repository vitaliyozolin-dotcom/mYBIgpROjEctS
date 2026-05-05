import api from "./client.js";

export async function askAI(messages, context = null, system = null) {
  const { data } = await api.post("/ai/chat", { messages, context, system });
  return data.content;
}
