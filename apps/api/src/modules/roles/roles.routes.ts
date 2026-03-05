import { Router } from "express";
import { requireAuth } from "../../middleware/auth";
import { requirePermission } from "../../middleware/permissions";
import { validate } from "../../middleware/validate";
import { rolesController } from "./roles.controller";
import { asyncHandler } from "../../common/asyncHandler";
import {
  assignRoleSchema,
  createRoleSchema,
  replacePermissionsSchema,
  roleIdParamsSchema,
  roleUsersQuerySchema,
  rolesListQuerySchema,
  updateRoleSchema
} from "./roles.schemas";

export const rolesRouter = Router();

rolesRouter.use(requireAuth);

rolesRouter.get("/", requirePermission("roles.read"), validate({ query: rolesListQuerySchema }), asyncHandler(rolesController.list));
rolesRouter.post("/", requirePermission("roles.write"), validate({ body: createRoleSchema }), asyncHandler(rolesController.create));
rolesRouter.patch(
  "/:id",
  requirePermission("roles.write"),
  validate({ params: roleIdParamsSchema, body: updateRoleSchema }),
  asyncHandler(rolesController.patch)
);
rolesRouter.get(
  "/:id/permissions",
  requirePermission("roles.read"),
  validate({ params: roleIdParamsSchema }),
  asyncHandler(rolesController.permissions)
);
rolesRouter.get(
  "/:id/users",
  requirePermission("roles.read"),
  validate({ params: roleIdParamsSchema, query: roleUsersQuerySchema }),
  asyncHandler(rolesController.users)
);
rolesRouter.post(
  "/:id/permissions",
  requirePermission("roles.write"),
  validate({ params: roleIdParamsSchema, body: replacePermissionsSchema }),
  asyncHandler(rolesController.replacePermissions)
);
rolesRouter.post(
  "/:id/assign",
  requirePermission("roles.write"),
  validate({ params: roleIdParamsSchema, body: assignRoleSchema }),
  asyncHandler(rolesController.assign)
);
rolesRouter.post(
  "/:id/unassign",
  requirePermission("roles.write"),
  validate({ params: roleIdParamsSchema, body: assignRoleSchema }),
  asyncHandler(rolesController.unassign)
);
