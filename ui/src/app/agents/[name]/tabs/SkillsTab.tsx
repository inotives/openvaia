"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Input,
  Modal,
  Popconfirm,
  Row,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  GlobalOutlined,
  LoadingOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { getSkillColor, getSkillIcon } from "../utils";

const { Text, Paragraph } = Typography;

interface SkillsTabProps {
  name: string;
  refreshKey: number;
  onCountChange?: (n: number) => void;
}

export default function SkillsTab({ name, refreshKey, onCountChange }: SkillsTabProps) {
  const [agentSkills, setAgentSkills] = useState<any[]>([]);
  const [allSkills, setAllSkills] = useState<any[]>([]);
  const [skillsLoading, setSkillsLoading] = useState(false);
  const [equipModalOpen, setEquipModalOpen] = useState(false);
  const [viewingSkill, setViewingSkill] = useState<any>(null);
  const [editingSkill, setEditingSkill] = useState(false);
  const [skillSaving, setSkillSaving] = useState(false);

  const fetchAgentSkills = useCallback(async () => {
    setSkillsLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/skills`);
      const data = await res.json();
      if (!data.error) {
        setAgentSkills(data);
        onCountChange?.(data.length);
      }
    } catch (err) {
      console.error("Failed to fetch agent skills:", err);
    } finally {
      setSkillsLoading(false);
    }
  }, [name, onCountChange]);

  const fetchAllSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills");
      const data = await res.json();
      if (Array.isArray(data)) setAllSkills(data);
    } catch {}
  }, []);

  // Fetch on mount
  useEffect(() => {
    fetchAgentSkills();
  }, [fetchAgentSkills, refreshKey]);

  return (
    <div>
      <div style={{ marginBottom: 16, textAlign: "right" }}>
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => { fetchAllSkills(); setEquipModalOpen(true); }}>
          Equip Skill
        </Button>
      </div>
      {skillsLoading ? (
        <div style={{ textAlign: "center", padding: 40 }}><LoadingOutlined /></div>
      ) : agentSkills.length === 0 ? (
        <Card size="small"><Text type="secondary">No skills equipped (global skills still apply)</Text></Card>
      ) : (
        <Row gutter={[12, 12]}>
          {agentSkills.map((skill: any) => (
            <Col key={skill.id} xs={24} sm={12} lg={8}>
              <Card
                size="small"
                hoverable
                onClick={() => setViewingSkill(skill)}
                style={{ height: "100%", cursor: "pointer" }}
                styles={{ body: { padding: "12px 16px", display: "flex", flexDirection: "column", height: "100%" } }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{
                        width: 36,
                        height: 36,
                        borderRadius: 8,
                        background: `${getSkillColor(skill)}20`,
                        border: `1px solid ${getSkillColor(skill)}40`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 18,
                        color: getSkillColor(skill),
                        flexShrink: 0,
                      }}>
                        {getSkillIcon(skill)}
                      </div>
                      <Text strong>{skill.name}</Text>
                    </div>
                    {skill.equipped ? (
                      <Popconfirm title="Unequip this skill?" onConfirm={async (e) => {
                        e?.stopPropagation();
                        await fetch(`/api/agents/${name}/skills`, {
                          method: "DELETE",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ skill_id: skill.id }),
                        });
                        fetchAgentSkills();
                      }}>
                        <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={e => e.stopPropagation()} />
                      </Popconfirm>
                    ) : null}
                  </div>
                  {skill.description && (
                    <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>{skill.description}</Text>
                  )}
                  <div>
                    {skill.global && <Tag color="blue" icon={<GlobalOutlined />}>Global</Tag>}
                    {skill.equipped && <Tag color="green">Equipped</Tag>}
                    {skill.tags?.map((t: string) => <Tag key={t} style={{ marginBottom: 4 }}>{t}</Tag>)}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 8, marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>Priority: {skill.priority}</Text>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* View/Edit Skill Modal */}
      <Modal
        title={viewingSkill?.name}
        open={!!viewingSkill}
        onCancel={() => { setViewingSkill(null); setEditingSkill(false); }}
        width={700}
        footer={editingSkill ? [
          <Button key="cancel" onClick={() => setEditingSkill(false)}>Cancel</Button>,
          <Button key="save" type="primary" loading={skillSaving} onClick={async () => {
            const contentEl = document.getElementById("skill-content-edit") as HTMLTextAreaElement;
            const descEl = document.getElementById("skill-desc-edit") as HTMLInputElement;
            const priorityEl = document.getElementById("skill-priority-edit") as HTMLInputElement;
            if (!contentEl) return;
            setSkillSaving(true);
            try {
              await fetch(`/api/skills/${viewingSkill.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  content: contentEl.value,
                  description: descEl?.value || viewingSkill.description,
                }),
              });
              if (viewingSkill.equipped && priorityEl) {
                const newPriority = parseInt(priorityEl.value, 10);
                if (!isNaN(newPriority) && newPriority !== viewingSkill.priority) {
                  await fetch(`/api/agents/${name}/skills`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ skill_id: viewingSkill.id, priority: newPriority }),
                  });
                }
              }
              fetchAgentSkills();
              setEditingSkill(false);
              setViewingSkill(null);
            } finally {
              setSkillSaving(false);
            }
          }}>Save</Button>,
        ] : [
          <Button key="edit" type="primary" icon={<EditOutlined />} onClick={() => setEditingSkill(true)}>Edit</Button>,
        ]}
      >
        {viewingSkill && !editingSkill && (
          <div>
            <div style={{ marginBottom: 12, display: "flex", gap: 4, flexWrap: "wrap" }}>
              {viewingSkill.global && <Tag color="blue" icon={<GlobalOutlined />}>Global</Tag>}
              {viewingSkill.equipped && <Tag color="green">Equipped</Tag>}
              {viewingSkill.tags?.map((t: string) => <Tag key={t}>{t}</Tag>)}
            </div>
            {viewingSkill.description && (
              <Paragraph type="secondary">{viewingSkill.description}</Paragraph>
            )}
            <Card
              size="small"
              styles={{ body: { padding: 16, fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" } }}
            >
              {viewingSkill.content}
            </Card>
          </div>
        )}
        {viewingSkill && editingSkill && (
          <div>
            <div style={{ marginBottom: 12 }}>
              <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Description</Text>
              <Input id="skill-desc-edit" defaultValue={viewingSkill.description} />
            </div>
            {viewingSkill.equipped && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Priority <Text type="secondary" style={{ fontSize: 11 }}>(lower = injected first in prompt)</Text></Text>
                <Input id="skill-priority-edit" type="number" defaultValue={viewingSkill.priority} style={{ width: 120 }} />
              </div>
            )}
            <div>
              <Text type="secondary" style={{ display: "block", marginBottom: 4 }}>Content (Markdown)</Text>
              <Input.TextArea
                id="skill-content-edit"
                defaultValue={viewingSkill.content}
                rows={16}
                style={{ fontFamily: "monospace", fontSize: 13 }}
              />
            </div>
          </div>
        )}
      </Modal>

      {/* Equip Skill Modal */}
      <Modal
        title="Equip Skill"
        open={equipModalOpen}
        onCancel={() => setEquipModalOpen(false)}
        footer={null}
      >
        <Table
          dataSource={allSkills.filter((s: any) => !s.global && !agentSkills.some((as: any) => as.id === s.id && as.equipped))}
          columns={[
            { title: "Name", dataIndex: "name" },
            { title: "Description", dataIndex: "description", ellipsis: true },
            {
              title: "",
              width: 80,
              render: (_: any, r: any) => (
                <Button
                  type="primary"
                  size="small"
                  onClick={async () => {
                    await fetch(`/api/agents/${name}/skills`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ skill_id: r.id, priority: 50 }),
                    });
                    fetchAgentSkills();
                    setEquipModalOpen(false);
                  }}
                >
                  Equip
                </Button>
              ),
            },
          ]}
          rowKey="id"
          pagination={false}
          size="small"
          locale={{ emptyText: "No available skills to equip" }}
        />
      </Modal>
    </div>
  );
}
