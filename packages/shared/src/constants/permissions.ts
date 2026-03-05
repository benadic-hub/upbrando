export const PERMISSIONS = {
  USERS_READ: "users.read",
  USERS_WRITE: "users.write",
  ROLES_READ: "roles.read",
  ROLES_WRITE: "roles.write"
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

export const ALL_PERMISSIONS: string[] = Object.values(PERMISSIONS);

export function groupPermission(code: string): string {
  const trimmed = code.trim();
  if (!trimmed) {
    return "misc";
  }
  const [prefix] = trimmed.split(".");
  return prefix || "misc";
}

function buildPermissionGroups(codes: string[]): Array<{ group: string; codes: string[] }> {
  const map = new Map<string, string[]>();
  for (const code of codes) {
    const group = groupPermission(code);
    const existing = map.get(group) ?? [];
    existing.push(code);
    map.set(group, existing);
  }
  return Array.from(map.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([group, groupedCodes]) => ({
      group,
      codes: groupedCodes.sort((left, right) => left.localeCompare(right))
    }));
}

export const PERMISSION_GROUPS = buildPermissionGroups(ALL_PERMISSIONS);

export const MINIMAL_PERMISSION_CODES = ALL_PERMISSIONS;
