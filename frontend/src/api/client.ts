import axios, { AxiosError } from "axios";
import type { ApiErrorDetail } from "./types";

export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || "http://localhost:8000";

const TOKEN_KEY = "timetable_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/** Listeners notified when the session is invalidated by a 401 response. */
type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken();
      unauthorizedListeners.forEach((listener) => listener());
    }
    return Promise.reject(error);
  },
);

/**
 * Pulls a human-readable message out of a FastAPI error response. 422 validation
 * errors carry `detail: ApiErrorDetail[]`; everything else is usually `detail: string`.
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: string | ApiErrorDetail[] } | undefined;
    if (data?.detail) {
      if (typeof data.detail === "string") return data.detail;
      if (Array.isArray(data.detail)) {
        return data.detail.map((d) => d.msg).join("; ");
      }
    }
    if (error.message) return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong";
}

/**
 * Maps a FastAPI 422 response onto a {fieldName: message} dictionary, keyed by the
 * last path segment of each error's `loc` (which is the Pydantic field name for
 * simple body models). Non-422 / non-field errors are ignored here; use
 * getErrorMessage for a general-purpose message instead.
 */
export function getFieldErrors(error: unknown): Record<string, string> {
  const result: Record<string, string> = {};
  if (axios.isAxiosError(error) && error.response?.status === 422) {
    const data = error.response.data as { detail?: ApiErrorDetail[] };
    if (Array.isArray(data?.detail)) {
      for (const item of data.detail) {
        const field = item.loc[item.loc.length - 1];
        if (typeof field === "string") {
          result[field] = item.msg;
        }
      }
    }
  }
  return result;
}
