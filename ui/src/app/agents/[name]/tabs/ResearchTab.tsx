"use client";

import React, { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  Input,
  Select,
  Space,
  Tag,
  Typography,
} from "antd";
import { ArrowLeftOutlined, FileSearchOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ResearchReport, timeAgo } from "../utils";

const { Text } = Typography;

interface ResearchTabProps {
  name: string;
  refreshKey: number;
}

export default function ResearchTab({ name, refreshKey }: ResearchTabProps) {
  const [reports, setReports] = useState<ResearchReport[]>([]);
  const [reportsLoading, setReportsLoading] = useState(false);
  const [selectedReport, setSelectedReport] = useState<ResearchReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [researchSearch, setResearchSearch] = useState("");
  const [researchTagFilter, setResearchTagFilter] = useState<string | undefined>();
  const [researchDateRange, setResearchDateRange] = useState<[string, string] | null>(null);

  const fetchReports = useCallback(async () => {
    setReportsLoading(true);
    try {
      const params = new URLSearchParams();
      if (researchSearch.trim()) params.set("q", researchSearch.trim());
      if (researchTagFilter) params.set("tag", researchTagFilter);
      if (researchDateRange) {
        params.set("from", researchDateRange[0]);
        params.set("to", researchDateRange[1]);
      }
      const res = await fetch(`/api/agents/${name}/research?${params}`);
      const data = await res.json();
      if (!data.error) setReports(data);
    } catch (err) {
      console.error("Failed to fetch reports:", err);
    } finally {
      setReportsLoading(false);
    }
  }, [name, researchSearch, researchTagFilter, researchDateRange]);

  const openReport = async (id: number) => {
    setReportLoading(true);
    try {
      const res = await fetch(`/api/agents/${name}/research/${id}`);
      const data = await res.json();
      if (!data.error) setSelectedReport(data);
    } catch (err) {
      console.error("Failed to fetch report:", err);
    } finally {
      setReportLoading(false);
    }
  };

  // Fetch on mount
  useEffect(() => {
    fetchReports();
  }, [fetchReports, refreshKey]);

  if (selectedReport) {
    return (
      <Card
        size="small"
        title={
          <Space>
            <Button
              type="text"
              size="small"
              icon={<ArrowLeftOutlined />}
              onClick={() => setSelectedReport(null)}
            />
            <span>{selectedReport.title}</span>
          </Space>
        }
        extra={
          <Space>
            {selectedReport.task_key && (
              <Tag color="blue">{selectedReport.task_key}</Tag>
            )}
            {selectedReport.tags?.map((t) => (
              <Tag key={t} style={{ margin: 0 }}>{t}</Tag>
            ))}
            <Text type="secondary" style={{ fontSize: 12 }}>
              {timeAgo(selectedReport.created_at)}
            </Text>
          </Space>
        }
      >
        <div style={{ padding: "8px 0" }}>
          <Text type="secondary" style={{ fontSize: 13, fontStyle: "italic" }}>
            {selectedReport.summary}
          </Text>
        </div>
        <div
          className="markdown-body"
          style={{
            maxHeight: 600,
            overflowY: "auto",
            padding: "12px 0",
            lineHeight: 1.7,
            fontSize: 13,
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {selectedReport.body ?? ""}
          </ReactMarkdown>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card size="small" styles={{ body: { padding: "12px 16px" } }} style={{ marginBottom: 12 }}>
        <Space wrap>
          <Input.Search
            placeholder="Search title..."
            allowClear
            style={{ width: 200 }}
            onSearch={(v) => setResearchSearch(v)}
          />
          <Select
            placeholder="Tag"
            allowClear
            value={researchTagFilter}
            onChange={setResearchTagFilter}
            style={{ width: 140 }}
            options={[...new Set(reports.flatMap((r) => r.tags || []))].sort().map((t) => ({ value: t, label: t }))}
          />
          <DatePicker.RangePicker
            size="middle"
            onChange={(_, dateStrings) => {
              if (dateStrings[0] && dateStrings[1]) {
                setResearchDateRange([dateStrings[0], dateStrings[1]]);
              } else {
                setResearchDateRange(null);
              }
            }}
          />
        </Space>
      </Card>
      <Card size="small" loading={reportsLoading}>
        {reports.length === 0 ? (
          <div style={{ textAlign: "center", padding: 40 }}>
            <FileSearchOutlined style={{ fontSize: 32, opacity: 0.3 }} />
            <br />
            <Text type="secondary">No research reports yet</Text>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {reports.map((r) => (
              <Card
                key={r.id}
                size="small"
                hoverable
                onClick={() => openReport(r.id)}
                style={{ cursor: "pointer" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <Text strong style={{ fontSize: 14 }}>{r.title}</Text>
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }} ellipsis>
                        {r.summary.slice(0, 150)}{r.summary.length > 150 ? "..." : ""}
                      </Text>
                    </div>
                    <div style={{ marginTop: 6 }}>
                      {r.task_key && <Tag color="blue" style={{ margin: "0 4px 0 0" }}>{r.task_key}</Tag>}
                      {r.tags?.slice(0, 4).map((t) => (
                        <Tag key={t} style={{ margin: "0 4px 0 0" }}>{t}</Tag>
                      ))}
                    </div>
                  </div>
                  <Text type="secondary" style={{ fontSize: 11, flexShrink: 0, marginLeft: 12 }}>
                    {timeAgo(r.created_at)}
                  </Text>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Card>
    </>
  );
}
