import { ApiError } from "./errors";

function triggerNativeDownload(url: string, filename: string): void {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}

function saveBlob(buffer: ArrayBuffer, contentType: string, filename: string): void {
  const blob = new Blob([buffer], { type: contentType });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.style.display = "none";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  // IDM / tarayıcı indirmeyi yakalasın diye kısa gecikme
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 2_000);
}

function looksLikeBinaryExport(contentType: string): boolean {
  const ct = contentType.toLowerCase();
  return (
    ct.includes("application/pdf") ||
    ct.includes("spreadsheetml") ||
    ct.includes("text/csv") ||
    ct.includes("octet-stream") ||
    ct.includes("application/vnd.ms-excel")
  );
}

async function readErrorDetail(response: Response): Promise<string> {
  let detail = response.statusText;
  const contentType = response.headers.get("content-type") ?? "";
  try {
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
      }
    } else {
      detail = (await response.text()).slice(0, 300) || detail;
    }
  } catch {
    // yedek mesaj
  }
  return detail;
}

/**
 * BFF üzerinden dosya indirir.
 *
 * IDM vb. eklentiler fetch gövdesini boşaltıp dosyayı kendileri kaydedebilir.
 * Eski kod `blob.size === 0` iken hata fırlatıyor, ardından `viaProxy` ile
 * native `<a>` indirmesini hiç çalıştırmıyordu — dosya IDM'de varken
 * "boş dosya" toast'ı görünüyordu. Bu yüzden 200 + boş gövde hata değildir.
 */
async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await fetch(url, {
    cache: "no-store",
    method: "GET",
    headers: { Accept: "*/*" },
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(`İndirme başarısız (${response.status})`, response.status, detail);
  }

  const contentType = response.headers.get("content-type") || "application/octet-stream";
  const declaredLength = Number(response.headers.get("content-length") || "0");
  const buffer = await response.arrayBuffer();

  if (buffer.byteLength === 0) {
    if (looksLikeBinaryExport(contentType) || declaredLength > 0) {
      // IDM gövdeyi aldı; dosya zaten kaydedilmiş kabul et — toast yok
      return;
    }
    triggerNativeDownload(url, filename);
    return;
  }

  if (filename.toLowerCase().endsWith(".pdf")) {
    const head = new Uint8Array(buffer.slice(0, 5));
    const isPdf =
      head[0] === 0x25 && head[1] === 0x50 && head[2] === 0x44 && head[3] === 0x46; // %PDF
    if (!isPdf) {
      const asText = new TextDecoder().decode(buffer.slice(0, 800));
      if (asText.trimStart().startsWith("{")) {
        try {
          const payload = JSON.parse(asText) as { detail?: string };
          throw new ApiError(
            "İndirme başarısız",
            response.status,
            payload.detail ?? "PDF beklenirken JSON alındı",
          );
        } catch (err) {
          if (err instanceof ApiError) throw err;
        }
      }
    }
  }

  saveBlob(buffer, contentType, filename);
}

export function downloadExecutivePdf(
  assetId: string,
  days = 30,
  locale = "tr",
  reportType = "executive",
): Promise<void> {
  return downloadFile(
    `/api/export/pdf?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}&report_type=${encodeURIComponent(reportType)}`,
    `${reportType}-${assetId}.pdf`,
  );
}

export function downloadExecutiveExcel(
  assetId: string,
  days = 30,
  locale = "tr",
  reportType = "executive",
): Promise<void> {
  return downloadFile(
    `/api/export/excel?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}&report_type=${encodeURIComponent(reportType)}`,
    `report-${assetId}.xlsx`,
  );
}

export function downloadHistoryCsv(assetId: string, days = 30, locale = "tr"): Promise<void> {
  return downloadFile(
    `/api/export/csv?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}`,
    `history-${assetId}.csv`,
  );
}

export function downloadExecutiveCsv(
  assetId: string,
  days = 30,
  locale = "tr",
  reportType = "executive",
): Promise<void> {
  return downloadFile(
    `/api/export/executive-csv?asset_id=${encodeURIComponent(assetId)}&days=${days}&locale=${encodeURIComponent(locale)}&report_type=${encodeURIComponent(reportType)}`,
    `${reportType}-${assetId}.csv`,
  );
}
