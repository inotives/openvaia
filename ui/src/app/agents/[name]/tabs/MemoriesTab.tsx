"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  DatePicker,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { DeleteOutlined, LoadingOutlined, ReloadOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface MemoriesTabProps {
  name: string;
  refreshKey: number;
}

export default function MemoriesTab({ name, refreshKey }: MemoriesTabProps) {
  const [memories, setMemories] = useState<any[]>([]);
  const [memoriesLoading, setMemoriesLoading] = useState(false);
  const [memoryTierFilter, setMemoryTierFilter] = useState<string | null>(null);
  const [memoryTagFilter, setMemoryTagFilter] = useState<string | null>(null);
  const [memorySearch, setMemorySearch] = useState("");
  const [memoryDateRange, setMemoryDateRange] = useState<[string, string] | null>(null);
  const [memoryLimit, setMemoryLimit] = useState(100);
  const [memoryHasMore, setMemoryHasMore] = useState(false);
  const [viewingMemory, setViewingMemory] = useState<any>(null);

  const fetchMemories = useCallback(async () => {
    setMemoriesLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/memories?limit=${memoryLimit}`);
      const data = await res.json();
      if (!data.error) {
        setMemories(data);
        setMemoryHasMore(data.length >= memoryLimit);
      }
    } catch (err) {
      console.error("Failed to fetch memories:", err);
    } finally {
      setMemoriesLoading(false);
    }
  }, [name, memoryLimit]);

  // Fetch on mount
  useEffect(() => {
    fetchMemories();
  }, [fetchMemories, refreshKey]);

  // Client-side memory filtering
  const filteredMemories = memories.filter((mem: any) => {
    if (memoryTierFilter && mem.tier !== memoryTierFilter) return false;
    if (memoryTagFilter && !(mem.tags || []).includes(memoryTagFilter)) return false;
    if (memorySearch.trim()) {
      const q = memorySearch.trim().toLowerCase();
      if (!mem.content?.toLowerCase().includes(q) && !(mem.tags || []).some((t: string) => t.toLowerCase().includes(q))) return false;
    }
    if (memoryDateRange) {
      const created = new Date(mem.created_at).toISOString().slice(0, 10);
      if (created < memoryDateRange[0] || created > memoryDateRange[1]) return false;
    }
    return true;
  });

  return (
    <div>
      {/* Filters */}
      <Space style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", flexWrap: "wrap" }}>
        <Space wrap>
          <Select
            placeholder="All tiers"
            allowClear
            style={{ width: 120 }}
            value={memoryTierFilter}
            onChange={(v) => setMemoryTierFilter(v || null)}
            options={[
              { label: "Long-term", value: "long" },
              { label: "Short-term", value: "short" },
            ]}
          />
          <Select
            placeholder="Filter by tag"
            allowClear
            style={{ width: 160 }}
            value={memoryTagFilter}
            onChange={(v) => setMemoryTagFilter(v || null)}
            options={[...new Set(memories.flatMap((m: any) => m.tags || []))].sort().map((t) => ({ label: t, value: t }))}
          />
          <DatePicker.RangePicker
            size="middle"
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setMemoryDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setMemoryDateRange(null);
              }
            }}
          />
          <Input
            placeholder="Search memories..."
            allowClear
            style={{ width: 220 }}
            value={memorySearch}
            onChange={(e) => setMemorySearch(e.target.value)}
          />
        </Space>
        <Button icon={<ReloadOutlined />} size="small" onClick={fetchMemories} loading={memoriesLoading}>
          Refresh
        </Button>
      </Space>

      {memoriesLoading ? (
        <div style={{ textAlign: "center", padding: 40 }}><LoadingOutlined /></div>
      ) : filteredMemories.length === 0 ? (
        <Card size="small"><Text type="secondary">{memories.length === 0 ? "No memories stored" : "No memories match filters"}</Text></Card>
      ) : (
        <Row gutter={[12, 12]}>
          {filteredMemories.map((mem: any) => (
            <Col key={mem.id} xs={24} sm={12} lg={8}>
              <Card
                size="small"
                hoverable
                onClick={() => setViewingMemory(mem)}
                style={{ height: "100%", cursor: "pointer" }}
                styles={{ body: { padding: "12px 16px", display: "flex", flexDirection: "column", height: "100%" } }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                    <Tag color={mem.tier === "long" ? "blue" : "default"}>{mem.tier}</Tag>
                    <Popconfirm
                      title="Delete this memory?"
                      onConfirm={async (e) => {
                        e?.stopPropagation();
                        await fetch(`/api/agents/${name}/memories`, {
                          method: "DELETE",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ id: mem.id }),
                        });
                        fetchMemories();
                      }}
                    >
                      <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
                    </Popconfirm>
                  </div>
                  <Text style={{ fontSize: 13, display: "block", marginBottom: 8 }}>
                    {mem.content.length > 120 ? mem.content.slice(0, 120) + "..." : mem.content}
                  </Text>
                  <div>
                    {(mem.tags || []).map((t: string) => <Tag key={t} style={{ marginBottom: 4 }}>{t}</Tag>)}
                  </div>
                </div>
                <div style={{ borderTop: "1px solid #f0f0f0", paddingTop: 8, marginTop: 8 }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {new Date(mem.created_at).toLocaleString()}
                  </Text>
                </div>
              </Card>
            </Col>
          ))}
        </Row>
      )}
      {memoryHasMore && (
        <div style={{ textAlign: "center", marginTop: 16 }}>
          <Button
            onClick={() => setMemoryLimit((prev) => prev + 100)}
            loading={memoriesLoading}
          >
            Load More
          </Button>
        </div>
      )}

      {/* Memory Detail Modal */}
      <Modal
        title="Memory"
        open={!!viewingMemory}
        onCancel={() => setViewingMemory(null)}
        width={600}
        footer={[
          <Popconfirm
            key="delete"
            title="Delete this memory?"
            onConfirm={async () => {
              await fetch(`/api/agents/${name}/memories`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ id: viewingMemory.id }),
              });
              setViewingMemory(null);
              fetchMemories();
            }}
            okText="Delete"
            okButtonProps={{ danger: true }}
          >
            <Button danger icon={<DeleteOutlined />}>Delete</Button>
          </Popconfirm>,
          <Button key="close" onClick={() => setViewingMemory(null)}>Close</Button>,
        ]}
      >
        {viewingMemory && (
          <div>
            <Space style={{ marginBottom: 12 }}>
              <Tag color={viewingMemory.tier === "long" ? "blue" : "default"}>{viewingMemory.tier}-term</Tag>
              {(viewingMemory.tags || []).map((t: string) => <Tag key={t}>{t}</Tag>)}
            </Space>
            <Card
              size="small"
              styles={{ body: { padding: 16, fontFamily: "monospace", fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400, overflow: "auto" } }}
            >
              {viewingMemory.content}
            </Card>
            <div style={{ marginTop: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Created: {new Date(viewingMemory.created_at).toLocaleString()}
              </Text>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
