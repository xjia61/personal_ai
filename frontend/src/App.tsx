import { useEffect, useState } from "react";
import {
  getConversation,
  getConversations,
  sendMessage,
  type ConversationSummary,
  type Message,
  type RetentionMode,
} from "./api";

import "./App.css";

type LocalMessage = Pick<Message, "role" | "content">;

function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<RetentionMode>("save");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    refreshConversations();
  }, []);

  async function refreshConversations() {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (err) {
      console.error(err);
    }
  }

  async function openConversation(id: number) {
    try {
      const conversation = await getConversation(id);

      setConversationId(id);

      setMessages(
        conversation.messages.map((message) => ({
          role: message.role,
          content: message.content,
        }))
      );

      if (
        conversation.retention_type === "memory" ||
        conversation.retention_type === "save"
      ) {
        setMode(conversation.retention_type);
      }

      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load chat.");
    }
  }

  function newChat() {
    setConversationId(null);
    setMessages([]);
    setInput("");
    setMode("save");
    setError("");
  }

  async function handleSend() {
    const text = input.trim();

    if (!text || loading) {
      return;
    }

    setMessages((current) => [
      ...current,
      {
        role: "user",
        content: text,
      },
    ]);

    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await sendMessage(
        text,
        mode,
        conversationId ?? undefined
      );

      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
        },
      ]);

      if (response.conversation_id !== null) {
        setConversationId(response.conversation_id);
        await refreshConversations();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
    } finally {
      setLoading(false);
    }
  }

  const modeLocked = messages.length > 0;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Personal AI</h2>

          <button className="new-chat" onClick={newChat}>
            + New Chat
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={
                conversation.id === conversationId
                  ? "conversation active"
                  : "conversation"
              }
              onClick={() => openConversation(conversation.id)}
            >
              <span>{conversation.title}</span>

              {conversation.retention_type === "memory" && (
                <small>Remember</small>
              )}
            </button>
          ))}
        </div>
      </aside>

      <main className="chat">
        <header className="chat-header">
          <div>
            <h1>Personal AI</h1>
            <p>Your private AI workspace</p>
          </div>

          <select
            value={mode}
            disabled={modeLocked}
            onChange={(event) =>
              setMode(event.target.value as RetentionMode)
            }
          >
            <option value="ephemeral">Temporary</option>
            <option value="save">Save</option>
            <option value="memory">Remember</option>
          </select>
        </header>

        <section className="messages">
          {messages.length === 0 && (
            <div className="empty">
              <h2>What would you like to work on?</h2>

              <p>
                Choose Temporary, Save, or Remember before starting.
              </p>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`message ${message.role}`}
            >
              <div className="message-content">
                {message.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="message-content">Thinking…</div>
            </div>
          )}

          {error && <div className="error">{error}</div>}
        </section>

        <footer className="composer">
          <textarea
            value={input}
            placeholder="Message Personal AI..."
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />

          <button onClick={handleSend} disabled={loading}>
            Send
          </button>
        </footer>
      </main>
    </div>
  );
}

export default App;
