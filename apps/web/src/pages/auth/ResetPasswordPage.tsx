import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { getErrorMessage } from "@/services/http";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const resetPassword = useAuthStore((state) => state.resetPassword);
  const pushToast = useUiStore((state) => state.pushToast);

  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      await resetPassword(token, newPassword);
      pushToast({ type: "success", message: "Password has been reset. Please sign in." });
      navigate("/login", { replace: true });
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-text">Reset password</h1>
      <p className="mt-1 text-sm text-muted">Enter your reset token and a new password.</p>
      <form className="mt-5 space-y-4" onSubmit={onSubmit}>
        <Input label="Token" value={token} onChange={(event) => setToken(event.target.value)} required />
        <Input
          label="New Password"
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          required
        />
        <Button className="w-full" type="submit" loading={loading}>
          Reset password
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
