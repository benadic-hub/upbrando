import { AppError } from "../../common/errors";
import { parsePagination } from "../../common/pagination";
import { prisma } from "../../db/prisma";
import { audit } from "../../common/audit";

function sanitizeRole(role: {
  id: string;
  organizationId: string;
  name: string;
  description: string | null;
  createdAt: Date;
  updatedAt: Date;
}) {
  return {
    id: role.id,
    organizationId: role.organizationId,
    name: role.name,
    description: role.description,
    createdAt: role.createdAt,
    updatedAt: role.updatedAt
  };
}

async function ensureRoleInOrg(roleId: string, orgId: string) {
  const role = await prisma.role.findFirst({
    where: {
      id: roleId,
      organizationId: orgId
    }
  });
  if (!role) {
    throw new AppError(404, "ROLE_NOT_FOUND", "Role not found");
  }
  return role;
}

export async function listRoles(input: {
  orgId: string;
  page?: number;
  pageSize?: number;
  sortBy?: "createdAt" | "name";
  sortDir?: "asc" | "desc";
}) {
  const pagination = parsePagination({
    page: input.page,
    pageSize: input.pageSize,
    sortBy: input.sortBy,
    sortDir: input.sortDir
  });

  const where = { organizationId: input.orgId };
  const [total, roles] = await Promise.all([
    prisma.role.count({ where }),
    prisma.role.findMany({
      where,
      skip: pagination.skip,
      take: pagination.take,
      orderBy: { [pagination.sortBy]: pagination.sortDir } as never
    })
  ]);

  return {
    data: roles.map(sanitizeRole),
    meta: {
      page: pagination.page,
      pageSize: pagination.pageSize,
      total,
      sortBy: pagination.sortBy,
      sortDir: pagination.sortDir
    }
  };
}

export async function createRole(input: {
  orgId: string;
  actorUserId: string;
  name: string;
  description?: string;
}) {
  const role = await prisma.role.create({
    data: {
      organizationId: input.orgId,
      name: input.name.trim(),
      description: input.description?.trim() ?? null
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "roles.create",
    entityType: "role",
    entityId: role.id,
    metadata: {
      name: role.name
    }
  });

  return sanitizeRole(role);
}

export async function updateRole(input: {
  orgId: string;
  actorUserId: string;
  roleId: string;
  name?: string;
  description?: string | null;
}) {
  await ensureRoleInOrg(input.roleId, input.orgId);

  const updated = await prisma.role.update({
    where: { id: input.roleId },
    data: {
      ...(input.name ? { name: input.name.trim() } : {}),
      ...(Object.prototype.hasOwnProperty.call(input, "description")
        ? { description: input.description?.trim() ?? null }
        : {})
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "roles.update",
    entityType: "role",
    entityId: updated.id,
    metadata: {
      name: updated.name,
      description: updated.description
    }
  });

  return sanitizeRole(updated);
}

export async function getRolePermissionCodes(input: { orgId: string; roleId: string }) {
  const role = await prisma.role.findFirst({
    where: {
      id: input.roleId,
      organizationId: input.orgId
    },
    include: {
      rolePermissions: {
        include: {
          permission: true
        }
      }
    }
  });

  if (!role) {
    throw new AppError(404, "ROLE_NOT_FOUND", "Role not found");
  }

  return role.rolePermissions.map((item) => item.permission.code).sort();
}

export async function replaceRolePermissions(input: {
  orgId: string;
  actorUserId: string;
  roleId: string;
  permissionCodes: string[];
}) {
  await ensureRoleInOrg(input.roleId, input.orgId);

  const uniqueCodes = Array.from(new Set(input.permissionCodes.map((code) => code.trim()).filter(Boolean)));

  await prisma.$transaction(async (tx) => {
    for (const code of uniqueCodes) {
      await tx.permission.upsert({
        where: { code },
        update: {},
        create: {
          code,
          description: `${code} permission`
        }
      });
    }

    const permissions = await tx.permission.findMany({
      where: { code: { in: uniqueCodes } },
      select: { id: true }
    });

    await tx.rolePermission.deleteMany({
      where: {
        roleId: input.roleId
      }
    });

    if (permissions.length > 0) {
      await tx.rolePermission.createMany({
        data: permissions.map((permission) => ({
          roleId: input.roleId,
          permissionId: permission.id
        }))
      });
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "roles.permissions.replace",
    entityType: "role",
    entityId: input.roleId,
    metadata: {
      permissionCodes: uniqueCodes
    }
  });
}

export async function assignRoleToUser(input: {
  orgId: string;
  actorUserId: string;
  roleId: string;
  userId: string;
}) {
  const [role, user] = await Promise.all([
    prisma.role.findFirst({
      where: {
        id: input.roleId,
        organizationId: input.orgId
      }
    }),
    prisma.user.findFirst({
      where: {
        id: input.userId,
        organizationId: input.orgId
      }
    })
  ]);

  if (!role) {
    throw new AppError(404, "ROLE_NOT_FOUND", "Role not found");
  }
  if (!user) {
    throw new AppError(404, "USER_NOT_FOUND", "User not found");
  }

  await prisma.userRole.upsert({
    where: {
      userId_roleId: {
        userId: input.userId,
        roleId: input.roleId
      }
    },
    update: {},
    create: {
      userId: input.userId,
      roleId: input.roleId
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "roles.assign",
    entityType: "role",
    entityId: input.roleId,
    metadata: {
      userId: input.userId
    }
  });
}

export async function unassignRoleFromUser(input: {
  orgId: string;
  actorUserId: string;
  roleId: string;
  userId: string;
}) {
  const role = await prisma.role.findFirst({
    where: {
      id: input.roleId,
      organizationId: input.orgId
    },
    select: { id: true }
  });
  if (!role) {
    throw new AppError(404, "ROLE_NOT_FOUND", "Role not found");
  }

  await prisma.userRole.deleteMany({
    where: {
      roleId: input.roleId,
      userId: input.userId
    }
  });

  await audit.log({
    orgId: input.orgId,
    actorUserId: input.actorUserId,
    eventType: "roles.unassign",
    entityType: "role",
    entityId: input.roleId,
    metadata: {
      userId: input.userId
    }
  });
}
