import type { ApiResponse } from "@shared/types/api";
import type { AuthMeData } from "@shared/types/auth";
import { http } from "./http";

export type LoginInput = {
  email: string;
  password: string;
};

export type ForgotPasswordInput = {
  email: string;
};

export type ResetPasswordInput = {
  token: string;
  newPassword: string;
};

export const authApi = {
  me() {
    return http.get<ApiResponse<AuthMeData>>("/auth/me");
  },
  login(input: LoginInput) {
    return http.post<ApiResponse<AuthMeData>, LoginInput>("/auth/login", input);
  },
  logout() {
    return http.post<ApiResponse<{ ok: true }>>("/auth/logout");
  },
  forgotPassword(input: ForgotPasswordInput) {
    return http.post<ApiResponse<{ ok: true }>, ForgotPasswordInput>("/auth/forgot-password", input);
  },
  resetPassword(input: ResetPasswordInput) {
    return http.post<ApiResponse<{ ok: true }>, ResetPasswordInput>("/auth/reset-password", input);
  }
};
