# Prisma Migrations (Windows-safe workflow)

This project uses standard Prisma migrations from `apps/api/prisma/migrations`.

## Recommended commands

- Create/apply local migration changes:
  - `pnpm --dir apps/api db:migrate`
- Apply existing migrations (CI/prod style):
  - `pnpm --dir apps/api db:deploy`
- Seed local dev data:
  - `pnpm --dir apps/api db:seed`
- Reset local DB and reseed:
  - `pnpm --dir apps/api db:reset`

## Important note for Windows

If API/web dev servers are running, `prisma generate` can fail with:

- `EPERM: operation not permitted, rename ... query_engine-windows.dll.node`

This happens when the Prisma engine file is in use by a running Node process.

Use this order when you hit that issue:

1. Stop `apps/api` dev server.
2. Run `pnpm --dir apps/api db:generate`.
3. Start dev servers again.

`db:migrate` and `db:reset` use `--skip-generate` to avoid this lock during migration steps.

