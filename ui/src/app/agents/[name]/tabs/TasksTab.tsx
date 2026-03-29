"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Card,
  DatePicker,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { STATUSES, PRIORITIES, STATUS_COLORS, STATUS_LABELS, PRIORITY_COLORS } from "@/lib/constants";
import type { Task } from "@/lib/types";

const { Text, Paragraph } = Typography;

interface TasksTabProps {
  name: string;
  tasks: Task[];
  tasksLoading: boolean;
  onFiltersChange: (filters: {
    status?: string;
    priority?: string;
    tag?: string;
    search?: string;
    dateRange?: [string, string] | null;
  }) => void;
  refreshKey: number;
}

export default function TasksTab({ name, tasks, tasksLoading, onFiltersChange, refreshKey }: TasksTabProps) {
  const [taskStatusFilter, setTaskStatusFilter] = useState<string | undefined>();
  const [taskPriorityFilter, setTaskPriorityFilter] = useState<string | undefined>();
  const [taskTagFilter, setTaskTagFilter] = useState<string | undefined>();
  const [taskSearch, setTaskSearch] = useState("");
  const [taskDateRange, setTaskDateRange] = useState<[string, string] | null>(null);

  // Notify parent of filter changes
  useEffect(() => {
    onFiltersChange({
      status: taskStatusFilter,
      priority: taskPriorityFilter,
      tag: taskTagFilter,
      search: taskSearch,
      dateRange: taskDateRange,
    });
  }, [taskStatusFilter, taskPriorityFilter, taskTagFilter, taskSearch, taskDateRange, onFiltersChange]);

  const allTaskTags = [...new Set(tasks.flatMap((t) => t.tags || []))].sort();

  const taskColumns = [
    {
      title: "Key",
      dataIndex: "key",
      key: "key",
      width: 100,
      render: (key: string) => <Text code style={{ fontSize: 12 }}>{key}</Text>,
    },
    {
      title: "Title",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 110,
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status]} style={{ margin: 0 }}>
          {STATUS_LABELS[status] || status}
        </Tag>
      ),
    },
    {
      title: "Priority",
      dataIndex: "priority",
      key: "priority",
      width: 90,
      render: (p: string) => (
        <Tag color={PRIORITY_COLORS[p]} style={{ margin: 0 }}>{p}</Tag>
      ),
    },
    {
      title: "Assigned",
      dataIndex: "assigned_to",
      key: "assigned_to",
      width: 90,
      render: (v: string | null) => v || "\u2014",
    },
    {
      title: "Created By",
      dataIndex: "created_by",
      key: "created_by",
      width: 90,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      width: 140,
      render: (d: string) => new Date(d).toLocaleString(),
      sorter: (a: Task, b: Task) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    },
    {
      title: "Updated",
      dataIndex: "updated_at",
      key: "updated_at",
      width: 140,
      render: (d: string) => new Date(d).toLocaleString(),
      sorter: (a: Task, b: Task) => new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime(),
      defaultSortOrder: "descend" as const,
    },
  ];

  return (
    <>
      <Card size="small" styles={{ body: { padding: "12px 16px" } }} style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select
            placeholder="Status"
            allowClear
            value={taskStatusFilter}
            onChange={setTaskStatusFilter}
            style={{ width: 140 }}
            options={STATUSES.map((s) => ({ value: s, label: STATUS_LABELS[s] }))}
          />
          <Select
            placeholder="Priority"
            allowClear
            value={taskPriorityFilter}
            onChange={setTaskPriorityFilter}
            style={{ width: 130 }}
            options={PRIORITIES.map((p) => ({ value: p, label: p }))}
          />
          <Select
            placeholder="Tag"
            allowClear
            value={taskTagFilter}
            onChange={setTaskTagFilter}
            style={{ width: 140 }}
            options={allTaskTags.map((t) => ({ value: t, label: t }))}
          />
          <DatePicker.RangePicker
            size="middle"
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setTaskDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setTaskDateRange(null);
              }
            }}
          />
          <Input.Search
            placeholder="Search tasks..."
            allowClear
            style={{ width: 200 }}
            onSearch={(v) => setTaskSearch(v)}
          />
        </Space>
      </Card>
      <Card size="small">
        <Table
          dataSource={tasks}
          columns={taskColumns}
          rowKey="key"
          size="small"
          loading={tasksLoading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          locale={{ emptyText: "No tasks" }}
          expandable={{
            expandedRowRender: (record: Task) => (
              <div style={{ padding: "8px 0" }}>
                {record.description && (
                  <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap" }}>{record.description}</Paragraph>
                )}
                {record.result && (
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ fontSize: 12 }}>Result:</Text>
                    <Paragraph style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>{record.result}</Paragraph>
                  </div>
                )}
                {record.tags?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {record.tags.map((t) => <Tag key={t} style={{ margin: "0 4px 4px 0" }}>{t}</Tag>)}
                  </div>
                )}
              </div>
            ),
            rowExpandable: (record: Task) => !!(record.description || record.result || record.tags?.length),
          }}
        />
      </Card>
    </>
  );
}
