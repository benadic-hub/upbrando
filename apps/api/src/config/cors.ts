import type { CorsOptions } from "cors";
import { env } from "./env";

const devDefaults = ["http://localhost:5173"];
const prodDefaults = ["https://www.upbrando.com"];

const allowedOrigins =
  env.ENV === "prod"
    ? prodDefaults
    : Array.from(new Set([...devDefaults, ...env.CORS_ALLOWED_ORIGINS_LIST]));

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
