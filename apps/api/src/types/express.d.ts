declare global {
  namespace Express {
    interface Request {
      requestId?: string;
      user?: {
        userId: string;
        orgId: string;
        sessionId?: string;
      };
    }
  }
}

export {};
