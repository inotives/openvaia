"use client";

import React, { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Button, Card, Typography } from "antd";

const { Title, Text } = Typography;

const errorMessages: Record<string, string> = {
  Configuration: "There is a problem with the server configuration.",
  AccessDenied: "You do not have permission to sign in.",
  Verification: "The verification link has expired or has already been used.",
  Default: "An unexpected error occurred during authentication.",
};

function AuthErrorContent() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error") || "Default";
  const message = errorMessages[error] || errorMessages.Default;

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
          width: 440,
          background: "transparent",
          border: "none",
          boxShadow: "none",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <Title level={4} style={{ marginBottom: 12 }}>Authentication Error</Title>
          <Text type="secondary" style={{ fontSize: 15, display: "block", marginBottom: 24 }}>
            {message}
          </Text>
          <Button size="large" block href="/login">
            Back to Sign In
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense>
      <AuthErrorContent />
    </Suspense>
  );
}
