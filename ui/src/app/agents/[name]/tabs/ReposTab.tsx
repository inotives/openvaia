"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Space,
  Table,
  Typography,
  message,
} from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined } from "@ant-design/icons";
import type { Repo } from "../utils";

const { Text } = Typography;

interface ReposTabProps {
  name: string;
  refreshKey: number;
  onCountChange?: (n: number) => void;
  onMutate?: () => void;
}

export default function ReposTab({ name, refreshKey, onCountChange, onMutate }: ReposTabProps) {
  const [repos, setRepos] = useState<Repo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [repoModalOpen, setRepoModalOpen] = useState(false);
  const [repoSaving, setRepoSaving] = useState(false);
  const [editingRepo, setEditingRepo] = useState<Repo | null>(null);
  const [repoForm] = Form.useForm();

  const fetchRepos = useCallback(async () => {
    setReposLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/repos`);
      const data = await res.json();
      if (!data.error) {
        setRepos(data);
        onCountChange?.(data.length);
      }
    } catch (err) {
      console.error("Failed to fetch repos:", err);
    } finally {
      setReposLoading(false);
    }
  }, [name, onCountChange]);

  // Fetch on mount
  useEffect(() => {
    fetchRepos();
  }, [fetchRepos, refreshKey]);

  const openAddRepo = () => {
    setEditingRepo(null);
    repoForm.resetFields();
    setRepoModalOpen(true);
  };

  const openEditRepo = (repo: Repo) => {
    setEditingRepo(repo);
    repoForm.setFieldsValue({
      repo_url: repo.repo_url,
      repo_name: repo.repo_name,
      assigned_by: repo.assigned_by || "",
    });
    setRepoModalOpen(true);
  };

  const handleRepoSave = async () => {
    try {
      const values = await repoForm.validateFields();
      setRepoSaving(true);

      const isEdit = editingRepo !== null;
      const res = await fetch(`/api/agents/${name}/repos`, {
        method: isEdit ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isEdit ? { id: editingRepo.id, ...values } : values),
      });
      const data = await res.json();
      if (!res.ok) {
        message.error(data.error || "Failed to save repo");
        return;
      }
      message.success(isEdit ? "Repo updated" : "Repo added");
      setRepoModalOpen(false);
      repoForm.resetFields();
      setEditingRepo(null);
      fetchRepos();
      onMutate?.();
    } catch {
      // validation error
    } finally {
      setRepoSaving(false);
    }
  };

  const handleDeleteRepo = async (id: number) => {
    try {
      const res = await fetch(`/api/agents/${name}/repos`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id }),
      });
      const data = await res.json();
      if (!res.ok) {
        message.error(data.error || "Failed to delete repo");
        return;
      }
      message.success("Repo removed");
      fetchRepos();
      onMutate?.();
    } catch {
      message.error("Failed to delete repo");
    }
  };

  const repoColumns = [
    {
      title: "Name",
      dataIndex: "repo_name",
      key: "repo_name",
      ellipsis: true,
    },
    {
      title: "URL",
      dataIndex: "repo_url",
      key: "repo_url",
      ellipsis: true,
      render: (url: string) => (
        <a href={url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
          {url.replace(/^https?:\/\/github\.com\//, "")}
        </a>
      ),
    },
    {
      title: "By",
      dataIndex: "assigned_by",
      key: "assigned_by",
      width: 80,
      render: (v: string | null) => v || "\u2014",
    },
    {
      title: "",
      key: "actions",
      width: 70,
      render: (_: unknown, record: Repo) => (
        <Space size={4}>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => { e.stopPropagation(); openEditRepo(record); }}
          />
          <Popconfirm
            title="Remove this repo?"
            onConfirm={(e) => { e?.stopPropagation(); handleDeleteRepo(record.id); }}
            onCancel={(e) => e?.stopPropagation()}
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        size="small"
        extra={
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={openAddRepo}>
            Add Repo
          </Button>
        }
      >
        <Table
          dataSource={repos}
          columns={repoColumns}
          rowKey="id"
          pagination={false}
          size="small"
          loading={reposLoading}
          locale={{ emptyText: "No repos assigned" }}
        />
      </Card>

      {/* Add/Edit Repo Modal */}
      <Modal
        title={editingRepo ? "Edit Repo" : "Add Repo"}
        open={repoModalOpen}
        onCancel={() => { setRepoModalOpen(false); repoForm.resetFields(); setEditingRepo(null); }}
        onOk={handleRepoSave}
        confirmLoading={repoSaving}
        okText={editingRepo ? "Update" : "Add"}
        forceRender
      >
        <Form form={repoForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="repo_url"
            label="Repository URL"
            rules={[{ required: true, message: "URL is required" }]}
          >
            <Input placeholder="https://github.com/org/repo" />
          </Form.Item>
          <Form.Item
            name="repo_name"
            label="Name"
            rules={[{ required: true, message: "Name is required" }]}
            extra="Short name used for the local clone folder"
          >
            <Input placeholder="my_repo" />
          </Form.Item>
          <Form.Item
            name="assigned_by"
            label="Assigned By"
          >
            <Input placeholder="boss" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
