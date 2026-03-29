"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Input,
  Select,
  Space,
  Typography,
  message,
  Tooltip,
} from "antd";
import {
  CopyOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

interface ModelOption {
  id: string;
  provider: string;
}

export default function PromptGenPage() {
  const [instruction, setInstruction] = useState("");
  const [enhanced, setEnhanced] = useState("");
  const [models, setModels] = useState<ModelOption[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>("nvidia-minimax-2.5");
  const [modelUsed, setModelUsed] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      if (!data.error) setModels(data);
    } catch (err) {
      console.error("Failed to fetch models:", err);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  const handleEnhance = async () => {
    if (!instruction.trim()) {
      message.warning("Enter an instruction first");
      return;
    }

    setLoading(true);
    setEnhanced("");
    setModelUsed("");

    try {
      const res = await fetch("/api/prompt-gen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: instruction.trim(),
          model: selectedModel,
        }),
      });

      const data = await res.json();
      if (data.error) {
        message.error(data.error);
      } else {
        setEnhanced(data.enhanced_prompt);
        setModelUsed(data.model_used);
      }
    } catch (err) {
      console.error("Prompt gen error:", err);
      message.error("Failed to enhance prompt");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(enhanced);
    message.success("Copied to clipboard");
  };

  return (
    <div>
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between" }}>
        <Title level={3} style={{ margin: 0 }}>
          Prompt Generator
        </Title>
      </Space>

      <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
        Turn rough instructions into structured prompts optimized for your agents.
      </Text>

      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Your instruction</Text>
          <Input.TextArea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={4}
            placeholder="e.g. look into Solana DeFi protocols and find the best yield opportunities"
            style={{ fontFamily: "monospace", fontSize: 13 }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                handleEnhance();
              }
            }}
          />
        </div>

        <Space>
          <Select
            placeholder="Model (auto)"
            allowClear
            value={selectedModel}
            onChange={(v) => setSelectedModel(v || null)}
            style={{ width: 220 }}
            options={models.map((m) => ({
              label: `${m.id} (${m.provider})`,
              value: m.id,
            }))}
          />
          <Button
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleEnhance}
            loading={loading}
          >
            Enhance
          </Button>
        </Space>
      </Card>

      {enhanced && (
        <Card
          size="small"
          title={
            <Space>
              <Text strong>Enhanced Prompt</Text>
              {modelUsed && <Text type="secondary" style={{ fontSize: 12 }}>via {modelUsed}</Text>}
            </Space>
          }
          extra={
            <Tooltip title="Copy to clipboard">
              <Button icon={<CopyOutlined />} size="small" onClick={handleCopy}>
                Copy
              </Button>
            </Tooltip>
          }
        >
          <div
            style={{
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              fontSize: 13,
              lineHeight: 1.6,
              maxHeight: 400,
              overflow: "auto",
            }}
          >
            {enhanced}
          </div>
        </Card>
      )}
    </div>
  );
}
