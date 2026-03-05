import type { ReactNode } from "react";

type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
};

type TableProps<T> = {
  columns: Array<Column<T>>;
  rows: T[];
  rowKey: (row: T) => string;
  emptyText?: string;
};

export function Table<T>({ columns, rows, rowKey, emptyText = "No records found." }: TableProps<T>) {
  return (
    <div className="overflow-hidden rounded-md border border-border bg-surface shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-bg">
            <tr>
              {columns.map((column) => (
                <th key={column.key} className="px-4 py-3 font-semibold text-text">
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-muted" colSpan={columns.length}>
                  {emptyText}
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={rowKey(row)} className="border-t border-border">
                  {columns.map((column) => (
                    <td key={column.key} className="px-4 py-3 text-text">
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
