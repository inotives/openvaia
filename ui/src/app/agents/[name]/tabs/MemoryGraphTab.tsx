"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Button, Card, Modal, Popconfirm, Space, Tag, Typography } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import MemoryGraph from "@/components/charts/MemoryGraph";

const { Text } = Typography;

interface MemoryGraphTabProps {
  name: string;
  refreshKey: number;
}

export default function MemoryGraphTab({ name, refreshKey }: MemoryGraphTabProps) {
  const [memories, setMemories] = useState<any[]>([]);
  const [viewingMemory, setViewingMemory] = useState<any>(null);

  const fetchMemories = useCallback(async () => {
    try {
      const res = await fetch(`/api/agents/${name}/memories?limit=100`);
      const data = await res.json();
      if (!data.error) setMemories(data);
    } catch (err) {
      console.error("Failed to fetch memories:", err);
    }
  }, [name]);

  // Fetch on mount
  useEffect(() => {
    fetchMemories();
  }, [fetchMemories, refreshKey]);

  return (
    <>
      <Card size="small" styles={{ body: { padding: 0 } }}>
        <MemoryGraph
          data={memories}
          height={800}
          onNodeClick={(mem) => setViewingMemory(mem)}
        />
      </Card>

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
    </>
  );
}
