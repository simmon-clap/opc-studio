/** PDF export via html2pdf — renders HTML with system CJK fonts (avoids jsPDF Helvetica garbling). */

function pdfEscapeHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildPdfExportNode({ title, subtitle, bodyHtml }) {
  const node = document.createElement("div");
  node.className = "pdf-export-doc";
  node.innerHTML = `
    <header class="pdf-export-head">
      <h1>${pdfEscapeHtml(title)}</h1>
      ${subtitle ? `<p class="pdf-export-sub">${pdfEscapeHtml(subtitle)}</p>` : ""}
    </header>
    <div class="pdf-export-body md-content">${bodyHtml || ""}</div>`;
  return node;
}

async function exportHtmlToPdf(node, filename) {
  await ensureHtml2Pdf();
  if (!window.html2pdf) {
    throw new Error("PDF 组件未加载，请刷新页面后重试");
  }
  const host = document.createElement("div");
  host.className = "pdf-export-host";
  host.appendChild(node);
  document.body.appendChild(host);
  try {
    await html2pdf()
      .set({
        margin: [10, 10, 10, 10],
        filename: filename || "export.pdf",
        image: { type: "jpeg", quality: 0.96 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: "#ffffff",
        },
        jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        pagebreak: { mode: ["css", "legacy"] },
      })
      .from(host)
      .save();
  } finally {
    host.remove();
  }
}

window.buildPdfExportNode = buildPdfExportNode;
window.exportHtmlToPdf = exportHtmlToPdf;
window.pdfEscapeHtml = pdfEscapeHtml;
