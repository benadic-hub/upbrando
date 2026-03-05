import { Router } from "express";
import { usersController } from "./users.controller";
import { requireAuth } from "../../middleware/auth";
import { requirePermission } from "../../middleware/permissions";
import { validate } from "../../middleware/validate";
import { createUserSchema, updateUserSchema, userIdParamsSchema, usersListQuerySchema } from "./users.schemas";
import { asyncHandler } from "../../common/asyncHandler";

export const usersRouter = Router();

usersRouter.use(requireAuth);

usersRouter.get("/", requirePermission("users.read"), validate({ query: usersListQuerySchema }), asyncHandler(usersController.list));
usersRouter.get(
  "/:id",
  requirePermission("users.read"),
  validate({ params: userIdParamsSchema }),
  asyncHandler(usersController.getById)
);
usersRouter.post("/", requirePermission("users.write"), validate({ body: createUserSchema }), asyncHandler(usersController.create));
usersRouter.patch(
  "/:id",
  requirePermission("users.write"),
  validate({ params: userIdParamsSchema, body: updateUserSchema }),
  asyncHandler(usersController.patch)
);
