import type { Request, Response } from "express";
import { AppError } from "../../common/errors";
import {
  assignRoleToUser,
  createRole,
  getRolePermissionCodes,
  listRoleUsers,
  listRoles,
  replaceRolePermissions,
  unassignRoleFromUser,
  updateRole
} from "./roles.service";

export const rolesController = {
  async list(req: Request, res: Response) {
    if (!req.user?.orgId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const result = await listRoles({
      orgId: req.user.orgId,
      ...req.query
    });
    res.status(200).json(result);
  },

  async create(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const data = await createRole({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      ...req.body
    });
    res.status(201).json({ data });
  },

  async patch(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const data = await updateRole({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      roleId: req.params.id,
      ...req.body
    });
    res.status(200).json({ data });
  },

  async permissions(req: Request, res: Response) {
    if (!req.user?.orgId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const codes = await getRolePermissionCodes({
      orgId: req.user.orgId,
      roleId: req.params.id
    });
    res.status(200).json({
      data: {
        permissionCodes: codes
      }
    });
  },

  async users(req: Request, res: Response) {
    if (!req.user?.orgId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const result = await listRoleUsers({
      orgId: req.user.orgId,
      roleId: req.params.id,
      ...req.query
    });
    res.status(200).json(result);
  },

  async replacePermissions(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    await replaceRolePermissions({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      roleId: req.params.id,
      permissionCodes: req.body.permissionCodes
    });
    res.status(200).json({
      data: {
        ok: true
      }
    });
  },

  async assign(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    await assignRoleToUser({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      roleId: req.params.id,
      userId: req.body.userId
    });
    res.status(200).json({
      data: {
        ok: true
      }
    });
  },

  async unassign(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    await unassignRoleFromUser({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      roleId: req.params.id,
      userId: req.body.userId
    });
    res.status(200).json({
      data: {
        ok: true
      }
    });
  }
};
