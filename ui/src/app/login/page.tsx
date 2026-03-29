"use client";

import React, { useEffect, useState } from "react";
import { signIn } from "next-auth/react";
import { Button, Card, Divider, Form, Input, Spin, Typography, message } from "antd";
import { GoogleOutlined, LockOutlined, UserOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [providers, setProviders] = useState<{ hasGoogle: boolean; hasCredentials: boolean; hasAny: boolean } | null>(null);

  useEffect(() => {
    fetch("/api/auth/providers-info")
      .then((r) => r.json())
      .then(setProviders)
      .catch(() => setProviders({ hasGoogle: false, hasCredentials: false, hasAny: false }));
  }, []);

  const onCredentialsSubmit = async (values: { username: string; password: string }) => {
    setLoading(true);
    const result = await signIn("credentials", {
      username: values.username,
      password: values.password,
      redirect: false,
    });
    setLoading(false);
    if (result?.error) {
      message.error("Invalid username or password");
    } else {
      window.location.href = "/dashboard";
    }
  };

  const onGoogleSignIn = () => {
    setGoogleLoading(true);
    signIn("google", { callbackUrl: "/dashboard" });
  };

  if (!providers) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#0f0f1a" }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "#0f0f1a",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/logo.svg" alt="OpenVAIA" style={{ width: 180, marginBottom: 32 }} />
      <Card
        style={{
          width: 380,
          background: "transparent",
          border: "none",
          boxShadow: "none",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Text type="secondary">Sign in to continue</Text>
        </div>

        {providers.hasGoogle && (
          <Button
            icon={<GoogleOutlined />}
            size="large"
            block
            onClick={onGoogleSignIn}
            loading={googleLoading}
          >
            Sign in with Google
          </Button>
        )}

        {providers.hasGoogle && providers.hasCredentials && (
          <Divider plain>
            <Text type="secondary" style={{ fontSize: 12 }}>or</Text>
          </Divider>
        )}

        {providers.hasCredentials && (
          <Form onFinish={onCredentialsSubmit} layout="vertical" requiredMark={false}>
            <Form.Item name="username" rules={[{ required: true, message: "Username is required" }]}>
              <Input prefix={<UserOutlined />} placeholder="Username" size="large" />
            </Form.Item>
            <Form.Item name="password" rules={[{ required: true, message: "Password is required" }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="Password" size="large" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" size="large" block loading={loading}>
                Sign in
              </Button>
            </Form.Item>
          </Form>
        )}

        {!providers.hasAny && (
          <div style={{ textAlign: "center", padding: 16 }}>
            <Text type="danger">
              No authentication configured. Set GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET or UI_USERNAME/UI_PASSWORD.
            </Text>
          </div>
        )}
      </Card>
    </div>
  );
}
