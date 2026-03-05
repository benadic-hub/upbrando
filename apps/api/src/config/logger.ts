import pino from "pino";
import { env } from "./env";

export const logger = pino({
  level: env.ENV === "prod" ? "info" : "debug",
  redact: {
    paths: [
      "req.headers.cookie",
      "req.headers.authorization",
      "res.headers['set-cookie']",
      "password",
      "token",
      "refresh_token"
    ],
    censor: "[REDACTED]"
  }
});
