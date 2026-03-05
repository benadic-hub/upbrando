import { z } from "zod";

export const rolesListQuerySchema = z.object({
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
  sortBy: z.enum(["createdAt", "name"]).optional(),
  sortDir: z.enum(["asc", "desc"]).optional()
});

export const createRoleSchema = z.object({
  name: z.string().trim().min(2).max(120),
  description: z.string().trim().max(255).optional()
});

export const updateRoleSchema = z.object({
  name: z.string().trim().min(2).max(120).optional(),
  description: z.string().trim().max(255).nullable().optional()
});

export const roleIdParamsSchema = z.object({
  id: z.string().uuid()
});

export const replacePermissionsSchema = z.object({
  permissionCodes: z.array(z.string().trim().min(3).max(120)).default([])
});

export const assignRoleSchema = z.object({
  userId: z.string().uuid()
});
