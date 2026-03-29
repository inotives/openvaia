"use client";

import React from "react";
import { Card, Typography } from "antd";
import CircularBarplotAnimated from "@/components/charts/CircularBarplotAnimated";

const { Title, Text } = Typography;

export default function DemoPage() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 8 }}>
        Chart Demo
      </Title>
      <Text type="secondary" style={{ display: "block", marginBottom: 24 }}>
        Animated circular barplot — random values 1-100, refreshing every second with eased transitions.
      </Text>

      <Card
        size="small"
        style={{ background: "transparent", border: "none", display: "inline-block" }}
        bodyStyle={{ padding: 0 }}
      >
        <CircularBarplotAnimated size={520} />
      </Card>
    </div>
  );
}
