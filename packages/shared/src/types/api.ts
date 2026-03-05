export type ApiError = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export type ApiResponse<T> = {
  data: T;
};

export type ListMeta = {
  page: number;
  pageSize: number;
  total: number;
  sortBy: string;
  sortDir: "asc" | "desc";
};

export type ListResponse<T> = {
  data: T[];
  meta: ListMeta;
};
