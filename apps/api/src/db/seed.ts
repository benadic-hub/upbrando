import { prisma } from "./prisma";

const MINIMAL_PERMISSION_CODES = ["auth.read", "auth.write", "users.read", "users.write", "roles.read", "roles.write"];

async function main() {
  for (const code of MINIMAL_PERMISSION_CODES) {
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
