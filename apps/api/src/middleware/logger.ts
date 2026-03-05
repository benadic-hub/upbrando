import type { NextFunction, Request, Response } from "express";
import { logger } from "../config/logger";

export function requestLogger(req: Request, res: Response, next: NextFunction) {
  const startedAt = process.hrtime.bigint();

  res.on("finish", () => {
    const durationMs = Number(process.hrtime.bigint() - startedAt) / 1_000_000;
    const payload = {
      requestId: req.requestId,
      method: req.method,
      path: req.originalUrl,
      status: res.statusCode,
      durationMs: Number(durationMs.toFixed(2))
    };

    if (res.statusCode >= 500) {
      logger.error(payload, "http_request");
      return;
    }
    if (res.statusCode >= 400) {
      logger.warn(payload, "http_request");
      return;
    }
    logger.info(payload, "http_request");
  });

  next();
}

