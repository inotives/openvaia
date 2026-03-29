"use client";

import React from "react";
import { usePathname } from "next/navigation";
import AppLayout from "@/components/AppLayout";

export default function LayoutSwitch({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // These pages get bare layout (no sidebar)
  if (pathname === "/login" || pathname === "/auth-error" || pathname === "/office") {
    return <>{children}</>;
  }

  return <AppLayout>{children}</AppLayout>;
}
