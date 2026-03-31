import { useTranslation } from 'react-i18next';

export interface Column<T> {
  header: string;
  accessor: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  keyExtractor: (row: T, index: number) => string;
}

const wrapperStyle: React.CSSProperties = {
  overflowX: 'auto',
  WebkitOverflowScrolling: 'touch',
  width: '100%',
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
  fontSize: '0.9rem',
};

const thStyle: React.CSSProperties = {
  textAlign: 'left',
  padding: '0.75rem 0.5rem',
  borderBottom: '2px solid #ddd',
  whiteSpace: 'nowrap',
  fontWeight: 600,
  backgroundColor: '#f5f5f5',
};

const tdStyle: React.CSSProperties = {
  padding: '0.75rem 0.5rem',
  borderBottom: '1px solid #eee',
  whiteSpace: 'nowrap',
};

const clickableRowStyle: React.CSSProperties = {
  cursor: 'pointer',
  minHeight: '44px',
};

const emptyStyle: React.CSSProperties = {
  padding: '2rem',
  textAlign: 'center',
  color: '#888',
};

export default function DataTable<T>({
  columns,
  data,
  onRowClick,
  keyExtractor,
}: DataTableProps<T>) {
  const { t } = useTranslation();

  if (data.length === 0) {
    return <div style={emptyStyle}>{t('common.noData')}</div>;
  }

  return (
    <div style={wrapperStyle}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i} style={thStyle}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={keyExtractor(row, rowIdx)}
              style={onRowClick ? clickableRowStyle : undefined}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              role={onRowClick ? 'button' : undefined}
              onKeyDown={
                onRowClick
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onRowClick(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((col, colIdx) => (
                <td key={colIdx} style={tdStyle}>
                  {col.accessor(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
