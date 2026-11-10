import { NextRequest, NextResponse } from "next/server";

import { backendAuthHeaders, getBackendOrigin } from "@/lib/server/backend";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  "authorization",
]);

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyRequest(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const { path } = await context.params;
  const segments = path ?? [];
  if (segments.length === 0) {
    return NextResponse.json({ detail: "Proxy path gerekli" }, { status: 400 });
  }

  const origin = getBackendOrigin();
  const targetPath = segments.map(encodeURIComponent).join("/");
  const search = request.nextUrl.search;
  const backendUrl = `${origin}/${targetPath}${search}`;

  const outboundHeaders = new Headers();
  request.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    outboundHeaders.set(key, value);
  });

  const auth = backendAuthHeaders();
  Object.entries(auth).forEach(([key, value]) => {
    if (typeof value === "string") outboundHeaders.set(key, value);
  });

  if (!outboundHeaders.has("Accept")) {
    outboundHeaders.set("Accept", "application/json");
  }

  const init: RequestInit = {
    method: request.method,
    headers: outboundHeaders,
    cache: "no-store",
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    const body = await request.arrayBuffer();
    if (body.byteLength > 0) {
      init.body = body;
    }
  }

  try {
    const upstream = await fetch(backendUrl, init);
    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (HOP_BY_HOP.has(key.toLowerCase())) return;
      responseHeaders.set(key, value);
    });

    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend bağlantısı başarısız";
    return NextResponse.json(
      { detail: `Backend erişilemedi (${origin}). ${message}` },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function HEAD(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
