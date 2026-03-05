import type { Request, Response } from "express";
import {
  clearAuthCookies,
  forgotPassword,
  login,
  me,
  register,
  resetPassword,
  setAuthCookies,
  logout as logoutSession
} from "./auth.service";
import { AppError } from "../../common/errors";
import { env } from "../../config/env";

export const authController = {
  async register(req: Request, res: Response) {
    const result = await register(req.body, {
      userAgent: req.get("user-agent") ?? undefined,
      ip: req.ip
    });
    setAuthCookies(res, result.tokens);
    res.status(201).json({
      data: result.authContext
    });
  },

  async login(req: Request, res: Response) {
    const result = await login(req.body, {
      userAgent: req.get("user-agent") ?? undefined,
      ip: req.ip
    });
    setAuthCookies(res, result.tokens);
    res.status(200).json({
      data: result.authContext
    });
  },

  async logout(req: Request, res: Response) {
    const refreshToken = req.cookies?.[env.AUTH_REFRESH_COOKIE_NAME];
    await logoutSession({
      refreshToken,
      actorUserId: req.user?.userId,
      orgId: req.user?.orgId
    });
    clearAuthCookies(res);
    res.status(200).json({
      data: {
        ok: true
      }
    });
  },

  async forgotPassword(req: Request, res: Response) {
    await forgotPassword(req.body);
    res.status(200).json({
      data: {
        ok: true
      }
    });
  },

  async resetPassword(req: Request, res: Response) {
    await resetPassword(req.body);
    res.status(200).json({
      data: {
        ok: true
      }
    });
  },

  async me(req: Request, res: Response) {
    if (!req.user?.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const data = await me({ userId: req.user.userId });
    res.status(200).json({
      data
    });
  }
};
