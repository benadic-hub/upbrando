export type UserStatus = "active" | "inactive" | "invited";

export type AuthUser = {
  id: string;
  organizationId: string;
  email: string;
  fullName: string;
  status: UserStatus;
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AuthOrganization = {
  id: string;
  name: string;
  domain: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AuthRole = {
  id: string;
  organizationId: string;
  name: string;
  description: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AuthMeData = {
  user: AuthUser;
  organization: AuthOrganization;
  roles: AuthRole[];
  permissions: string[];
};

export type AuthMeResponse = {
  data: AuthMeData;
};

export type AppUser = AuthUser;
export type AppRole = AuthRole;
export type AppOrganization = AuthOrganization;
