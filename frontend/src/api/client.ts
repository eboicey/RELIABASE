import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

export function unwrap<T>(promise: Promise<{ data: T }>): Promise<T> {
  return promise.then((res) => res.data);
}
