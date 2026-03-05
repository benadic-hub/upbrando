import type { NextFunction, Request, Response } from "express";
import { randomUUID } from "crypto";

export function requestIdMiddleware(req: Request, res: Response, next: NextFunction) {
  const incoming = req.header("X-Request-ID");
  const id = incoming && incoming.trim() ? incoming : randomUUID();
  req.requestId = id;
  res.setHeader("X-Request-ID", id);
  next();
}
