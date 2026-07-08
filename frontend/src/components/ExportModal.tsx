import { useState, useEffect, useRef, useCallback } from 'react';
import type {
  ExportColumnDef,
  ExportConfig,
} from '../utils/exportEngine';
import {
  buildColumnOrder,
  generateExcel,
  generatePdf,
  triggerDownload,
  deriveFilename,
} from '../utils/exportEngine';

interface ExportModalProps {
  open: boolean;
  onClose: () => void;
  columns: ExportColumnDef[];
  data: Record<string, unknown>[];
  viewContext: 'animal-list' | 'procedure-detail';
  procedureInfo?: {
    date: string;
    status: string;
  };
}

export default function ExportModal({
  open,
  onClose,
  columns,
  data,
  viewContext,
  procedureInfo,
}: ExportModalProps) {
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState('');
  const [includeNotes, setIncludeNotes] = useState(false);
  const [formats, setFormats] = useState({ excel: true, pdf: false });
  const [generating, setGenerating] = useState(false);

  const modalContentRef = useRef<HTMLDivElement>(null);
  const titleId = 'export-modal-title';

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setSelectedColumns(new Set(columns.map((col) => col.key)));
      setTitle('');
      setIncludeNotes(false);
      setFormats({ excel: true, pdf: false });
      setGenerating(false);
    }
  }, [open, columns]);

  // Escape key dismissal
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  // Focus trap
  useEffect(() => {
    if (!open || !modalContentRef.current) return;

    const modal = modalContentRef.current;
    const focusableSelector =
      'input, button, select, textarea, [tabindex]:not([tabindex="-1"])';
    const focusableElements = modal.querySelectorAll<HTMLElement>(focusableSelector);

    if (focusableElements.length > 0) {
      focusableElements[0].focus();
    }

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      const currentFocusable = modal.querySelectorAll<HTMLElement>(focusableSelector);
      if (currentFocusable.length === 0) return;

      const first = currentFocusable[0];
      const last = currentFocusable[currentFocusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleTab);
    return () => document.removeEventListener('keydown', handleTab);
  }, [open]);

  // Outside click dismissal
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  const handleToggleColumn = (key: string) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    setSelectedColumns(new Set(columns.map((col) => col.key)));
  };

  const handleDeselectAll = () => {
    setSelectedColumns(new Set());
  };

  const allSelected = selectedColumns.size === columns.length;

  const canExport =
    selectedColumns.size > 0 && (formats.excel || formats.pdf) && !generating;

  const handleExport = async () => {
    setGenerating(true);
    try {
      const selected = columns.filter((col) => selectedColumns.has(col.key));
      const orderedColumns = buildColumnOrder(selected, includeNotes);

      const config: ExportConfig = {
        title,
        columns: orderedColumns,
        data,
        includeNotes,
        procedureInfo: viewContext === 'procedure-detail' ? procedureInfo : undefined,
      };

      if (formats.excel) {
        const excelBlob = generateExcel(config);
        triggerDownload(excelBlob, deriveFilename(title, 'xlsx'));
      }

      if (formats.pdf) {
        const pdfBlob = generatePdf(config);
        triggerDownload(pdfBlob, deriveFilename(title, 'pdf'));
      }

      onClose();
    } catch (err) {
      console.error('Export generation error:', err);
    } finally {
      setGenerating(false);
    }
  };

  if (!open) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={handleOverlayClick}
    >
      <div
        ref={modalContentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border-light)',
          padding: 'var(--space-lg, 1.5rem)',
          maxWidth: '500px',
          width: '90%',
          maxHeight: '85vh',
          overflowY: 'auto',
          position: 'relative',
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--space-md)',
          }}
        >
          <h2
            id={titleId}
            style={{ margin: 0, fontSize: '1.25rem' }}
          >
            Exportar Relatório
          </h2>
          <button
            type="button"
            className="btn"
            onClick={onClose}
            aria-label="Fechar"
            style={{ padding: '0.25rem 0.5rem', fontSize: '1.25rem', lineHeight: 1 }}
          >
            ×
          </button>
        </div>

        {/* Title input */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <label className="form-label">
            Título do relatório (opcional)
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Relatório de pesagem"
            />
          </label>
        </div>

        {/* Column selection */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 'var(--space-sm, 0.5rem)',
            }}
          >
            <span className="form-label" style={{ margin: 0 }}>
              Colunas
            </span>
            <button
              type="button"
              className="btn"
              onClick={allSelected ? handleDeselectAll : handleSelectAll}
              style={{ fontSize: '0.85rem', padding: '0.2rem 0.5rem' }}
            >
              {allSelected ? 'Desmarcar Todas' : 'Selecionar Todas'}
            </button>
          </div>
          <div
            style={{
              border: '1px solid var(--border-light)',
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-sm, 0.5rem)',
              maxHeight: '180px',
              overflowY: 'auto',
            }}
          >
            {columns.map((col) => (
              <label
                key={col.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.25rem 0',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedColumns.has(col.key)}
                  onChange={() => handleToggleColumn(col.key)}
                />
                {col.label}
              </label>
            ))}
          </div>
        </div>

        {/* Notes column toggle */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <label
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              cursor: 'pointer',
            }}
          >
            <input
              type="checkbox"
              checked={includeNotes}
              onChange={(e) => setIncludeNotes(e.target.checked)}
            />
            Incluir coluna de Anotações (espaço para escrita)
          </label>
        </div>

        {/* Format selection */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <span className="form-label" style={{ display: 'block', marginBottom: 'var(--space-sm, 0.5rem)' }}>
            Formato
          </span>
          <div style={{ display: 'flex', gap: 'var(--space-md)' }}>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={formats.excel}
                onChange={(e) =>
                  setFormats((prev) => ({ ...prev, excel: e.target.checked }))
                }
              />
              Excel (.xlsx)
            </label>
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                cursor: 'pointer',
              }}
            >
              <input
                type="checkbox"
                checked={formats.pdf}
                onChange={(e) =>
                  setFormats((prev) => ({ ...prev, pdf: e.target.checked }))
                }
              />
              PDF (.pdf)
            </label>
          </div>
        </div>

        {/* Export button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-sm, 0.5rem)' }}>
          <button type="button" className="btn" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canExport}
            onClick={handleExport}
          >
            {generating ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span
                  className="spinner-dot"
                  style={{ width: '14px', height: '14px' }}
                />
                Gerando...
              </span>
            ) : (
              'Exportar'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
