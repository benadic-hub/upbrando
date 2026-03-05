import { z } from "zod";

export const usersListQuerySchema = z.object({
  page: z.coerce.number().int().positive().optional(),
  pageSize: z.coerce.number().int().positive().max(100).optional(),
  q: z.string().trim().min(1).max(120).optional(),
  status: z.enum(["active", "inactive", "invited"]).optional(),
  sortBy: z.enum(["createdAt", "fullName", "email", "status"]).optional(),
  sortDir: z.enum(["asc", "desc"]).optional()
});

export const createUserSchema = z.object({
  email: z.string().trim().email().max(255),
  fullName: z.string().trim().min(2).max(120),
  password: z.string().min(8).max(128).optional(),
  status: z.enum(["active", "inactive", "invited"]).optional()
});

export const updateUserSchema = z.object({
  fullName: z.string().trim().min(2).max(120).optional(),
  status: z.enum(["active", "inactive", "invited"]).optional()
});

export const userIdParamsSchema = z.object({
  id: z.string().trim().min(1)
});
