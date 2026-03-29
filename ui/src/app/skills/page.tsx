"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Drawer,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
} from "antd";
import {
  BulbOutlined,
  CodeOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  GlobalOutlined,
  MessageOutlined,
  PlusOutlined,
  ReloadOutlined,
  RobotOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { Skill } from "@/lib/types";

const { Title, Text, Paragraph } = Typography;

const SKILL_ICON_MAP: Record<string, React.ReactNode> = {
  code: <CodeOutlined />, coding: <CodeOutlined />, dev: <CodeOutlined />,
  search: <SearchOutlined />, research: <FileSearchOutlined />,
  browse: <GlobalOutlined />, browser: <GlobalOutlined />, web: <GlobalOutlined />,
  chat: <MessageOutlined />, message: <MessageOutlined />, discord: <MessageOutlined />,
  data: <DatabaseOutlined />, database: <DatabaseOutlined />, memory: <DatabaseOutlined />,
  deploy: <CloudServerOutlined />, server: <CloudServerOutlined />, api: <CloudServerOutlined />,
  write: <EditOutlined />, report: <FileTextOutlined />, doc: <FileTextOutlined />,
  think: <BulbOutlined />, plan: <BulbOutlined />,
  analyze: <ExperimentOutlined />, test: <ExperimentOutlined />,
  auto: <RobotOutlined />, agent: <RobotOutlined />,
  tool: <ToolOutlined />, shell: <ToolOutlined />,
};

const SKILL_COLORS = ["#1677ff", "#36cfc9", "#9254de", "#f5222d", "#fa8c16", "#52c41a", "#eb2f96", "#faad14"];

function getSkillIcon(skill: { name: string; tags?: string[]; description?: string }): React.ReactNode {
  const text = `${skill.name} ${(skill.tags || []).join(" ")} ${skill.description || ""}`.toLowerCase();
  for (const [keyword, icon] of Object.entries(SKILL_ICON_MAP)) {
    if (text.includes(keyword)) return icon;
  }
  return <ThunderboltOutlined />;
}

function getSkillColor(skill: { name: string }): string {
  let hash = 0;
  for (let i = 0; i < skill.name.length; i++) hash = skill.name.charCodeAt(i) + ((hash << 5) - hash);
  return SKILL_COLORS[Math.abs(hash) % SKILL_COLORS.length];
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Skill | null>(null);
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [viewing, setViewing] = useState<Skill | null>(null);

  const fetchSkills = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/skills");
      const data = await res.json();
      setSkills(Array.isArray(data) ? data : []);
    } catch {
      setSkills([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ global: false, enabled: true });
    setModalOpen(true);
  };

  const openEdit = (skill: Skill) => {
    setEditing(skill);
    form.setFieldsValue({
      name: skill.name,
      description: skill.description,
      content: skill.content,
      tags: skill.tags,
      global: skill.global,
      enabled: skill.enabled,
    });
    setModalOpen(true);
  };

  const handleSave = async (values: any) => {
    setSaving(true);
    try {
      const url = editing ? `/api/skills/${editing.id}` : "/api/skills";
      const method = editing ? "PATCH" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (res.ok) {
        setModalOpen(false);
        form.resetFields();
        setEditing(null);
        fetchSkills();
      }
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    await fetch(`/api/skills/${id}`, { method: "DELETE" });
    fetchSkills();
  };

  const handleToggleEnabled = async (skill: Skill) => {
    await fetch(`/api/skills/${skill.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !skill.enabled }),
    });
    fetchSkills();
  };

  const allTags = Array.from(new Set(skills.flatMap((s) => s.tags || []))).sort();

  const filteredSkills = skills.filter((skill) => {
    const q = search.toLowerCase();
    const matchesSearch = !q || skill.name.toLowerCase().includes(q) || (skill.description || "").toLowerCase().includes(q);
    const matchesTag = !selectedTag || (skill.tags || []).includes(selectedTag);
    const matchesStatus = !statusFilter || (skill.status || "active") === statusFilter;
    return matchesSearch && matchesTag && matchesStatus;
  });

  const STATUS_BADGE: Record<string, { color: string; label: string }> = {
    draft: { color: "orange", label: "Draft" },
    active: { color: "green", label: "Active" },
    rejected: { color: "red", label: "Rejected" },
    inactive: { color: "default", label: "Inactive" },
  };

  const handleStatusChange = async (id: number, status: string) => {
    try {
      const res = await fetch(`/api/skills/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("Failed");
      fetchSkills();
    } catch {
      // error handled silently
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Skills</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchSkills} />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Add Skill
          </Button>
        </Space>
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
        <Input
          placeholder="Search skills..."
          prefix={<SearchOutlined />}
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 260 }}
        />
        <Select
          placeholder="Filter by tag"
          allowClear
          value={selectedTag}
          onChange={(v) => setSelectedTag(v || null)}
          style={{ width: 180 }}
          options={allTags.map((t) => ({ label: t, value: t }))}
        />
        <Select
          placeholder="Filter by status"
          allowClear
          value={statusFilter}
          onChange={(v) => setStatusFilter(v || null)}
          style={{ width: 140 }}
          options={[
            { label: "Draft", value: "draft" },
            { label: "Active", value: "active" },
            { label: "Rejected", value: "rejected" },
            { label: "Inactive", value: "inactive" },
          ]}
        />
        {(search || selectedTag) && (
          <Text type="secondary" style={{ lineHeight: "32px" }}>
            {filteredSkills.length} of {skills.length} skills
          </Text>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 60 }}><Spin /></div>
      ) : (
        <Row gutter={[16, 16]}>
          {filteredSkills.map((skill) => (
            <Col key={skill.id} xs={24} sm={12} lg={8} xl={6}>
              <Card
                hoverable
                onClick={() => setViewing(skill)}
                style={{ height: "100%", opacity: skill.enabled ? 1 : 0.5 }}
                styles={{ body: { padding: "16px 20px", display: "flex", flexDirection: "column", height: "100%" } }}
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
                      <Text strong style={{ fontSize: 15 }}>{skill.name}</Text>
                    </div>
                    <Space size={4} onClick={(e) => e.stopPropagation()}>
                      <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openEdit(skill)} />
                      <Popconfirm title="Delete this skill?" onConfirm={() => handleDelete(skill.id)}>
                        <Button type="text" danger size="small" icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </Space>
                  </div>

                  {skill.description && (
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2 }}
                      style={{ marginBottom: 12, fontSize: 13 }}
                    >
                      {skill.description}
                    </Paragraph>
                  )}

                  <div style={{ marginBottom: 12 }}>
                    {(skill.status && skill.status !== "active") && (
                      <Tag color={STATUS_BADGE[skill.status]?.color || "default"} style={{ marginBottom: 4 }}>
                        {STATUS_BADGE[skill.status]?.label || skill.status}
                      </Tag>
                    )}
                    {skill.global ? (
                      <Tag color="blue" icon={<GlobalOutlined />}>Global</Tag>
                    ) : (
                      <Tag icon={<UserOutlined />}>{skill.agent_count || 0} agent{(skill.agent_count || 0) !== 1 ? "s" : ""}</Tag>
                    )}
                    {skill.tags?.map((t) => (
                      <Tag key={t} style={{ marginBottom: 4 }}>{t}</Tag>
                    ))}
                    {skill.created_by && (
                      <Tag color="purple" style={{ marginBottom: 4 }}>by {skill.created_by}</Tag>
                    )}
                  </div>
                  {skill.status === "draft" && (
                    <Space size={4} style={{ marginBottom: 8 }} onClick={(e) => e.stopPropagation()}>
                      <Button size="small" type="primary" onClick={() => handleStatusChange(skill.id, "active")}>
                        Approve
                      </Button>
                      <Button size="small" danger onClick={() => handleStatusChange(skill.id, "rejected")}>
                        Reject
                      </Button>
                    </Space>
                  )}
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 10 }} onClick={(e) => e.stopPropagation()}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(skill.updated_at).toLocaleDateString()}
                  </Text>
                  <Switch
                    size="small"
                    checked={skill.enabled}
                    onChange={() => handleToggleEnabled(skill)}
                  />
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* Create / Edit Modal */}
      <Modal
        title={editing ? "Edit Skill" : "Add Skill"}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditing(null); }}
        onOk={() => form.submit()}
        confirmLoading={saving}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g. task_workflow" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input placeholder="One-line description of what this skill does" />
          </Form.Item>
          <Form.Item name="content" label="Content (Markdown)" rules={[{ required: true }]}>
            <Input.TextArea rows={16} placeholder="Skill instructions in markdown..." style={{ fontFamily: "monospace", fontSize: 13 }} />
          </Form.Item>
          <Form.Item name="tags" label="Tags">
            <Select mode="tags" placeholder="Add tags" />
          </Form.Item>
          <Space>
            <Form.Item name="global" label="Global" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="enabled" label="Enabled" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>

      {/* View Drawer */}
      <Drawer
        title={viewing?.name}
        open={!!viewing}
        onClose={() => setViewing(null)}
        width={600}
        extra={
          viewing && (
            <Button type="primary" size="small" icon={<EditOutlined />} onClick={() => { setViewing(null); openEdit(viewing); }}>
              Edit
            </Button>
          )
        }
      >
        {viewing && (
          <div>
            <Space style={{ marginBottom: 16 }}>
              {viewing.global ? <Tag color="blue" icon={<GlobalOutlined />}>Global</Tag> : <Tag icon={<UserOutlined />}>{viewing.agent_count || 0} agents</Tag>}
              {viewing.enabled ? <Tag color="green">Enabled</Tag> : <Tag color="red">Disabled</Tag>}
              {viewing.tags?.map((t) => <Tag key={t}>{t}</Tag>)}
            </Space>
            {viewing.description && (
              <Paragraph type="secondary">{viewing.description}</Paragraph>
            )}
            <Card
              size="small"
              styles={{ body: { padding: 16, fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap" } }}
            >
              {viewing.content}
            </Card>
            <div style={{ marginTop: 16 }}>
              <Text type="secondary">
                Updated: {new Date(viewing.updated_at).toLocaleString()}
              </Text>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
