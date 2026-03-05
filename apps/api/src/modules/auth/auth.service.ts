import bcrypt from "bcrypt";
import crypto, { randomUUID } from "crypto";
import jwt from "jsonwebtoken";
import type { Response } from "express";
import type { Prisma, UserStatus } from "@prisma/client";
import { prisma } from "../../db/prisma";
import { env } from "../../config/env";
import { AppError } from "../../common/errors";
import { audit } from "../../common/audit";

const ACCESS_COOKIE_NAME = env.AUTH_ACCESS_COOKIE_NAME;
const REFRESH_COOKIE_NAME = env.AUTH_REFRESH_COOKIE_NAME;
const BCRYPT_SALT_ROUNDS = 12;
const MINIMAL_PERMISSION_CODES = ["auth.read", "auth.write", "users.read", "users.write", "roles.read", "roles.write"];

function parseDurationToMs(duration: string, fallbackMs: number): number {
  const normalized = duration.trim().toLowerCase();
  const match = normalized.match(/^(\d+)([mhd])$/);
  if (!match) {
    return fallbackMs;
  }
  const value = Number(match[1]);
  const unit = match[2];
  if (unit === "m") {
    return value * 60 * 1000;
  }
  if (unit === "h") {
    return value * 60 * 60 * 1000;
  }
  return value * 24 * 60 * 60 * 1000;
}

function hashToken(rawToken: string): string {
  return crypto.createHash("sha256").update(rawToken).digest("hex");
}

function authCookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: env.AUTH_COOKIE_SECURE,
    sameSite: env.AUTH_COOKIE_SAMESITE,
    domain: env.AUTH_COOKIE_DOMAIN || undefined,
    path: "/",
    maxAge
  } as const;
}

type AuthContext = {
  user: {
    id: string;
    organizationId: string;
    email: string;
    fullName: string;
    status: UserStatus;
    lastLoginAt: Date | null;
    createdAt: Date;
    updatedAt: Date;
  };
  organization: {
    id: string;
    name: string;
    domain: string | null;
    createdAt: Date;
    updatedAt: Date;
  };
  roles: Array<{
    id: string;
    organizationId: string;
    name: string;
    description: string | null;
    createdAt: Date;
    updatedAt: Date;
  }>;
  permissions: string[];
};

async function ensureGlobalPermissions(tx: Prisma.TransactionClient) {
  for (const code of MINIMAL_PERMISSION_CODES) {
    await tx.permission.upsert({
      where: { code },
      update: {},
      create: {
        code,
        description: `${code} permission`
      }
    });
  }
}

async function getAuthContext(userId: string): Promise<AuthContext> {
  const user = await prisma.user.findUnique({
    where: { id: userId },
    include: {
      organization: true,
      userRoles: {
        include: {
          role: {
            include: {
              rolePermissions: {
                include: {
                  permission: true
                }
              }
            }
          }
        }
      }
    }
  });

  if (!user) {
    throw new AppError(401, "UNAUTHORIZED", "User not found");
  }

  const roles = user.userRoles.map((item) => item.role);
  const permissions = Array.from(
    new Set(
      user.userRoles.flatMap((item) => item.role.rolePermissions.map((permissionItem) => permissionItem.permission.code))
    )
  );

  return {
    user: {
      id: user.id,
      organizationId: user.organizationId,
      email: user.email,
      fullName: user.fullName,
      status: user.status,
      lastLoginAt: user.lastLoginAt,
      createdAt: user.createdAt,
      updatedAt: user.updatedAt
    },
    organization: {
      id: user.organization.id,
      name: user.organization.name,
      domain: user.organization.domain,
      createdAt: user.organization.createdAt,
      updatedAt: user.organization.updatedAt
    },
    roles: roles.map((role) => ({
      id: role.id,
      organizationId: role.organizationId,
      name: role.name,
      description: role.description,
      createdAt: role.createdAt,
      updatedAt: role.updatedAt
    })),
    permissions
  };
}

async function buildTokens(input: {
  userId: string;
  orgId: string;
  userAgent?: string;
  ip?: string;
}) {
  const accessTtlMs = parseDurationToMs(env.JWT_ACCESS_EXPIRES_IN, 15 * 60 * 1000);
  const refreshTtlMs = parseDurationToMs(env.JWT_REFRESH_EXPIRES_IN, 30 * 24 * 60 * 60 * 1000);
  const sessionId = randomUUID();
  const refreshExpiresAt = new Date(Date.now() + refreshTtlMs);

  await prisma.userSession.create({
    data: {
      id: sessionId,
      userId: input.userId,
      refreshTokenHash: "",
      userAgent: input.userAgent ?? null,
      ip: input.ip ?? null,
      expiresAt: refreshExpiresAt
    }
  });

  const refreshToken = jwt.sign(
    {
      sub: input.userId,
      sid: sessionId,
      org: input.orgId
    },
    env.JWT_REFRESH_SECRET,
    { expiresIn: Math.floor(refreshTtlMs / 1000) }
  );

  await prisma.userSession.update({
    where: { id: sessionId },
    data: {
      refreshTokenHash: hashToken(refreshToken)
    }
  });

  const accessToken = jwt.sign(
    {
      sub: input.userId,
      org: input.orgId
    },
    env.JWT_ACCESS_SECRET,
    { expiresIn: Math.floor(accessTtlMs / 1000) }
  );

  return {
    accessToken,
    refreshToken,
    accessTtlMs,
    refreshTtlMs
  };
}

export function setAuthCookies(
  res: Response,
  payload: { accessToken: string; refreshToken: string; accessTtlMs: number; refreshTtlMs: number }
) {
  res.cookie(ACCESS_COOKIE_NAME, payload.accessToken, authCookieOptions(payload.accessTtlMs));
  res.cookie(REFRESH_COOKIE_NAME, payload.refreshToken, authCookieOptions(payload.refreshTtlMs));
}

export function clearAuthCookies(res: Response) {
  const clearOptions = {
    httpOnly: true,
    secure: env.AUTH_COOKIE_SECURE,
    sameSite: env.AUTH_COOKIE_SAMESITE,
    domain: env.AUTH_COOKIE_DOMAIN || undefined,
    path: "/",
    expires: new Date(0),
    maxAge: 0
  } as const;
  res.cookie(ACCESS_COOKIE_NAME, "", clearOptions);
  res.cookie(REFRESH_COOKIE_NAME, "", clearOptions);
}

export async function register(
  input: {
    organizationName: string;
    fullName: string;
    email: string;
    password: string;
  },
  context: {
    userAgent?: string;
    ip?: string;
  }
) {
  const normalizedEmail = input.email.trim().toLowerCase();
  const existing = await prisma.user.findUnique({
    where: { email: normalizedEmail },
    select: { id: true }
  });
  if (existing) {
    throw new AppError(409, "EMAIL_EXISTS", "Email is already registered");
  }

  const passwordHash = await bcrypt.hash(input.password, BCRYPT_SALT_ROUNDS);

  const created = await prisma.$transaction(async (tx) => {
    await ensureGlobalPermissions(tx);
    const organization = await tx.organization.create({
      data: {
        name: input.organizationName.trim()
      }
    });

    const adminRole = await tx.role.create({
      data: {
        organizationId: organization.id,
        name: "Admin",
        description: "Default admin role for organization"
      }
    });

    const permissions = await tx.permission.findMany({
      where: {
        code: { in: MINIMAL_PERMISSION_CODES }
      },
      select: { id: true, code: true }
    });

    if (permissions.length) {
      await tx.rolePermission.createMany({
        data: permissions.map((permission) => ({
          roleId: adminRole.id,
          permissionId: permission.id
        })),
        skipDuplicates: true
      });
    }

    const user = await tx.user.create({
      data: {
        organizationId: organization.id,
        email: normalizedEmail,
        passwordHash,
        fullName: input.fullName.trim(),
        status: "active"
      }
    });

    await tx.userRole.create({
      data: {
        userId: user.id,
        roleId: adminRole.id
      }
    });

    return {
      organizationId: organization.id,
      userId: user.id
    };
  });

  const authContext = await getAuthContext(created.userId);
  const tokens = await buildTokens({
    userId: created.userId,
    orgId: created.organizationId,
    userAgent: context.userAgent,
    ip: context.ip
  });

  await audit.log({
    orgId: created.organizationId,
    actorUserId: created.userId,
    eventType: "auth.register",
    entityType: "user",
    entityId: created.userId,
    metadata: { email: normalizedEmail }
  });

  return {
    authContext,
    tokens
  };
}

export async function login(
  input: { email: string; password: string },
  context: {
    userAgent?: string;
    ip?: string;
  }
) {
  const normalizedEmail = input.email.trim().toLowerCase();
  const user = await prisma.user.findUnique({
    where: { email: normalizedEmail }
  });

  if (!user) {
    throw new AppError(401, "INVALID_CREDENTIALS", "Invalid email or password");
  }

  const isValid = await bcrypt.compare(input.password, user.passwordHash);
  if (!isValid) {
    throw new AppError(401, "INVALID_CREDENTIALS", "Invalid email or password");
  }

  if (user.status !== "active") {
    throw new AppError(403, "ACCOUNT_INACTIVE", "User account is not active");
  }

  await prisma.user.update({
    where: { id: user.id },
    data: { lastLoginAt: new Date() }
  });

  const authContext = await getAuthContext(user.id);
  const tokens = await buildTokens({
    userId: user.id,
    orgId: user.organizationId,
    userAgent: context.userAgent,
    ip: context.ip
  });

  await audit.log({
    orgId: user.organizationId,
    actorUserId: user.id,
    eventType: "auth.login",
    entityType: "user",
    entityId: user.id
  });

  return {
    authContext,
    tokens
  };
}

export async function logout(input: { refreshToken?: string; actorUserId?: string; orgId?: string }) {
  if (input.refreshToken) {
    const tokenHash = hashToken(input.refreshToken);
    await prisma.userSession.updateMany({
      where: {
        refreshTokenHash: tokenHash,
        revokedAt: null
      },
      data: {
        revokedAt: new Date()
      }
    });
  }

  await audit.log({
    orgId: input.orgId ?? null,
    actorUserId: input.actorUserId ?? null,
    eventType: "auth.logout"
  });
}

export async function forgotPassword(input: { email: string }) {
  const normalizedEmail = input.email.trim().toLowerCase();
  const user = await prisma.user.findUnique({
    where: { email: normalizedEmail }
  });

  if (user) {
    const rawToken = crypto.randomBytes(32).toString("hex");
    const tokenHash = hashToken(rawToken);
    const expiresAt = new Date(Date.now() + 15 * 60 * 1000);

    await prisma.passwordResetToken.create({
      data: {
        userId: user.id,
        tokenHash,
        expiresAt
      }
    });

    await audit.log({
      orgId: user.organizationId,
      actorUserId: user.id,
      eventType: "auth.forgot_password",
      entityType: "user",
      entityId: user.id
    });
  } else {
    await audit.log({
      eventType: "auth.forgot_password",
      metadata: { email: normalizedEmail }
    });
  }
}

export async function resetPassword(input: { token: string; newPassword: string }) {
  const tokenHash = hashToken(input.token);
  const now = new Date();
  const tokenRecord = await prisma.passwordResetToken.findFirst({
    where: {
      tokenHash,
      usedAt: null,
      expiresAt: {
        gt: now
      }
    },
    include: {
      user: true
    }
  });

  if (!tokenRecord) {
    throw new AppError(400, "INVALID_RESET_TOKEN", "Invalid or expired reset token");
  }

  const passwordHash = await bcrypt.hash(input.newPassword, BCRYPT_SALT_ROUNDS);

  await prisma.$transaction(async (tx) => {
    await tx.user.update({
      where: { id: tokenRecord.userId },
      data: { passwordHash }
    });
    await tx.passwordResetToken.update({
      where: { id: tokenRecord.id },
      data: { usedAt: new Date() }
    });
  });

  await audit.log({
    orgId: tokenRecord.user.organizationId,
    actorUserId: tokenRecord.user.id,
    eventType: "auth.reset_password",
    entityType: "user",
    entityId: tokenRecord.user.id
  });
}

export async function me(input: { userId: string }) {
  return getAuthContext(input.userId);
}
