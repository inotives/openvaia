"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Input,
  Popconfirm,
  Select,
  Tag,
  Typography,
  message,
} from "antd";
import { SaveOutlined, SettingOutlined, SyncOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface SettingsTabProps {
  name: string;
  refreshKey: number;
}

export default function SettingsTab({ name, refreshKey }: SettingsTabProps) {
  const [agentConfigs, setAgentConfigs] = useState<{ key: string; value: string; source: string; description: string; updated_at: string }[]>([]);
  const [configsLoading, setConfigsLoading] = useState(false);
  const [availableModels, setAvailableModels] = useState<{ id: string; provider: string; model: string; context_window: number; max_tokens: number }[]>([]);
  const [configSaving, setConfigSaving] = useState<string | null>(null);

  const fetchAgentConfigs = useCallback(async () => {
    setConfigsLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/configs`);
      const data = await res.json();
      if (!data.error) setAgentConfigs(data);
    } catch (err) {
      console.error("Failed to fetch agent configs:", err);
    } finally {
      setConfigsLoading(false);
    }
  }, [name]);

  const fetchModels = useCallback(async () => {
    try {
      const res = await fetch("/api/models");
      const data = await res.json();
      if (Array.isArray(data)) setAvailableModels(data);
    } catch {}
  }, []);

  const updateConfig = async (key: string, value: string) => {
    setConfigSaving(key);
    try {
      await fetch(`/api/agents/${name}/configs`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      fetchAgentConfigs();
      message.success(`Updated ${key}`);
    } catch {
      message.error(`Failed to update ${key}`);
    } finally {
      setConfigSaving(null);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchAgentConfigs();
    fetchModels();
  }, [fetchAgentConfigs, fetchModels, refreshKey]);

  return (
    <Card size="small" loading={configsLoading}>
      {agentConfigs.length === 0 ? (
        <div style={{ textAlign: "center", padding: 40 }}>
          <SettingOutlined style={{ fontSize: 32, opacity: 0.3 }} />
          <br />
          <Text type="secondary">No configs found. Deploy the agent to seed configs from agent.yml.</Text>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 600 }}>
          {agentConfigs.map((cfg) => {
            const isModel = cfg.key === "model";
            const isFallbacks = cfg.key === "fallbacks";
            const isMissionTags = cfg.key === "mission_tags";
            const isParallel = cfg.key === "parallel";

            return (
              <div key={cfg.key}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <Text strong>{cfg.key}</Text>
                  <Tag color={cfg.source === "ui" ? "blue" : "default"} style={{ fontSize: 10 }}>{cfg.source}</Tag>
                </div>
                {cfg.description && (
                  <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 6 }}>{cfg.description}</Text>
                )}

                {isModel ? (
                  <Select
                    style={{ width: "100%" }}
                    value={cfg.value}
                    onChange={(val) => updateConfig("model", val)}
                    loading={configSaving === "model"}
                    showSearch
                    optionFilterProp="label"
                    options={availableModels.map((m) => ({
                      value: m.id,
                      label: `${m.id} (${m.provider}, ${Math.round(m.context_window / 1000)}k ctx)`,
                    }))}
                  />
                ) : isFallbacks ? (
                  <Select
                    mode="multiple"
                    style={{ width: "100%" }}
                    value={(() => { try { return JSON.parse(cfg.value); } catch { return []; } })()}
                    onChange={(val) => updateConfig("fallbacks", JSON.stringify(val))}
                    loading={configSaving === "fallbacks"}
                    showSearch
                    optionFilterProp="label"
                    options={availableModels.map((m) => ({
                      value: m.id,
                      label: `${m.id} (${m.provider})`,
                    }))}
                  />
                ) : isMissionTags ? (
                  <Select
                    mode="tags"
                    style={{ width: "100%" }}
                    value={(() => { try { return JSON.parse(cfg.value); } catch { return []; } })()}
                    onChange={(val) => updateConfig("mission_tags", JSON.stringify(val))}
                    loading={configSaving === "mission_tags"}
                    placeholder="Add tags (press Enter)"
                  />
                ) : isParallel ? (
                  <Select
                    style={{ width: 120 }}
                    value={cfg.value}
                    onChange={(val) => updateConfig("parallel", val)}
                    loading={configSaving === "parallel"}
                    options={[
                      { value: "true", label: "Enabled" },
                      { value: "false", label: "Disabled" },
                    ]}
                  />
                ) : (
                  <Input
                    defaultValue={cfg.value}
                    onPressEnter={(e) => updateConfig(cfg.key, (e.target as HTMLInputElement).value)}
                    suffix={<SaveOutlined style={{ opacity: 0.3 }} />}
                  />
                )}

                <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: "block" }}>
                  Updated: {new Date(cfg.updated_at).toLocaleString()}
                </Text>
              </div>
            );
          })}

          <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12, marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Changes take effect on next agent restart. Source &quot;yaml&quot; = seeded from agent.yml, &quot;ui&quot; = changed from dashboard.
            </Text>
            <div style={{ marginTop: 12 }}>
              <Popconfirm
                title="Restart agent?"
                description={`This will restart ${name}'s container within 60 seconds.`}
                onConfirm={async () => {
                  try {
                    const res = await fetch(`/api/agents/${name}/restart`, { method: "POST" });
                    const data = await res.json();
                    if (res.ok) {
                      message.success(data.message || "Restart requested");
                    } else {
                      message.error(data.error || "Failed to request restart");
                    }
                  } catch {
                    message.error("Failed to request restart");
                  }
                }}
                okText="Restart"
                okButtonProps={{ danger: true }}
              >
                <Button icon={<SyncOutlined />} danger>Restart Agent</Button>
              </Popconfirm>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
