import "dotenv/config";
import { z } from "zod";

const boolFromEnv = z
  .union([z.boolean(), z.string()])
  .transform((value) => {
    if (typeof value === "boolean") {
      return value;
    }
    return ["1", "true", "yes", "on"].includes(value.toLowerCase());
  });

const envSchema = z.object({
  ENV: z.enum(["dev", "prod"]).default("dev"),
  PORT: z.coerce.number().int().positive().default(5174),
  DATABASE_URL: z.string().min(1, "DATABASE_URL is required"),
  COOKIE_SECRET: z.string().min(16, "COOKIE_SECRET must be at least 16 characters"),
  COOKIE_NAME: z.string().min(1).default("sid"),
  CORS_ORIGIN: z.string().url("CORS_ORIGIN must be a valid URL"),
  CORS_ALLOWED_ORIGINS: z.string().optional(),
  JWT_ACCESS_SECRET: z.string().min(32).optional(),
  JWT_REFRESH_SECRET: z.string().min(32).optional(),
  JWT_ACCESS_EXPIRES_IN: z.string().default("15m"),
  JWT_REFRESH_EXPIRES_IN: z.string().default("30d"),
  AUTH_ACCESS_COOKIE_NAME: z.string().min(1).optional(),
  AUTH_REFRESH_COOKIE_NAME: z.string().min(1).optional(),
  AUTH_COOKIE_DOMAIN: z.string().default(""),
  AUTH_COOKIE_SAMESITE: z.enum(["lax", "strict", "none"]).default("lax"),
  AUTH_COOKIE_SECURE: boolFromEnv.optional()
});

const parsed = envSchema.safeParse(process.env);
if (!parsed.success) {
  const message = parsed.error.issues.map((issue) => `${issue.path.join(".")}: ${issue.message}`).join("; ");
  throw new Error(`Invalid environment configuration: ${message}`);
}

const parsedEnv = parsed.data;

const authCookieSecure =
  typeof parsedEnv.AUTH_COOKIE_SECURE === "boolean"
    ? parsedEnv.AUTH_COOKIE_SECURE
    : parsedEnv.ENV === "prod";

if (parsedEnv.ENV === "prod" && !authCookieSecure) {
  throw new Error("AUTH_COOKIE_SECURE must be true in prod");
}

export const env = {
  ...parsedEnv,
  JWT_ACCESS_SECRET: parsedEnv.JWT_ACCESS_SECRET ?? parsedEnv.COOKIE_SECRET,
  JWT_REFRESH_SECRET: parsedEnv.JWT_REFRESH_SECRET ?? parsedEnv.COOKIE_SECRET,
  AUTH_ACCESS_COOKIE_NAME: parsedEnv.AUTH_ACCESS_COOKIE_NAME ?? parsedEnv.COOKIE_NAME,
  AUTH_REFRESH_COOKIE_NAME: parsedEnv.AUTH_REFRESH_COOKIE_NAME ?? `${parsedEnv.COOKIE_NAME}_refresh`,
  AUTH_COOKIE_SECURE: authCookieSecure,
  CORS_ALLOWED_ORIGINS_LIST: [parsedEnv.CORS_ORIGIN, ...(parsedEnv.CORS_ALLOWED_ORIGINS ?? "").split(",")]
    .map((origin) => origin.trim())
    .filter(Boolean)
} as const;

export type AppEnv = typeof env;
