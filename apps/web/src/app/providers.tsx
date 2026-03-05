import { RouterProvider } from "react-router-dom";
import { router } from "./router";
import { ToastViewport } from "@/components/ui/Toast";

export function AppProviders() {
  return (
    <>
      <RouterProvider router={router} />
      <ToastViewport />
    </>
  );
}
