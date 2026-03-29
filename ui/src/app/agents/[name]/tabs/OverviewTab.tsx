"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Card, Col, Row, Space, Tag, Typography } from "antd";
import { ClockCircleOutlined } from "@ant-design/icons";
import CircularBarplot from "@/components/charts/CircularBarplot";
import ActivityTimeline from "@/components/charts/ActivityTimeline";
import PriorityHeatmap from "@/components/charts/PriorityHeatmap";
import ActivityHeatmap from "@/components/charts/ActivityHeatmap";
import TokenUsageChart from "@/components/charts/TokenUsageChart";
import { AgentMetrics, timeAgo } from "../utils";

const { Text } = Typography;

interface OverviewTabProps {
  name: string;
  metrics: AgentMetrics | null;
  loading: boolean;
  refreshKey: number;
}

export default function OverviewTab({ name, metrics, loading }: OverviewTabProps) {
  return (
    <Row gutter={[16, 16]}>
      {/* Left column: 3/10 */}
      <Col xs={24} md={7}>
        <Row gutter={[0, 16]}>
          <Col span={24}>
            <Card title="Activity Radar" size="small" loading={loading} style={{ background: "transparent", border: "none" }}>
              <div style={{ display: "flex", justifyContent: "center" }}>
                <CircularBarplot data={metrics?.radar ?? []} size={460} hideLabels />
              </div>
            </Card>
          </Col>
          <Col span={24}>
            <Card title="Health (24h)" size="small" loading={loading}>
              {metrics?.healthHistory.length ? (
                <div style={{ maxHeight: 220, overflow: "auto" }}>
                  {metrics.healthHistory.slice(-10).reverse().map((h, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid #f0f0f0" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        <ClockCircleOutlined /> {timeAgo(h.checked_at)}
                      </Text>
                      <Space size={8}>
                        {h.details?.is_busy && <Tag color="orange" style={{ margin: 0 }}>Busy</Tag>}
                        {h.details?.uptime_seconds != null && (
                          <Text style={{ fontSize: 12 }}>
                            Up: {Math.floor(h.details.uptime_seconds / 3600)}h
                          </Text>
                        )}
                      </Space>
                    </div>
                  ))}
                </div>
              ) : (
                <Text type="secondary">No health data</Text>
              )}
            </Card>
          </Col>
        </Row>
      </Col>

      {/* Right column: 7/10 */}
      <Col xs={24} md={17}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="Priority x Status" size="small" loading={loading} style={{ background: "transparent", border: "none" }}>
              <PriorityHeatmap data={metrics?.tasksByPriority ?? []} height={220} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Task Completions (6 months)" size="small" loading={loading} style={{ background: "transparent", border: "none" }}>
              <div style={{ overflowX: "auto" }}>
                <ActivityHeatmap data={metrics?.completionHeatmap ?? []} height={220} />
              </div>
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Activity (30 days)" size="small" loading={loading} style={{ background: "transparent", border: "none" }}>
              <ActivityTimeline data={metrics?.activityTimeline ?? []} height={220} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Token Usage (30 days)" size="small" loading={loading} style={{ background: "transparent", border: "none" }}>
              <TokenUsageChart data={metrics?.tokenTimeline ?? []} height={220} />
            </Card>
          </Col>
        </Row>
      </Col>
    </Row>
  );
}
