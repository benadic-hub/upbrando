import type { Request, Response } from "express";
import { AppError } from "../../common/errors";
import { createUser, getUser, listUsers, updateUser } from "./users.service";

export const usersController = {
  async list(req: Request, res: Response) {
    if (!req.user?.orgId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const result = await listUsers({
      orgId: req.user.orgId,
      ...req.query
    });
    res.status(200).json(result);
  },

  async getById(req: Request, res: Response) {
    if (!req.user?.orgId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const data = await getUser({
      orgId: req.user.orgId,
      id: req.params.id
    });
    res.status(200).json({ data });
  },

  async create(req: Request, res: Response) {
    if (!req.user?.orgId || !req.user.userId) {
      throw new AppError(401, "UNAUTHORIZED", "Authentication required");
    }
    const data = await createUser({
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
    const data = await updateUser({
      orgId: req.user.orgId,
      actorUserId: req.user.userId,
      id: req.params.id,
      ...req.body
    });
    res.status(200).json({ data });
  }
};
