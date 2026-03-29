"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, Card, Input, Space, Tag, Typography, message } from "antd";
import { LoadingOutlined, PlusOutlined, SendOutlined } from "@ant-design/icons";
import { timeAgo } from "../utils";

const { Text } = Typography;

interface ChatTabProps {
  name: string;
  refreshKey: number;
}

export default function ChatTab({ name, refreshKey }: ChatTabProps) {
  const [chatSession, setChatSession] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(`chat-session-${name}`) || Date.now().toString(36);
    }
    return Date.now().toString(36);
  });
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string; created_at: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatPending, setChatPending] = useState(false);
  const [agentBusy, setAgentBusy] = useState(false);
  const [chatWaiting, setChatWaiting] = useState(false);
  const chatEndRef = React.useRef<HTMLDivElement>(null);

  // Persist session to localStorage
  useEffect(() => {
    localStorage.setItem(`chat-session-${name}`, chatSession);
  }, [chatSession, name]);

  const fetchChat = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/chat?session=${chatSession}`);
      const data = await res.json();
      if (!data.error) {
        const msgs = data.messages ?? [];
        setChatMessages(msgs);
        setChatPending(data.has_pending ?? false);
        setAgentBusy(data.is_busy ?? false);
        const lastMsg = msgs[msgs.length - 1];
        setChatWaiting(lastMsg?.role === "user");
      }
    } catch (err) {
      console.error("Failed to fetch chat:", err);
    }
  }, [name, chatSession]);

  // Fetch on mount
  useEffect(() => {
    fetchChat();
  }, [fetchChat, refreshKey]);

  // Poll while waiting for agent response
  useEffect(() => {
    if (!chatWaiting) return;
    const interval = setInterval(fetchChat, 1500);
    return () => clearInterval(interval);
  }, [chatWaiting, fetchChat]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const startNewChat = () => {
    const newSession = Date.now().toString(36);
    setChatSession(newSession);
    setChatMessages([]);
    setChatWaiting(false);
    setChatPending(false);
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text) return;
    setChatSending(true);
    setChatInput("");
    try {
      const res = await fetch(`/api/agents/${name}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session: chatSession }),
      });
      const data = await res.json();
      if (!res.ok) {
        message.error(data.error || "Failed to send");
        return;
      }
      setChatPending(true);
      setChatWaiting(true);
      fetchChat();
    } catch {
      message.error("Failed to send message");
    } finally {
      setChatSending(false);
    }
  };

  return (
    <Card
      size="small"
      extra={
        <Space>
          {chatWaiting && (
            <Tag icon={<LoadingOutlined spin />} color="processing">
              Waiting for response...
            </Tag>
          )}
          {agentBusy && !chatWaiting && (
            <Tag color="orange">Agent busy</Tag>
          )}
          <Button size="small" icon={<PlusOutlined />} onClick={startNewChat}>
            New Chat
          </Button>
        </Space>
      }
    >
      {/* Messages area */}
      <div style={{
        height: 400,
        overflowY: "auto",
        marginBottom: 12,
        padding: "8px 4px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
      }}>
        {chatMessages.length === 0 && (
          <div style={{ textAlign: "center", padding: 40 }}>
            <Text type="secondary">Send a message to start chatting with {name}</Text>
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              marginBottom: 8,
            }}
          >
            <div style={{
              maxWidth: "70%",
              padding: "8px 12px",
              borderRadius: 8,
              background: m.role === "user"
                ? "rgba(22, 119, 255, 0.15)"
                : "rgba(255, 255, 255, 0.06)",
              border: `1px solid ${m.role === "user" ? "rgba(22, 119, 255, 0.3)" : "rgba(255, 255, 255, 0.1)"}`,
            }}>
              <div style={{ fontSize: 11, marginBottom: 4, opacity: 0.5 }}>
                {m.role === "user" ? "You" : name} · {timeAgo(m.created_at)}
              </div>
              <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 13 }}>
                {m.content}
              </div>
            </div>
          </div>
        ))}
        {chatWaiting && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 8 }}>
            <div style={{
              padding: "8px 16px",
              borderRadius: 8,
              background: "rgba(255, 255, 255, 0.06)",
              border: "1px solid rgba(255, 255, 255, 0.1)",
            }}>
              <LoadingOutlined spin /> <Text type="secondary" style={{ fontSize: 12 }}>{name} is thinking...</Text>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input area */}
      <div style={{ display: "flex", gap: 8 }}>
        <Input.TextArea
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          placeholder={agentBusy ? `${name} is busy, message will queue...` : `Message ${name}...`}
          autoSize={{ minRows: 1, maxRows: 4 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              sendChat();
            }
          }}
          style={{ flex: 1 }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={sendChat}
          loading={chatSending}
          disabled={!chatInput.trim()}
        >
          Send
        </Button>
      </div>
    </Card>
  );
}
