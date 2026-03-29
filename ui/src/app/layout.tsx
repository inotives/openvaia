import "@ant-design/v5-patch-for-react-19";
import React from "react";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider, theme } from "antd";
import SessionWrapper from "@/components/SessionWrapper";
import LayoutSwitch from "@/components/LayoutSwitch";

export const metadata = {
  title: "openvaia",
  description: "openvaia admin dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Pixelify+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body style={{ margin: 0 }}>
        <SessionWrapper>
          <AntdRegistry>
            <ConfigProvider
              theme={{
                algorithm: theme.darkAlgorithm,
                token: {
                  colorPrimary: "#1677ff",
                  colorBgBase: "#141422",
                  colorBgContainer: "#1a1a2e",
                  colorBgElevated: "#1f1f3a",
                  colorBgLayout: "#0f0f1a",
                  colorBorderSecondary: "#2a2a4a",
                  colorText: "rgba(255,255,255,0.85)",
                  colorTextSecondary: "rgba(255,255,255,0.55)",
                  colorTextTertiary: "rgba(255,255,255,0.35)",
                  colorTextQuaternary: "rgba(255,255,255,0.25)",
                },
                components: {
                  Menu: {
                    itemSelectedBg: "rgba(255,255,255,0.1)",
                    itemSelectedColor: "#ffffff",
                    itemHoverBg: "rgba(255,255,255,0.06)",
                    itemColor: "rgba(255,255,255,0.55)",
                    itemHoverColor: "rgba(255,255,255,0.85)",
                  },
                  Select: {
                    optionSelectedBg: "rgba(22,119,255,0.25)",
                    optionSelectedColor: "#ffffff",
                    optionActiveBg: "rgba(22,119,255,0.15)",
                  },
                  Dropdown: {
                    controlItemBgActive: "rgba(22,119,255,0.25)",
                    controlItemBgActiveHover: "rgba(22,119,255,0.35)",
                    controlItemBgHover: "rgba(22,119,255,0.15)",
                  },
                  Cascader: {
                    optionSelectedBg: "rgba(22,119,255,0.25)",
                  },
                  TreeSelect: {
                    nodeSelectedBg: "rgba(22,119,255,0.25)",
                    nodeHoverBg: "rgba(22,119,255,0.15)",
                  },
                  DatePicker: {
                    cellActiveWithRangeBg: "rgba(22,119,255,0.15)",
                    cellHoverBg: "rgba(22,119,255,0.15)",
                  },
                  Table: {
                    rowSelectedBg: "rgba(22,119,255,0.15)",
                    rowSelectedHoverBg: "rgba(22,119,255,0.25)",
                    rowHoverBg: "rgba(255,255,255,0.04)",
                  },
                },
              }}
            >
              <LayoutSwitch>{children}</LayoutSwitch>
            </ConfigProvider>
          </AntdRegistry>
        </SessionWrapper>
      </body>
    </html>
  );
}
