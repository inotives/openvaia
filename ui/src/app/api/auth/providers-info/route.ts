import { NextResponse } from "next/server";
import { getAvailableProviders } from "@/lib/auth";

export async function GET() {
  return NextResponse.json(getAvailableProviders());
}
