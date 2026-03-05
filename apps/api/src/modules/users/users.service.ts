import bcrypt from "bcrypt";
import crypto from "crypto";
import { AppError } from "../../common/errors";
import { parsePagination } from "../../common/pagination";
import { prisma } from "../../db/prisma";
import { audit } from "../../common/audit";

const BCRYPT_SALT_ROUNDS = 12;

function sanitizeUser(user: {
  id: string;
  organizationId: string;
  email: string;
  fullName: string;
  status: string;
  lastLoginAt: Date | null;
  createdAt: Date;
  updatedAt: Date;
}) {
  return {
    id: user.id,
    organizationId: user.organizationId,
    email: user.email,
    fullName: user.fullName,
    status: user.status,
    lastLoginAt: user.lastLoginAt,
    createdAt: user.createdAt,
    updatedAt: user.updatedAt
  };
}

export async function listUsers(input: {
  orgId: string;
  page?: number;
  pageSize?: number;
  q?: string;
  status?: "active" | "inactive" | "invited";
  sortBy?: "createdAt" | "fullName" | "email" | "status";
  sortDir?: "asc" | "desc";
}) {
  const pagination = parsePagination({
    page: input.page,
    pageSize: input.pageSize,
    sortBy: input.sortBy,
    sortDir: input.sortDir
  });

  const where = {
    organizationId: input.orgId,
    ...(input.status ? { status: input.status } : {}),
    ...(input.q
      ? {
          OR: [
            { email: { contains: input.q, mode: "insensitive" as const } },
            { fullName: { contains: input.q, mode: "insensitive" as const } }
          ]
        }
      : {})
  };

  const [total, users] = await Promise.all([
    prisma.user.count({ where }),
    prisma.user.findMany({
      where,
      skip: pagination.skip,
      take: pagination.take,
      orderBy: { [pagination.sortBy]: pagination.sortDir } as never
    })
  ]);

  return {
    data: users.map(sanitizeUser),
    meta: {
      page: pagination.page,
      pageSize: pagination.pageSize,
      total,
      sortBy: pagination.sortBy,
      sortDir: pagination.sortDir
    }
  };
}

export async function getUser(input: { orgId: string; id: string }) {
  const user = await prisma.user.findFirst({
    where: {
      id: input.id,
      organizationId: input.orgId
    }
  });

  if (!user) {
    throw new AppError(404, "USER_NOT_FOUND", "User not found");
  }

  return sanitizeUser(user);
}

export async function createUser(input: {
  orgId: string;
  actorUserId: string;
  email: string;
  fullName: string;
  password?: string;
  status?: "active" | "inactive" | "invited";
}) {
  const normalizedEmail = input.email.trim().toLowerCase();
  const existing = await prisma.user.findUnique({
    where: { email: normalizedEmail },
    select: { id: true }
  });
  if (existing) {
    throw new AppError(409, "EMAIL_EXISTS", "Email is already registered");
  }

  const status = input.status ?? "active";
  const effectivePassword = input.password ?? crypto.randomBytes(16).toString("hex");
  const passwordHash = await bcrypt.hash(effectivePassword, BCRYPT_SALT_ROUNDS);

  const created = await prisma.user.create({
    data: {
      organizationId: input.orgId,
      email: normalizedEmail,
      fullName: input.fullName.trim(),
      passwordHash,
      status
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "users.create",
    entityType: "user",
    entityId: created.id,
    metadata: {
      email: created.email,
      status: created.status
    }
  });

  return sanitizeUser(created);
}

export async function updateUser(input: {
  orgId: string;
  actorUserId: string;
  id: string;
  fullName?: string;
  status?: "active" | "inactive" | "invited";
}) {
  const existing = await prisma.user.findFirst({
    where: {
      id: input.id,
      organizationId: input.orgId
    },
    select: { id: true }
  });
  if (!existing) {
    throw new AppError(404, "USER_NOT_FOUND", "User not found");
  }

  const updated = await prisma.user.update({
    where: { id: input.id },
    data: {
      ...(input.fullName ? { fullName: input.fullName.trim() } : {}),
      ...(input.status ? { status: input.status } : {})
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "users.update",
    entityType: "user",
    entityId: updated.id,
    metadata: {
      fullName: updated.fullName,
      status: updated.status
    }
  });

  return sanitizeUser(updated);
}
