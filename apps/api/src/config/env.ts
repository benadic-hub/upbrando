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

const envSchema = z
  .object({
    ENV: z.enum(["dev", "prod"]).default("dev"),
    PORT: z.coerce.number().int().positive().default(8000),
    DATABASE_URL: z.string().min(1),
    JWT_ACCESS_SECRET: z.string().min(32),
    JWT_REFRESH_SECRET: z.string().min(32),
    JWT_ACCESS_EXPIRES_IN: z.string().default("15m"),
    JWT_REFRESH_EXPIRES_IN: z.string().default("30d"),
    AUTH_COOKIE_DOMAIN: z.string().default(".upbrando.com"),
    AUTH_COOKIE_SAMESITE: z.enum(["lax", "strict", "none"]).default("lax"),
    AUTH_COOKIE_SECURE: boolFromEnv.optional(),
    CORS_ALLOWED_ORIGINS: z.string().default("http://localhost:5173")
  })
  .superRefine((cfg, ctx) => {
    if (cfg.ENV === "prod" && !cfg.CORS_ALLOWED_ORIGINS.includes("https://www.upbrando.com")) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["CORS_ALLOWED_ORIGINS"],
        message: "CORS_ALLOWED_ORIGINS must include https://www.upbrando.com in prod"
      });
    }
    if (cfg.ENV === "prod" && cfg.AUTH_COOKIE_SAMESITE !== "lax") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["AUTH_COOKIE_SAMESITE"],
        message: "AUTH_COOKIE_SAMESITE must be lax in prod for WWW rewrite model"
      });
    }
    if (cfg.ENV === "prod" && cfg.AUTH_COOKIE_DOMAIN !== ".upbrando.com") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["AUTH_COOKIE_DOMAIN"],
        message: "AUTH_COOKIE_DOMAIN must be .upbrando.com in prod"
      });
    }
  });

const parsedEnv = envSchema.parse(process.env);

const authCookieSecure =
  typeof parsedEnv.AUTH_COOKIE_SECURE === "boolean"
    ? parsedEnv.AUTH_COOKIE_SECURE
    : parsedEnv.ENV === "prod";

if (parsedEnv.ENV === "prod" && !authCookieSecure) {
  throw new Error("AUTH_COOKIE_SECURE must be true in prod");
}

export const env = {
  ...parsedEnv,
  AUTH_COOKIE_SECURE: authCookieSecure,
  CORS_ALLOWED_ORIGINS_LIST: parsedEnv.CORS_ALLOWED_ORIGINS.split(",")
    .map((origin) => origin.trim())
    .filter(Boolean)
} as const;

export type AppEnv = typeof env;
