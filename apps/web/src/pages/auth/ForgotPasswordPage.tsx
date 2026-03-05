import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { getErrorMessage } from "@/services/http";

export function ForgotPasswordPage() {
  const forgotPassword = useAuthStore((state) => state.forgotPassword);
  const pushToast = useUiStore((state) => state.pushToast);
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      await forgotPassword(email);
      pushToast({ type: "success", message: "If this account exists, reset instructions were processed." });
      setEmail("");
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-text">Forgot password</h1>
      <p className="mt-1 text-sm text-muted">Enter your email to continue.</p>
      <form className="mt-5 space-y-4" onSubmit={onSubmit}>
        <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Button className="w-full" type="submit" loading={loading}>
          Send reset link
        </Button>
      </form>
      <div className="mt-4 text-sm">
        <Link className="text-primary hover:underline" to="/login">
          Back to login
        </Link>
      </div>
    </div>
  );
}
