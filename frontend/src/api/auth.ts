import { api } from "./client";
import type { Token, UserOut } from "./types";

export const authApi = {
  login: (email: string, password: string) => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return api
      .post<Token>("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      })
      .then((r) => r.data);
  },
  me: () => api.get<UserOut>("/api/auth/me").then((r) => r.data),
};
