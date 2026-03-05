import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";
import { env } from "../config/env";
import { AppError } from "../common/errors";

type AccessPayload = {
  sub: string;
  org: string;
};

export function requireAuth(req: Request, _res: Response, next: NextFunction) {
  const token = req.cookies?.[env.AUTH_ACCESS_COOKIE_NAME];
  if (!token) {
    next(new AppError(401, "UNAUTHORIZED", "Authentication required"));
    return;
  }

  try {
    const decoded = jwt.verify(token, env.JWT_ACCESS_SECRET) as AccessPayload;
    req.user = {
      userId: decoded.sub,
      orgId: decoded.org
    };
    next();
  } catch {
    next(new AppError(401, "UNAUTHORIZED", "Invalid or expired access token"));
  }
}
