import { NextRequest, NextResponse } from "next/server";

import { backendAuthHeaders, getBackendOrigin } from "@/lib/server/backend";

export async function GET(request: NextRequest) {
  const assetId = request.nextUrl.searchParams.get("asset_id");
  const days = request.nextUrl.searchParams.get("days") ?? "30";
  const locale = request.nextUrl.searchParams.get("locale") ?? "tr";
  const reportType = request.nextUrl.searchParams.get("report_type") ?? "executive";

  if (!assetId) {
    return NextResponse.json({ detail: "asset_id gerekli" }, { status: 400 });
  }

  const origin = getBackendOrigin();
  const backendUrl = `${origin}/api/v1/reporting/export/excel?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}&report_type=${encodeURIComponent(reportType)}`;

  try {
    const res = await fetch(backendUrl, {
      headers: backendAuthHeaders({ Accept: "*/*" }),
      cache: "no-store",
    });

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const json = (await res.json()) as { detail?: string };
        if (json.detail) detail = json.detail;
      } catch {
        detail = (await res.text()).slice(0, 200) || detail;
      }
      return NextResponse.json({ detail }, { status: res.status });
    }

    const buffer = await res.arrayBuffer();
    if (buffer.byteLength === 0) {
      return NextResponse.json(
        { detail: "Export produced an empty Excel payload" },
        { status: 502 },
      );
    }

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Content-Disposition": `attachment; filename="report-${assetId}.xlsx"`,
        "Content-Length": String(buffer.byteLength),
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Backend bağlantısı başarısız";
    return NextResponse.json({ detail: `Backend erisilemedi. ${message}` }, { status: 502 });
  }
}
