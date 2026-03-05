export type PaginationInput = {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortDir?: "asc" | "desc";
};

export function parsePagination(input: PaginationInput) {
  const page = Math.max(1, input.page ?? 1);
  const pageSize = Math.min(100, Math.max(1, input.pageSize ?? 20));
  const sortBy = input.sortBy ?? "createdAt";
  const sortDir = input.sortDir ?? "desc";

  return {
    page,
    pageSize,
    sortBy,
    sortDir,
    skip: (page - 1) * pageSize,
    take: pageSize
  };
}
