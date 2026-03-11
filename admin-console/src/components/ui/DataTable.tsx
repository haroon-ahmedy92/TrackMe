import { ReactNode } from 'react';

interface Column<T> {
  key: string;
  header: string;
  cell: (item: T) => ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
}

export function DataTable<T>({ columns, rows, rowKey, emptyMessage = 'No records available' }: DataTableProps<T>) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'separate', borderSpacing: 0 }}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                style={{
                  textAlign: 'left',
                  padding: '10px 12px',
                  borderBottom: '1px solid var(--border)',
                  color: 'var(--text-muted)',
                  fontSize: 12,
                  fontWeight: 600,
                  width: column.width,
                }}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} style={{ padding: '11px 12px', borderBottom: '1px solid var(--border)', verticalAlign: 'top' }}>
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 ? (
        <p className="text-muted" style={{ marginTop: 10 }}>
          {emptyMessage}
        </p>
      ) : null}
    </div>
  );
}
