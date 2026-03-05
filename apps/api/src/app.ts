import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import { corsOptions } from "./config/cors";
import { requestIdMiddleware } from "./middleware/requestId";
import { requestLogger } from "./middleware/logger";
import { globalRateLimiter } from "./middleware/rateLimit";
import { errorHandler, notFoundHandler } from "./middleware/errorHandler";
import { apiRouter } from "./routes";

export const app = express();

app.set("trust proxy", 1);

app.use(requestIdMiddleware);
app.use(requestLogger);
app.use(globalRateLimiter);
app.use(cors(corsOptions));
app.use(express.json({ limit: "1mb" }));
app.use(cookieParser());

app.use("/api/v1", apiRouter);

app.use(notFoundHandler);
app.use(errorHandler);
