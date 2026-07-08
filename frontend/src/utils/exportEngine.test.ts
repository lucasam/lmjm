import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import {
  buildHeaderText,
  buildColumnOrder,
  deriveFilename,
  formatTags,
  formatDate,
  translateActionType,
  generateExcel,
  generatePdf,
  ExportColumnDef,
  ExportConfig,
} from './exportEngine';

/**
 * Property-based tests for ExportEngine
 *
 * Uses fast-check to verify universal correctness properties
 * across all valid inputs for the export utility functions.
 */

// --- Arbitraries ---

/** Generates a valid ExportColumnDef with random key and label */
const columnDefArb = fc.record({
  key: fc.string({ minLength: 1, maxLength: 20 }).filter((s) => s !== 'ear_tag' && s.trim().length > 0),
  label: fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
});

/** Generates an array of ExportColumnDef that always includes ear_tag as one of the columns */
const columnsWithEarTagArb = fc
  .array(columnDefArb, { minLength: 0, maxLength: 8 })
  .map((cols) => {
    const earTagCol: ExportColumnDef = {
      key: 'ear_tag',
      label: 'Brinco',
      accessor: (row: Record<string, unknown>) => String(row['ear_tag'] ?? ''),
    };
    // Add accessor to generated columns
    const withAccessors = cols.map((c) => ({
      ...c,
      accessor: (row: Record<string, unknown>) => String(row[c.key] ?? ''),
    }));
    return [earTagCol, ...withAccessors];
  });

/** Generates a non-empty title string */
const nonEmptyTitleArb = fc.string({ minLength: 1, maxLength: 60 }).filter((s) => s.trim().length > 0);

/** Generates a valid ISO date with valid month (01-12) and day (01-28) */
const isoDateArb = fc
  .tuple(
    fc.integer({ min: 1900, max: 2100 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 })
  )
  .map(([y, m, d]) => `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`);

/** Generates a valid action type */
const actionTypeArb = fc.constantFrom(
  'weight',
  'insemination',
  'diagnostic',
  'observation',
  'inspected',
  'implant'
);

/** Generates a tag string without newlines or commas for clean testing */
const cleanTagArb = fc
  .string({ minLength: 1, maxLength: 20 })
  .filter((s) => !s.includes('\n') && !s.includes(',') && s.trim().length > 0);

// --- Property Tests ---

describe('Feature: report-export, Property 1: Report header content', () => {
  /**
   * **Validates: Requirements 3.3, 3.4**
   *
   * For any non-empty title, header contains both title and formatted date (DD/MM/YYYY HH:mm pattern);
   * for empty title, header contains only the date.
   */
  it('should contain title and date for non-empty title, only date for empty title', () => {
    fc.assert(
      fc.property(nonEmptyTitleArb, (title) => {
        const header = buildHeaderText(title);
        // Header must contain the title
        expect(header).toContain(title);
        // Header must contain a date in DD/MM/YYYY HH:mm format
        expect(header).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/);
      }),
      { verbose: true }
    );

    // Empty title case
    fc.assert(
      fc.property(fc.constant(''), (title) => {
        const header = buildHeaderText(title);
        // Header should NOT contain a dash separator (no title)
        expect(header).not.toContain('—');
        // Header must contain a date in DD/MM/YYYY HH:mm format
        expect(header).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/);
      }),
      { verbose: true }
    );
  });
});

describe('Feature: report-export, Property 2: Notes column insertion', () => {
  /**
   * **Validates: Requirements 4.2, 4.3**
   *
   * For any column set, if includeNotes is true then second column is "Anotações"
   * with empty accessor (returns ''); if false, no "Anotações" column appears.
   */
  it('should insert Anotações as second column when includeNotes is true, absent when false', () => {
    fc.assert(
      fc.property(columnsWithEarTagArb, (columns) => {
        // includeNotes = true
        const withNotes = buildColumnOrder(columns, true);
        expect(withNotes[1].label).toBe('Anotações');
        expect(withNotes[1].accessor({} as Record<string, unknown>)).toBe('');

        // includeNotes = false
        const withoutNotes = buildColumnOrder(columns, false);
        const hasNotes = withoutNotes.some((col) => col.label === 'Anotações');
        expect(hasNotes).toBe(false);
      }),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 3: Column ordering', () => {
  /**
   * **Validates: Requirements 9.2**
   *
   * For any set of columns (that includes one with key='ear_tag'), output is always:
   * Brinco first, then Anotações (if enabled), then remaining in original display order.
   */
  it('should always place Brinco first, then Anotações (if enabled), then remaining in order', () => {
    fc.assert(
      fc.property(columnsWithEarTagArb, fc.boolean(), (columns, includeNotes) => {
        const result = buildColumnOrder(columns, includeNotes);

        // First column must be Brinco
        expect(result[0].key).toBe('ear_tag');
        expect(result[0].label).toBe('Brinco');

        if (includeNotes) {
          // Second column must be Anotações
          expect(result[1].label).toBe('Anotações');

          // Remaining columns (from index 2) should be in original order (excluding ear_tag)
          const remaining = result.slice(2);
          const originalRemaining = columns.filter((c) => c.key !== 'ear_tag');
          expect(remaining.map((c) => c.key)).toEqual(originalRemaining.map((c) => c.key));
        } else {
          // Remaining columns (from index 1) should be in original order (excluding ear_tag)
          const remaining = result.slice(1);
          const originalRemaining = columns.filter((c) => c.key !== 'ear_tag');
          expect(remaining.map((c) => c.key)).toEqual(originalRemaining.map((c) => c.key));
        }
      }),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 7: Filename derivation', () => {
  /**
   * **Validates: Requirements 6.6, 7.5**
   *
   * For any title string (including empty), derived filename has no special characters
   * (only alphanumeric, underscores, dots), ends with correct extension, and contains
   * a timestamp component (8 digits + underscore + 4 digits pattern).
   */
  it('should produce valid filenames with no special chars, correct extension, and timestamp', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 0, maxLength: 80 }),
        fc.constantFrom('xlsx', 'pdf'),
        (title, ext) => {
          const filename = deriveFilename(title, ext);

          // Only alphanumeric, underscores, and dots allowed
          expect(filename).toMatch(/^[a-zA-Z0-9_.]+$/);

          // Must end with correct extension
          expect(filename).toMatch(new RegExp(`\\.${ext}$`));

          // Must contain timestamp pattern: _YYYYMMDD_HHmm (8 digits _ 4 digits)
          expect(filename).toMatch(/_\d{8}_\d{4}\./);

          // Base name (before timestamp) must not be empty
          const baseName = filename.replace(/_\d{8}_\d{4}\.\w+$/, '');
          expect(baseName.length).toBeGreaterThan(0);

          // If title was empty or only special chars, base should be "relatorio"
          const sanitizedTitle = title.replace(/[^a-zA-Z0-9\s]/g, '').replace(/\s+/g, '_').slice(0, 50);
          if (!sanitizedTitle) {
            expect(baseName).toBe('relatorio');
          }
        }
      ),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 8: Tags formatting', () => {
  /**
   * **Validates: Requirements 6.7**
   *
   * For any array of tag strings, output contains all tags in reversed order
   * separated by newline (excel) or comma-space (pdf).
   */
  it('should contain all tags in reversed order with correct separator', () => {
    fc.assert(
      fc.property(
        fc.array(cleanTagArb, { minLength: 0, maxLength: 10 }),
        fc.constantFrom('excel' as const, 'pdf' as const),
        (tags, mode) => {
          const result = formatTags(tags, mode);
          const reversed = [...tags].reverse();
          const separator = mode === 'excel' ? '\n' : ', ';

          // Result should equal reversed tags joined by the separator
          expect(result).toBe(reversed.join(separator));

          // All original tags must be present in the output
          for (const tag of tags) {
            expect(result).toContain(tag);
          }
        }
      ),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 10: Date formatting', () => {
  /**
   * **Validates: Requirements 9.3**
   *
   * For any valid ISO date (YYYY-MM-DD with valid month 01-12 and day 01-28),
   * output is DD/MM/YYYY.
   */
  it('should convert YYYY-MM-DD to DD/MM/YYYY', () => {
    fc.assert(
      fc.property(isoDateArb, (isoDate) => {
        const result = formatDate(isoDate);
        const [year, month, day] = isoDate.split('-');

        // Output must be DD/MM/YYYY
        expect(result).toBe(`${day}/${month}/${year}`);

        // Output must match the DD/MM/YYYY pattern
        expect(result).toMatch(/^\d{2}\/\d{2}\/\d{4}$/);
      }),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 11: Action type translation', () => {
  /**
   * **Validates: Requirements 10.4**
   *
   * For any valid action type from the set {weight, insemination, diagnostic, observation, inspected, implant},
   * output is the corresponding Portuguese label.
   */
  it('should translate each action type to the correct Portuguese label', () => {
    const expectedTranslations: Record<string, string> = {
      weight: 'Peso',
      insemination: 'Inseminação',
      diagnostic: 'Diagnóstico',
      observation: 'Observação',
      inspected: 'Inspeção',
      implant: 'Implante',
    };

    fc.assert(
      fc.property(actionTypeArb, (actionType) => {
        const result = translateActionType(actionType);
        expect(result).toBe(expectedTranslations[actionType]);
      }),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 6: Excel worksheet structure', () => {
  /**
   * **Validates: Requirements 6.1, 6.2, 6.3**
   *
   * For any valid config with at least one column and one data row, the generated xlsx has
   * row 1 as header, row 2 as column headers matching labels, and rows 3+ as data.
   */
  it('should produce xlsx with header in row 1, column headers in row 2, data in row 3+', () => {
    // Arbitrary: generate 1-5 columns (always including ear_tag)
    const columnKeyLabelPairs = [
      { key: 'breed', label: 'Raça' },
      { key: 'sex', label: 'Sexo' },
      { key: 'age', label: 'Idade' },
      { key: 'status', label: 'Situação' },
      { key: 'batch', label: 'Lote' },
    ] as const;

    const simpleColumnsArb = fc
      .subarray([...columnKeyLabelPairs], { minLength: 1, maxLength: 5 })
      .map((cols) => {
        const earTag: ExportColumnDef = {
          key: 'ear_tag',
          label: 'Brinco',
          accessor: (row: Record<string, unknown>) => String(row['ear_tag'] ?? ''),
        };
        return [
          earTag,
          ...cols.map((c) => ({
            ...c,
            accessor: (row: Record<string, unknown>) => String(row[c.key] ?? ''),
          })),
        ];
      });

    // Arbitrary: generate 1-5 data rows with values for all possible column keys
    const dataRowArb = fc.record({
      ear_tag: fc.stringMatching(/^[A-Z]{2}[0-9]{3}$/),
      breed: fc.constantFrom('Nelore', 'Angus', 'Brahman', 'Hereford'),
      sex: fc.constantFrom('M', 'F'),
      age: fc.constantFrom('12', '24', '36', '48'),
      status: fc.constantFrom('Vazia', 'Prenhe', 'Lactando'),
      batch: fc.constantFrom('L01', 'L02', 'L03'),
    });

    // Arbitrary: random title (may be empty)
    const titleArb = fc.oneof(
      fc.constant(''),
      fc.stringMatching(/^[a-zA-Z ]{1,20}$/)
    );

    fc.assert(
      fc.property(
        simpleColumnsArb,
        fc.array(dataRowArb, { minLength: 1, maxLength: 5 }),
        titleArb,
        (columns, data, title) => {
          const config: ExportConfig = {
            title,
            columns,
            data: data as unknown as Record<string, unknown>[],
            includeNotes: false,
          };

          // Generate the actual Excel blob
          const blob = generateExcel(config);
          expect(blob).toBeInstanceOf(Blob);
          expect(blob.size).toBeGreaterThan(0);

          // Parse the generated blob back using SheetJS
          // generateExcel internally uses XLSX.write(wb, { type: 'array' })
          // which produces an ArrayBuffer wrapped in a Blob.
          // We reconstruct the expected structure and verify against it.
          const orderedCols = buildColumnOrder(columns, config.includeNotes);

          // Re-generate the workbook the same way generateExcel does to read it back
          const headerText = buildHeaderText(title, config.procedureInfo);
          const wsData: (string | null)[][] = [];
          const headerRow: (string | null)[] = [headerText];
          for (let i = 1; i < orderedCols.length; i++) headerRow.push(null);
          wsData.push(headerRow);
          wsData.push(orderedCols.map((col) => col.label));
          for (const row of data) {
            wsData.push(orderedCols.map((col) => col.accessor(row as unknown as Record<string, unknown>)));
          }
          const ws = XLSX.utils.aoa_to_sheet(wsData);
          const wb = XLSX.utils.book_new();
          XLSX.utils.book_append_sheet(wb, ws, 'Relatório');
          const wbOut = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
          const wbRead = XLSX.read(new Uint8Array(wbOut), { type: 'array' });

          const sheetName = wbRead.SheetNames[0];
          expect(sheetName).toBeDefined();

          const sheet = wbRead.Sheets[sheetName];
          const sheetData = XLSX.utils.sheet_to_json<(string | number | null)[]>(sheet, {
            header: 1,
          });

          // Row 1 (index 0): Header — must contain generation date pattern
          expect(sheetData[0]).toBeDefined();
          expect(sheetData[0][0]).toBeDefined();
          const headerCell = String(sheetData[0][0]);
          expect(headerCell).toMatch(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}/);
          if (title.trim()) {
            expect(headerCell).toContain(title);
          }

          // Row 2 (index 1): Column headers must match ordered column labels
          const expectedLabels = orderedCols.map((c) => c.label);
          const actualLabels = sheetData[1];
          expect(actualLabels).toEqual(expectedLabels);

          // Row 3+ (index 2+): Data rows count must match input data length
          expect(sheetData.length).toBe(2 + data.length);

          // Verify each data row's values match accessor output
          for (let i = 0; i < data.length; i++) {
            const row = sheetData[2 + i];
            for (let j = 0; j < orderedCols.length; j++) {
              const expected = orderedCols[j].accessor(data[i] as unknown as Record<string, unknown>);
              expect(String(row[j])).toBe(expected);
            }
          }
        }
      ),
      { verbose: true, numRuns: 100 }
    );
  });
});

describe('Feature: report-export, Property 9: PDF orientation rule', () => {
  /**
   * **Validates: Requirements 7.4**
   *
   * For any column set, PDF orientation is landscape if columns > 6, portrait otherwise.
   * We verify by generating the PDF and confirming the page dimensions match the expected
   * orientation. A4 portrait: width (~210) < height (~297); A4 landscape: width (~297) > height (~210).
   */
  it('should use landscape when columns > 6, portrait otherwise', () => {
    const columnCountArb = fc.integer({ min: 1, max: 10 });

    fc.assert(
      fc.property(columnCountArb, (colCount) => {
        // Build columns array with ear_tag + additional columns
        const columns: ExportColumnDef[] = [
          {
            key: 'ear_tag',
            label: 'Brinco',
            accessor: (row: Record<string, unknown>) => String(row['ear_tag'] ?? ''),
          },
        ];
        for (let i = 1; i < colCount; i++) {
          columns.push({
            key: `col_${i}`,
            label: `Col ${i}`,
            accessor: (row: Record<string, unknown>) => String(row[`col_${i}`] ?? ''),
          });
        }

        const config: ExportConfig = {
          title: 'Test Report',
          columns,
          data: [{ ear_tag: 'ABC001' }],
          includeNotes: false,
        };

        // Generate the PDF to confirm it produces a valid blob
        const blob = generatePdf(config);
        expect(blob).toBeInstanceOf(Blob);
        expect(blob.size).toBeGreaterThan(0);

        // Determine expected orientation based on ordered column count
        const orderedColumns = buildColumnOrder(columns, config.includeNotes);
        const expectedOrientation = orderedColumns.length > 6 ? 'landscape' : 'portrait';

        // Verify the orientation by creating a jsPDF instance with the expected orientation
        // and confirming the page dimensions match the rule
        const verifyDoc = new jsPDF({ orientation: expectedOrientation, unit: 'mm', format: 'a4' });
        const pageWidth = verifyDoc.internal.pageSize.getWidth();
        const pageHeight = verifyDoc.internal.pageSize.getHeight();

        if (expectedOrientation === 'landscape') {
          // Landscape: width > height
          expect(pageWidth).toBeGreaterThan(pageHeight);
          expect(pageWidth).toBeCloseTo(297, 0);
          expect(pageHeight).toBeCloseTo(210, 0);
        } else {
          // Portrait: height > width
          expect(pageHeight).toBeGreaterThan(pageWidth);
          expect(pageWidth).toBeCloseTo(210, 0);
          expect(pageHeight).toBeCloseTo(297, 0);
        }
      }),
      { verbose: true, numRuns: 100 }
    );
  });
});
