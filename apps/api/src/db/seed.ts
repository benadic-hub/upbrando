import bcrypt from "bcryptjs";
import { prisma } from "./prisma";

const ADMIN_EMAIL = "admin@upbrando.local";
const ADMIN_PASSWORD = "Admin@12345";
const ADMIN_FULL_NAME = "Admin";
const ORG_NAME = "Upbrando";

const PERMISSIONS = ["users.read", "users.write", "roles.read", "roles.write"] as const;
const ADMIN_ROLE_NAME = "Admin";
const MEMBER_ROLE_NAME = "Member";

async function upsertPermissions() {
  for (const code of PERMISSIONS) {
    await prisma.permission.upsert({
      where: { code },
      update: {},
      create: {
        code,
        description: `${code} permission`
      }
    });
  }
}

async function main() {
  await upsertPermissions();

  const org = await prisma.organization.upsert({
    where: { id: "upbrando-org" },
    update: {
      name: ORG_NAME
    },
    create: {
      id: "upbrando-org",
      name: ORG_NAME
    }
  });

  const adminRole = await prisma.role.upsert({
    where: {
      organizationId_name: {
        organizationId: org.id,
        name: ADMIN_ROLE_NAME
      }
    },
    update: {
      description: "Organization administrators"
    },
    create: {
      organizationId: org.id,
      name: ADMIN_ROLE_NAME,
      description: "Organization administrators"
    }
  });

  const memberRole = await prisma.role.upsert({
    where: {
      organizationId_name: {
        organizationId: org.id,
        name: MEMBER_ROLE_NAME
      }
    },
    update: {
      description: "Default member role"
    },
    create: {
      organizationId: org.id,
      name: MEMBER_ROLE_NAME,
      description: "Default member role"
    }
  });

  const allPermissionRows = await prisma.permission.findMany({
    where: { code: { in: [...PERMISSIONS] } },
    select: { id: true, code: true }
  });

  const memberPermissionRows = allPermissionRows.filter(
    (permission) => permission.code === "users.read" || permission.code === "roles.read"
  );

  await prisma.rolePermission.deleteMany({
    where: { roleId: { in: [adminRole.id, memberRole.id] } }
  });

  await prisma.rolePermission.createMany({
    data: allPermissionRows.map((permission) => ({
      roleId: adminRole.id,
      permissionId: permission.id
    }))
  });

  await prisma.rolePermission.createMany({
    data: memberPermissionRows.map((permission) => ({
      roleId: memberRole.id,
      permissionId: permission.id
    }))
  });

  const passwordHash = await bcrypt.hash(ADMIN_PASSWORD, 12);
  const adminUser = await prisma.user.upsert({
    where: { email: ADMIN_EMAIL },
    update: {
      organizationId: org.id,
      fullName: ADMIN_FULL_NAME,
      status: "active",
      passwordHash
    },
    create: {
      organizationId: org.id,
      email: ADMIN_EMAIL,
      fullName: ADMIN_FULL_NAME,
      status: "active",
      passwordHash
    }
  });

  await prisma.userRole.upsert({
    where: {
      userId_roleId: {
        userId: adminUser.id,
        roleId: adminRole.id
      }
    },
    update: {},
    create: {
      userId: adminUser.id,
      roleId: adminRole.id
    }
  });

  const sampleUsers = [
    { email: "member1@upbrando.local", fullName: "Member One", status: "active" as const },
    { email: "member2@upbrando.local", fullName: "Member Two", status: "invited" as const }
  ];

  for (const sample of sampleUsers) {
    const samplePasswordHash = await bcrypt.hash("Member@12345", 12);
    const user = await prisma.user.upsert({
      where: { email: sample.email },
      update: {
        organizationId: org.id,
        fullName: sample.fullName,
        status: sample.status,
        passwordHash: samplePasswordHash
      },
      create: {
        organizationId: org.id,
        email: sample.email,
        fullName: sample.fullName,
        status: sample.status,
        passwordHash: samplePasswordHash
      }
    });

    await prisma.userRole.upsert({
      where: {
        userId_roleId: {
          userId: user.id,
          roleId: memberRole.id
        }
      },
      update: {},
      create: {
        userId: user.id,
        roleId: memberRole.id
      }
    });
  }

  // eslint-disable-next-line no-console
  console.log("Seed completed");
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    // eslint-disable-next-line no-console
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
