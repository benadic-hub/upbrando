import type { NextFunction, Request, Response } from "express";
import { Prisma } from "@prisma/client";
import { ZodError } from "zod";
import { AppError } from "../common/errors";
import { logger } from "../config/logger";

export function notFoundHandler(_req: Request, res: Response) {
  res.status(404).json({
    error: {
      code: "NOT_FOUND",
      message: "Route not found"
    }
  });
}

export function errorHandler(error: unknown, req: Request, res: Response, _next: NextFunction) {
  if (error instanceof AppError) {
    res.status(error.statusCode).json({
      error: {
        code: error.code,
        message: error.message,
        details: error.details
      }
    });
    return;
  }

  if (error instanceof ZodError) {
    res.status(400).json({
      error: {
        code: "VALIDATION_ERROR",
        message: "Invalid request",
        details: error.flatten()
      }
    });
    return;
  }

  // Express JSON parser errors should return 400 with a stable envelope.
  const syntaxErrorStatus = (error as { status?: unknown } | undefined)?.status;
  if (error instanceof SyntaxError && typeof syntaxErrorStatus === "number" && syntaxErrorStatus === 400 && "body" in error) {
    res.status(400).json({
      error: {
        code: "INVALID_JSON",
        message: "Request body is not valid JSON"
      }
    });
    return;
  }

  if (error instanceof Error && error.message === "Origin not allowed by CORS") {
    res.status(403).json({
      error: {
        code: "CORS_FORBIDDEN",
        message: "Origin not allowed by CORS policy"
      }
    });
    return;
  }

  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    const status = error.code === "P2002" ? 409 : 400;
    res.status(status).json({
      error: {
        code: "DATABASE_ERROR",
        message: error.message
      }
    });
    return;
  }

  logger.error(
    {
      err: error,
      requestId: req.requestId
    },
    "Unhandled error"
  );

  res.status(500).json({
    error: {
      code: "INTERNAL_SERVER_ERROR",
      message: "An unexpected error occurred"
    }
  });
}
