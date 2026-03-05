import { Router } from "express";
import { authController } from "./auth.controller";
import { validate } from "../../middleware/validate";
import { requireAuth } from "../../middleware/auth";
import { authRateLimiter } from "../../middleware/rateLimit";
import { forgotPasswordSchema, loginSchema, registerSchema, resetPasswordSchema } from "./auth.schemas";
import { asyncHandler } from "../../common/asyncHandler";

export const authRouter = Router();

authRouter.post("/register", authRateLimiter, validate({ body: registerSchema }), asyncHandler(authController.register));
authRouter.post("/login", authRateLimiter, validate({ body: loginSchema }), asyncHandler(authController.login));
authRouter.post("/logout", authRateLimiter, asyncHandler(authController.logout));
authRouter.post(
  "/forgot-password",
  authRateLimiter,
  validate({ body: forgotPasswordSchema }),
  asyncHandler(authController.forgotPassword)
);
authRouter.post(
  "/reset-password",
  authRateLimiter,
  validate({ body: resetPasswordSchema }),
  asyncHandler(authController.resetPassword)
);
authRouter.get("/me", requireAuth, asyncHandler(authController.me));
