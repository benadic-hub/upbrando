import { readFileSync } from "fs";
import path from "path";
import { Router } from "express";
import { authRouter } from "./modules/auth/auth.routes";
import { usersRouter } from "./modules/users/users.routes";
import { rolesRouter } from "./modules/roles/roles.routes";

const packageJsonPath = path.resolve(__dirname, "..", "package.json");
const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8")) as { version?: string };

export const apiRouter = Router();

apiRouter.get("/health", (_req, res) => {
  res.status(200).json({
    data: {
      ok: true
    }
  });
});

apiRouter.get("/version", (_req, res) => {
  res.status(200).json({
    data: {
      version: packageJson.version ?? "0.0.0"
    }
  });
});

apiRouter.use("/auth", authRouter);
apiRouter.use("/users", usersRouter);
apiRouter.use("/roles", rolesRouter);
