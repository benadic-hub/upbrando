import type { NextFunction, Request, Response } from "express";
import { prisma } from "../db/prisma";
import { AppError } from "../common/errors";

export function requirePermission(permissionCode: string) {
  return async (req: Request, _res: Response, next: NextFunction) => {
    try {
      if (!req.user) {
        throw new AppError(401, "UNAUTHORIZED", "Authentication required");
      }

      const userRoles = await prisma.userRole.findMany({
        where: {
          userId: req.user.userId,
          role: {
            organizationId: req.user.orgId
          }
        },
        select: {
          role: {
            select: {
              rolePermissions: {
                select: {
                  permission: {
                    select: {
                      code: true
                    }
                  }
                }
              }
            }
          }
        }
      });

      const permissions = new Set(
        userRoles.flatMap((userRole) => userRole.role.rolePermissions.map((rp) => rp.permission.code))
      );

      if (!permissions.has(permissionCode)) {
        throw new AppError(403, "FORBIDDEN", "Permission denied");
      }

      next();
    } catch (error) {
      next(error);
    }
  };
}
