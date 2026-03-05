import { prisma } from "../db/prisma";

type AuditPayload = {
  orgId?: string | null;
  actorUserId?: string | null;
  eventType: string;
  entityType?: string | null;
  entityId?: string | null;
  metadata?: unknown;
};

export const audit = {
  async log(payload: AuditPayload) {
    const metadata =
      payload.metadata === undefined || payload.metadata === null ? null : JSON.stringify(payload.metadata);

    await prisma.auditEvent.create({
      data: {
        organizationId: payload.orgId ?? null,
        actorUserId: payload.actorUserId ?? null,
        eventType: payload.eventType,
        entityType: payload.entityType ?? null,
        entityId: payload.entityId ?? null,
        metadataJson: metadata
      }
    });
  }
};
