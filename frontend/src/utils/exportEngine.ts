import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

/**
 * ExportEngine type definitions
 *
 * Shared interfaces for the report export feature, used by ExportModal
 * and view integrations (AnimalListView, ProcedureDetailView).
 */

/** Column definition for export configuration */
export interface ExportColumnDef {
  /** Unique key for the column, used in selection state */
  key: string;
  /** Display label shown in modal checkboxes and as column header in export */
  label: string;
  /** Function to extract the cell value from a data row */
  accessor: (row: Record<string, unknown>) => string;
}

/** Configuration passed to export generation functions */
export interface ExportConfig {
  /** Optional report title for the header */
  title: string;
  /** Ordered list of selected columns (already filtered and ordered) */
  columns: ExportColumnDef[];
  /** Data rows to export (already filtered by view) */
  data: Record<string, unknown>[];
  /** Whether to insert the empty "Anotações" column */
  includeNotes: boolean;
  /** Procedure metadata for procedure exports */
  procedureInfo?: {
    date: string;
    status: string;
  };
}

/**
 * Converts an ISO date string (YYYY-MM-DD) to DD/MM/YYYY format.
 */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-');
  return `${day}/${month}/${year}`;
}

/**
 * Reverses the tags array and joins with newline (excel) or comma-space (pdf).
 */
export function formatTags(tags: string[], mode: 'excel' | 'pdf'): string {
  const reversed = [...tags].reverse();
  return mode === 'excel' ? reversed.join('\n') : reversed.join(', ');
}

/**
 * Maps action type keys to Portuguese labels.
 */
export function translateActionType(type: string): string {
  const translations: Record<string, string> = {
    weight: 'Peso',
    insemination: 'Inseminação',
    diagnostic: 'Diagnóstico',
    observation: 'Observação',
    inspected: 'Inspeção',
    implant: 'Implante',
  };
  return translations[type] ?? type;
}

/**
 * Sanitizes title (removes special chars, replaces spaces with underscores,
 * truncates to 50 chars), defaults to "relatorio" if empty, appends
 * _YYYYMMDD_HHmm timestamp and extension.
 */
export function deriveFilename(title: string, extension: string): string {
  let sanitized = title
    .replace(/[^a-zA-Z0-9\s]/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 50);

  if (!sanitized) {
    sanitized = 'relatorio';
  }

  const now = new Date();
  const yyyy = now.getFullYear().toString();
  const mm = (now.getMonth() + 1).toString().padStart(2, '0');
  const dd = now.getDate().toString().padStart(2, '0');
  const hh = now.getHours().toString().padStart(2, '0');
  const min = now.getMinutes().toString().padStart(2, '0');
  const timestamp = `${yyyy}${mm}${dd}_${hh}${min}`;

  return `${sanitized}_${timestamp}.${extension}`;
}

/**
 * Builds header text with title and generation date DD/MM/YYYY HH:mm.
 * If procedureInfo is provided, includes procedure date and status.
 */
export function buildHeaderText(
  title: string,
  procedureInfo?: { date: string; status: string }
): string {
  const now = new Date();
  const dd = now.getDate().toString().padStart(2, '0');
  const mm = (now.getMonth() + 1).toString().padStart(2, '0');
  const yyyy = now.getFullYear().toString();
  const hh = now.getHours().toString().padStart(2, '0');
  const min = now.getMinutes().toString().padStart(2, '0');
  const generationDate = `${dd}/${mm}/${yyyy} ${hh}:${min}`;

  let header = title ? `${title} — ${generationDate}` : generationDate;

  if (procedureInfo) {
    header += ` | Procedimento: ${formatDate(procedureInfo.date)} (${procedureInfo.status})`;
  }

  return header;
}

/**
 * Places "Brinco" (key="ear_tag") first, inserts "Anotações" at position 1
 * if includeNotes is true, remaining columns in original order.
 */
export function buildColumnOrder(
  columns: ExportColumnDef[],
  includeNotes: boolean
): ExportColumnDef[] {
  const brinco = columns.find((col) => col.key === 'ear_tag');
  const remaining = columns.filter((col) => col.key !== 'ear_tag');

  const result: ExportColumnDef[] = [];

  if (brinco) {
    result.push(brinco);
  }

  if (includeNotes) {
    result.push({
      key: 'notes_handwriting',
      label: 'Anotações',
      accessor: () => '',
    });
  }

  result.push(...remaining);

  return result;
}

/**
 * Generates an Excel (.xlsx) file from the export configuration.
 *
 * Structure:
 * - Row 1: Merged header text (report title + generation date)
 * - Row 2: Column headers with auto-filter applied
 * - Row 3+: Data rows using column accessors
 *
 * Returns a Blob with the appropriate MIME type.
 */
export function generateExcel(config: ExportConfig): Blob {
  const orderedColumns = buildColumnOrder(config.columns, config.includeNotes);
  const headerText = buildHeaderText(config.title, config.procedureInfo);

  // Build worksheet data as array of arrays
  const wsData: (string | null)[][] = [];

  // Row 1: Header text (will be merged across all columns)
  const headerRow: (string | null)[] = [headerText];
  for (let i = 1; i < orderedColumns.length; i++) {
    headerRow.push(null);
  }
  wsData.push(headerRow);

  // Row 2: Column headers
  const columnHeaderRow = orderedColumns.map((col) => col.label);
  wsData.push(columnHeaderRow);

  // Row 3+: Data rows
  for (const row of config.data) {
    const dataRow = orderedColumns.map((col) => col.accessor(row));
    wsData.push(dataRow);
  }

  // Create worksheet from array of arrays
  const ws = XLSX.utils.aoa_to_sheet(wsData);

  // Merge cells in row 1 across all columns for the header
  if (orderedColumns.length > 1) {
    ws['!merges'] = [
      { s: { r: 0, c: 0 }, e: { r: 0, c: orderedColumns.length - 1 } },
    ];
  }

  // Apply auto-filter to column header row (row 2, 0-indexed row 1)
  ws['!autofilter'] = {
    ref: XLSX.utils.encode_range({
      s: { r: 1, c: 0 },
      e: { r: 1, c: orderedColumns.length - 1 },
    }),
  };

  // Create workbook with single worksheet
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Relatório');

  // Write workbook to array buffer
  const wbOut = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });

  return new Blob([wbOut], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
}

/**
 * Generates a PDF file from the export configuration.
 *
 * Structure:
 * - Header text at top of document (report title + generation date)
 * - Bordered table with auto-sized columns and readable font
 * - Column headers repeated on page breaks
 * - "Página X de Y" footer on each page
 * - Orientation: landscape if columns > 6, portrait otherwise
 *
 * Returns a Blob with the appropriate MIME type.
 */
export function generatePdf(config: ExportConfig): Blob {
  const orderedColumns = buildColumnOrder(config.columns, config.includeNotes);
  const headerText = buildHeaderText(config.title, config.procedureInfo);

  // Determine orientation based on column count
  const orientation = orderedColumns.length > 6 ? 'landscape' : 'portrait';

  const doc = new jsPDF({ orientation, unit: 'mm', format: 'a4' });

  // Add header text at top of document
  doc.setFontSize(11);
  doc.text(headerText, 14, 15);

  // Build table head and body
  const head = [orderedColumns.map((col) => col.label)];
  const body = config.data.map((row) =>
    orderedColumns.map((col) => col.accessor(row))
  );

  // Render table using autoTable
  autoTable(doc, {
    head,
    body,
    startY: 22,
    showHead: 'everyPage',
    theme: 'grid',
    styles: { fontSize: 9 },
    headStyles: { fillColor: [41, 128, 185], fontStyle: 'bold' },
    margin: { top: 22, bottom: 20 },
    didDrawPage: (data) => {
      // Add "Página X de Y" footer on each page
      const pageCount = doc.getNumberOfPages();
      const currentPage = data.pageNumber;
      const pageWidth = doc.internal.pageSize.getWidth();
      doc.setFontSize(8);
      doc.text(
        `Página ${currentPage} de ${pageCount}`,
        pageWidth / 2,
        doc.internal.pageSize.getHeight() - 10,
        { align: 'center' }
      );
    },
  });

  // Update page count in footers (since total pages is only known after all pages are drawn)
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    // Overwrite footer with correct total page count
    doc.setFillColor(255, 255, 255);
    doc.rect(0, pageHeight - 15, pageWidth, 15, 'F');
    doc.setFontSize(8);
    doc.setTextColor(0, 0, 0);
    doc.text(
      `Página ${i} de ${totalPages}`,
      pageWidth / 2,
      pageHeight - 10,
      { align: 'center' }
    );
  }

  return doc.output('blob');
}

/**
 * Triggers a browser download for the given Blob with the specified filename.
 *
 * Creates an object URL, programmatically clicks a hidden anchor element,
 * then revokes the URL. Throws if the browser does not support the required APIs.
 */
export function triggerDownload(blob: Blob, filename: string): void {
  if (typeof window === 'undefined' || !window.URL || !window.URL.createObjectURL) {
    throw new Error('Navegador não suportado para exportação');
  }

  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.style.display = 'none';
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(url);
}
