"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import type { Task } from "@/lib/types";
import {
  STATUSES,
  PRIORITIES,
  STATUS_LABELS,
  STATUS_COLORS,
  PRIORITY_COLORS,
} from "@/lib/constants";

const { Title, Text, Paragraph } = Typography;

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [agents, setAgents] = useState<string[]>([]);

  // Filters
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [filterAssigned, setFilterAssigned] = useState<string | undefined>();
  const [filterPriority, setFilterPriority] = useState<string | undefined>();
  const [filterSearch, setFilterSearch] = useState("");
  const [filterDateRange, setFilterDateRange] = useState<[string, string] | null>(null);
  const [filterCreatedBy, setFilterCreatedBy] = useState<string | undefined>();
  const [filterTag, setFilterTag] = useState<string | undefined>();

  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  // Detail drawer
  const [selected, setSelected] = useState<Task | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm] = Form.useForm();
  const [editSaving, setEditSaving] = useState(false);

  const fetchTasks = useCallback(async () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (filterStatus) params.set("status", filterStatus);
    if (filterAssigned) params.set("assigned_to", filterAssigned);
    if (filterPriority) params.set("priority", filterPriority);
    if (filterCreatedBy) params.set("created_by", filterCreatedBy);
    if (filterSearch.trim()) params.set("q", filterSearch.trim());
    if (filterTag) params.set("tag", filterTag);
    if (filterDateRange) {
      params.set("from", filterDateRange[0]);
      params.set("to", filterDateRange[1]);
    }
    try {
      const res = await fetch(`/api/tasks?${params}`);
      const data = await res.json();
      setTasks(Array.isArray(data) ? data : []);
    } catch {
      setTasks([]);
    }
    setLoading(false);
  }, [filterStatus, filterAssigned, filterPriority, filterCreatedBy, filterSearch, filterTag, filterDateRange]);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await fetch("/api/dashboard/agents");
      const data = await res.json();
      setAgents(data.map((a: any) => a.name));
    } catch {
      setAgents([]);
    }
  }, []);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleCreate = async (values: any) => {
    setCreating(true);
    try {
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...values,
          tags: values.tags || [],
        }),
      });
      if (res.ok) {
        setCreateOpen(false);
        createForm.resetFields();
        fetchTasks();
      }
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async (key: string, status: string) => {
    await fetch(`/api/tasks/${key}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    fetchTasks();
    if (selected?.key === key) {
      setSelected((prev) => (prev ? { ...prev, status } : null));
    }
  };

  const handleAssignChange = async (key: string, assigned_to: string | null) => {
    await fetch(`/api/tasks/${key}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assigned_to }),
    });
    fetchTasks();
  };

  const openEdit = () => {
    if (!selected) return;
    editForm.setFieldsValue({
      title: selected.title,
      description: selected.description || "",
      priority: selected.priority,
      assigned_to: selected.assigned_to || "",
      tags: selected.tags || [],
    });
    setEditing(true);
  };

  const handleEditSave = async () => {
    if (!selected) return;
    try {
      const values = await editForm.validateFields();
      setEditSaving(true);
      const res = await fetch(`/api/tasks/${selected.key}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...values,
          assigned_to: values.assigned_to || null,
        }),
      });
      if (!res.ok) throw new Error("Update failed");
      const updated = await res.json();
      setSelected({ ...selected, ...updated });
      setEditing(false);
      message.success("Task updated");
      fetchTasks();
    } catch (err: any) {
      message.error(err?.message || "Failed to update task");
    } finally {
      setEditSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    Modal.confirm({
      title: `Delete task ${key}?`,
      content: "This action cannot be undone.",
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        await fetch(`/api/tasks/${key}`, { method: "DELETE" });
        if (selected?.key === key) setSelected(null);
        fetchTasks();
      },
    });
  };

  const columns = [
    {
      title: "Key",
      dataIndex: "key",
      width: 100,
      render: (key: string) => (
        <Text code style={{ cursor: "pointer" }} onClick={() => setSelected(tasks.find((t) => t.key === key) || null)}>
          {key}
        </Text>
      ),
    },
    {
      title: "Title",
      dataIndex: "title",
      ellipsis: true,
      render: (title: string, record: Task) => (
        <Space size={4}>
          <a onClick={() => setSelected(record)}>{title}</a>
          {record.recurrence_minutes && (
            <Tag color="cyan" style={{ margin: 0, fontSize: 10 }}>
              {record.recurrence_minutes >= 1440 ? `${Math.round(record.recurrence_minutes / 1440)}d` : record.recurrence_minutes >= 60 ? `${Math.round(record.recurrence_minutes / 60)}h` : `${record.recurrence_minutes}m`}
              {record.recurrence_count > 0 && ` #${record.recurrence_count}`}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      width: 130,
      render: (status: string, record: Task) => (
        <Select
          size="small"
          value={status}
          onChange={(val) => handleStatusChange(record.key, val)}
          style={{ width: 120 }}
          options={STATUSES.map((s) => ({
            value: s,
            label: (
              <Tag color={STATUS_COLORS[s]} style={{ margin: 0 }}>
                {STATUS_LABELS[s]}
              </Tag>
            ),
          }))}
        />
      ),
    },
    {
      title: "Priority",
      dataIndex: "priority",
      width: 90,
      render: (p: string) => (
        <Tag color={PRIORITY_COLORS[p]}>{p}</Tag>
      ),
    },
    {
      title: "Assigned To",
      dataIndex: "assigned_to",
      width: 140,
      render: (assignee: string | null, record: Task) => (
        <Select
          size="small"
          value={assignee || undefined}
          placeholder="Unassigned"
          allowClear
          onChange={(val) => handleAssignChange(record.key, val || null)}
          style={{ width: 130 }}
          options={agents.map((a) => ({ value: a, label: a }))}
        />
      ),
    },
    {
      title: "Created By",
      dataIndex: "created_by",
      width: 110,
    },
    {
      title: "Tags",
      dataIndex: "tags",
      width: 160,
      render: (tags: string[]) =>
        tags?.map((t) => (
          <Tag key={t} style={{ marginBottom: 2 }}>
            {t}
          </Tag>
        )),
    },
    {
      title: "Created",
      dataIndex: "created_at",
      width: 160,
      render: (d: string) => new Date(d).toLocaleString(),
      sorter: (a: Task, b: Task) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: "Updated",
      dataIndex: "updated_at",
      width: 160,
      render: (d: string) => new Date(d).toLocaleString(),
      sorter: (a: Task, b: Task) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      defaultSortOrder: "descend" as const,
    },
    {
      title: "",
      width: 50,
      render: (_: any, record: Task) => (
        <Button
          type="text"
          danger
          size="small"
          icon={<DeleteOutlined />}
          onClick={(e) => {
            e.stopPropagation();
            handleDelete(record.key);
          }}
        />
      ),
    },
  ];

  // Collect all unique tags from current tasks for filter dropdown
  const allTags = [...new Set(tasks.flatMap((t) => t.tags || []))].sort();

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>
          Tasks
        </Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchTasks} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            Create Task
          </Button>
        </Space>
      </div>

      <Card styles={{ body: { padding: "12px 16px" } }} style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select
            placeholder="Status"
            allowClear
            value={filterStatus}
            onChange={setFilterStatus}
            style={{ width: 140 }}
            options={STATUSES.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
          />
          <Select
            placeholder="Assigned To"
            allowClear
            value={filterAssigned}
            onChange={setFilterAssigned}
            style={{ width: 150 }}
            options={[
              { value: "unassigned", label: "Unassigned" },
              ...agents.map((a) => ({ value: a, label: a })),
            ]}
          />
          <Select
            placeholder="Priority"
            allowClear
            value={filterPriority}
            onChange={setFilterPriority}
            style={{ width: 130 }}
            options={PRIORITIES.map((p) => ({ value: p, label: p }))}
          />
          <Select
            placeholder="Created By"
            allowClear
            value={filterCreatedBy}
            onChange={setFilterCreatedBy}
            style={{ width: 140 }}
            options={[
              { value: "boss", label: "boss" },
              ...agents.map((a) => ({ value: a, label: a })),
            ]}
          />
          <Select
            placeholder="Tag"
            allowClear
            value={filterTag}
            onChange={setFilterTag}
            style={{ width: 140 }}
            options={allTags.map((t) => ({ value: t, label: t }))}
          />
          <DatePicker.RangePicker
            size="middle"
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setFilterDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setFilterDateRange(null);
              }
            }}
          />
          <Input.Search
            placeholder="Search tasks..."
            allowClear
            style={{ width: 200 }}
            onSearch={(v) => setFilterSearch(v)}
          />
        </Space>
      </Card>

      <Card styles={{ body: { padding: 0 } }}>
        <Table
          dataSource={tasks}
          columns={columns}
          rowKey="key"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `${t} tasks` }}
        />
      </Card>

      {/* Create Task Modal */}
      <Modal
        title="Create Task"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => createForm.submit()}
        confirmLoading={creating}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="title" label="Title" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="priority" label="Priority" initialValue="medium">
            <Select options={PRIORITIES.map((p) => ({ value: p, label: p }))} />
          </Form.Item>
          <Form.Item name="created_by" label="Created By" rules={[{ required: true }]}>
            <Select
              placeholder="Who is creating this task?"
              options={[
                { value: "boss", label: "boss (human)" },
                ...agents.map((a) => ({ value: a, label: a })),
              ]}
            />
          </Form.Item>
          <Form.Item name="assigned_to" label="Assign To">
            <Select
              placeholder="Leave empty for mission board"
              allowClear
              options={agents.map((a) => ({ value: a, label: a }))}
            />
          </Form.Item>
          <Form.Item name="tags" label="Tags">
            <Select mode="tags" placeholder="Add tags (press Enter)" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Task Detail Drawer */}
      <Drawer
        title={selected?.key}
        open={!!selected}
        onClose={() => { setSelected(null); setEditing(false); }}
        width={500}
        extra={
          selected && !editing && (
            <Button icon={<EditOutlined />} onClick={openEdit}>Edit</Button>
          )
        }
      >
        {selected && editing ? (
          <Form form={editForm} layout="vertical" style={{ marginTop: 8 }}>
            <Form.Item label="Title" name="title" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item label="Description" name="description">
              <Input.TextArea rows={4} />
            </Form.Item>
            <Form.Item label="Priority" name="priority">
              <Select options={PRIORITIES.map((p) => ({ label: p, value: p }))} />
            </Form.Item>
            <Form.Item label="Assigned To" name="assigned_to">
              <Input placeholder="Agent name (leave empty for mission board)" />
            </Form.Item>
            <Form.Item label="Tags" name="tags">
              <Select mode="tags" placeholder="Add tags (press Enter)" />
            </Form.Item>
            <Space>
              <Button type="primary" onClick={handleEditSave} loading={editSaving}>Save</Button>
              <Button onClick={() => setEditing(false)}>Cancel</Button>
            </Space>
          </Form>
        ) : selected && (
          <div>
            <Title level={4}>{selected.title}</Title>
            <Space style={{ marginBottom: 16 }}>
              <Tag color={STATUS_COLORS[selected.status]}>{STATUS_LABELS[selected.status]}</Tag>
              <Tag color={PRIORITY_COLORS[selected.priority]}>{selected.priority}</Tag>
            </Space>

            {selected.description && (
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">Description</Text>
                <Paragraph>{selected.description}</Paragraph>
              </div>
            )}

            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Assigned To: </Text>
              <Text>{selected.assigned_to || "Unassigned (Mission Board)"}</Text>
            </div>

            <div style={{ marginBottom: 12 }}>
              <Text type="secondary">Created By: </Text>
              <Text>{selected.created_by}</Text>
            </div>

            {selected.tags?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">Tags: </Text>
                {selected.tags.map((t) => (
                  <Tag key={t}>{t}</Tag>
                ))}
              </div>
            )}

            {selected.result && (
              <div style={{ marginBottom: 12 }}>
                <Text type="secondary">Result</Text>
                <Card size="small" styles={{ body: { padding: 12, whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 13, maxHeight: 300, overflow: "auto" } }}>
                  {selected.result}
                </Card>
              </div>
            )}

            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">Created: </Text>
              <Text>{new Date(selected.created_at).toLocaleString()}</Text>
            </div>
            <div>
              <Text type="secondary">Updated: </Text>
              <Text>{new Date(selected.updated_at).toLocaleString()}</Text>
            </div>

            <div style={{ marginTop: 24 }}>
              <Text type="secondary">Change Status</Text>
              <div style={{ marginTop: 8 }}>
                <Space wrap>
                  {STATUSES.map((s) => (
                    <Button
                      key={s}
                      size="small"
                      type={selected.status === s ? "primary" : "default"}
                      onClick={() => handleStatusChange(selected.key, s)}
                    >
                      {STATUS_LABELS[s]}
                    </Button>
                  ))}
                </Space>
              </div>
            </div>

            <div style={{ marginTop: 32, borderTop: "1px solid #f0f0f0", paddingTop: 16 }}>
              <Button
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(selected.key)}
              >
                Delete Task
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
