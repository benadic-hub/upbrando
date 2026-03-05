import type { CorsOptions } from "cors";
import { env } from "./env";

const allowedOrigins = Array.from(
  new Set(
    env.ENV === "prod"
      ? ["https://www.upbrando.com", ...env.CORS_ALLOWED_ORIGINS_LIST]
      : env.CORS_ALLOWED_ORIGINS_LIST
  )
);

export const corsOptions: CorsOptions = {
  origin(origin, callback) {
    if (!origin) {
      callback(null, true);
      return;
    }
    if (allowedOrigins.includes(origin)) {
      callback(null, true);
      return;
    }
    callback(new Error("Origin not allowed by CORS"));
  },
  credentials: true,
  methods: ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
  allowedHeaders: ["Content-Type", "X-Request-ID"]
};
