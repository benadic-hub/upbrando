export const PERMISSIONS = {
  AUTH_READ: "auth.read",
  AUTH_WRITE: "auth.write",
  USERS_READ: "users.read",
  USERS_WRITE: "users.write",
  ROLES_READ: "roles.read",
  ROLES_WRITE: "roles.write"
} as const;

export const MINIMAL_PERMISSION_CODES = Object.values(PERMISSIONS);

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
