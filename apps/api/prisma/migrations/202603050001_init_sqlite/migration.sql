-- CreateTable
CREATE TABLE IF NOT EXISTS "organizations" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "domain" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "users" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "organization_id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "password_hash" TEXT NOT NULL,
    "full_name" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'active',
    "last_login_at" DATETIME,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    CONSTRAINT "users_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "organizations" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "roles" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "organization_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    CONSTRAINT "roles_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "organizations" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "permissions" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "code" TEXT NOT NULL,
    "description" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "role_permissions" (
    "role_id" TEXT NOT NULL,
    "permission_id" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY ("role_id", "permission_id"),
    CONSTRAINT "role_permissions_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "roles" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "role_permissions_permission_id_fkey" FOREIGN KEY ("permission_id") REFERENCES "permissions" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "user_roles" (
    "user_id" TEXT NOT NULL,
    "role_id" TEXT NOT NULL,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY ("user_id", "role_id"),
    CONSTRAINT "user_roles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "user_roles_role_id_fkey" FOREIGN KEY ("role_id") REFERENCES "roles" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "user_sessions" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "refresh_token_hash" TEXT NOT NULL,
    "user_agent" TEXT,
    "ip" TEXT,
    "expires_at" DATETIME NOT NULL,
    "revoked_at" DATETIME,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "user_sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "password_reset_tokens" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "user_id" TEXT NOT NULL,
    "token_hash" TEXT NOT NULL,
    "expires_at" DATETIME NOT NULL,
    "used_at" DATETIME,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "password_reset_tokens_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "audit_events" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "organization_id" TEXT,
    "actor_user_id" TEXT,
    "event_type" TEXT NOT NULL,
    "entity_type" TEXT,
    "entity_id" TEXT,
    "metadata_json" TEXT,
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "audit_events_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "organizations" ("id") ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT "audit_events_actor_user_id_fkey" FOREIGN KEY ("actor_user_id") REFERENCES "users" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "uq_users_email" ON "users"("email");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_users_organization_id" ON "users"("organization_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_users_org_status" ON "users"("organization_id", "status");

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "uq_roles_org_name" ON "roles"("organization_id", "name");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_roles_organization_id" ON "roles"("organization_id");

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "uq_permissions_code" ON "permissions"("code");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_role_permissions_permission_id" ON "role_permissions"("permission_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_user_roles_role_id" ON "user_roles"("role_id");

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "uq_user_sessions_refresh_token_hash" ON "user_sessions"("refresh_token_hash");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_user_sessions_user_id" ON "user_sessions"("user_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_user_sessions_user_revoked" ON "user_sessions"("user_id", "revoked_at");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_password_reset_tokens_user_id" ON "password_reset_tokens"("user_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_password_reset_tokens_expires_at" ON "password_reset_tokens"("expires_at");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_password_reset_tokens_token_hash" ON "password_reset_tokens"("token_hash");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_audit_events_org_id" ON "audit_events"("organization_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_audit_events_actor_user_id" ON "audit_events"("actor_user_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "idx_audit_events_event_type" ON "audit_events"("event_type");
