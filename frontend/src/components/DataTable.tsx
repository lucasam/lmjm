import { useTranslation } from 'react-i18next';

export interface Column<T> {
  header: React.ReactNode;
  accessor: (row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  keyExtractor: (row: T, index: number) => string;
}

export default function DataTable<T>({
  columns,
  data,
  onRowClick,
  keyExtractor,
}: DataTableProps<T>) {
  const { t } = useTranslation();

  if (data.length === 0) {
    return <div className="table-empty">{t('common.noData')}</div>;
  }

  return (
    <div className="table-wrapper">
      <table className="table">
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th key={i}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={keyExtractor(row, rowIdx)}
              className={onRowClick ? 'table-row-clickable' : undefined}
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
                <td key={colIdx}>{col.accessor(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
