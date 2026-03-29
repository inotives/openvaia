"use client";

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { Avatar, Layout, Menu, theme, Typography } from "antd";
import {
  BookOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  DashboardOutlined,
  LogoutOutlined,
  ProjectOutlined,
  RobotOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  UserOutlined,
} from "@ant-design/icons";

const { Sider, Content } = Layout;
const { Title, Text } = Typography;

const menuItems = [
  { key: "/office", icon: <RobotOutlined />, label: "🎮 Office" },
  { key: "/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "/tasks", icon: <ProjectOutlined />, label: "Tasks" },
  { key: "/agents", icon: <RobotOutlined />, label: "Agents" },
  { key: "/skills", icon: <ThunderboltOutlined />, label: "Skills" },
  // Cron disabled — replaced by recurring tasks via heartbeat
  // { key: "/cron-jobs", icon: <ClockCircleOutlined />, label: "Cron Jobs" },
  { key: "/resources", icon: <BookOutlined />, label: "Resources" },
  { key: "/prompt-gen", icon: <BulbOutlined />, label: "Prompt Gen" },
  { key: "/config", icon: <SettingOutlined />, label: "Config" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const { data: session } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const { token } = theme.useToken();

  const selectedKey = menuItems.find((item) => pathname.startsWith(item.key))?.key || "/dashboard";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        style={{ background: token.colorBgContainer, borderRight: `1px solid ${token.colorBorderSecondary}`, display: "flex", flexDirection: "column" }}
      >
        <div
          style={{
            padding: collapsed ? "12px 8px" : "16px",
            textAlign: "center",
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={collapsed ? "/logo-icon.svg" : "/logo-primary.svg"}
            alt="OpenVAIA"
            style={{ width: collapsed ? 32 : "100%", maxWidth: 170 }}
          />
        </div>
        {session?.user && (
          <div
            style={{
              padding: collapsed ? "12px 0" : "12px 16px",
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "flex-start",
              gap: 10,
              overflow: "hidden",
            }}
          >
            {session.user.image ? (
              <Avatar src={session.user.image} size={collapsed ? 28 : 32} />
            ) : (
              <Avatar icon={<UserOutlined />} size={collapsed ? 28 : 32} />
            )}
            {!collapsed && (
              <div style={{ minWidth: 0 }}>
                <Text strong style={{ fontSize: 13, display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {session.user.name || "Admin"}
                </Text>
                <Text type="secondary" style={{ fontSize: 11, display: "block", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {session.user.email}
                </Text>
              </div>
            )}
          </div>
        )}
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => router.push(key)}
          style={{ borderInlineEnd: "none", flex: 1 }}
        />
        <Menu
          mode="inline"
          selectable={false}
          items={[{ key: "logout", icon: <LogoutOutlined />, label: "Logout" }]}
          onClick={() => signOut({ callbackUrl: "/login" })}
          style={{ borderInlineEnd: "none" }}
        />
      </Sider>
      <Content style={{ padding: 24, background: token.colorBgLayout }}>
        {children}
      </Content>
    </Layout>
  );
}
