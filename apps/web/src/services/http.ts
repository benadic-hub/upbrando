import type { ApiError } from "@shared/types/api";

type HttpMethod = "GET" | "POST" | "PATCH";
type QueryParams = Record<string, string | number | boolean | undefined | null>;

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5173";

export class HttpError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, payload: ApiError["error"]) {
    super(payload.message);
    this.status = status;
    this.code = payload.code;
    this.details = payload.details;
  }
}

function toQueryString(params?: QueryParams): string {
  if (!params) {
    return "";
  }
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    search.set(key, String(value));
  });
  const raw = search.toString();
  return raw ? `?${raw}` : "";
}

async function request<TResponse, TBody = unknown>(
  method: HttpMethod,
  path: string,
  body?: TBody,
  query?: QueryParams
): Promise<TResponse> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${baseUrl}/api/v1${normalizedPath}${toQueryString(query)}`;

  const response = await fetch(url, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json"
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  });

  const payload = (await response.json().catch(() => null)) as TResponse | ApiError | null;

  if (!response.ok) {
    const fallback: ApiError = {
      error: {
        code: "HTTP_ERROR",
        message: "Request failed"
      }
    };
    const errorPayload =
      payload && typeof payload === "object" && "error" in payload ? (payload as ApiError) : fallback;
    throw new HttpError(response.status, errorPayload.error);
  }

  return payload as TResponse;
}

export const http = {
  get<TResponse>(path: string, query?: QueryParams) {
    return request<TResponse>("GET", path, undefined, query);
  },
  post<TResponse, TBody = unknown>(path: string, body?: TBody) {
    return request<TResponse, TBody>("POST", path, body);
  },
  patch<TResponse, TBody = unknown>(path: string, body?: TBody) {
    return request<TResponse, TBody>("PATCH", path, body);
  }
};

export function getErrorMessage(error: unknown): string {
  if (error instanceof HttpError) {
    return error.message;
  }
  return "Something went wrong. Please try again.";
}
