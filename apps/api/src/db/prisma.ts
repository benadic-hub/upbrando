import { PrismaClient } from "@prisma/client";
import { env } from "../config/env";

declare global {
  // eslint-disable-next-line no-var
  var __upbrandoPrisma__: PrismaClient | undefined;
}

export const prisma =
  global.__upbrandoPrisma__ ??
  new PrismaClient({
    datasources: {
      db: { url: env.DATABASE_URL }
    }
  });

if (env.ENV !== "prod") {
  global.__upbrandoPrisma__ = prisma;
}
