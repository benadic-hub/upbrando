import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/auth.store";
import { useUiStore } from "@/store/ui.store";
import { getErrorMessage } from "@/services/http";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);
  const isLoading = useAuthStore((state) => state.isLoading);
  const pushToast = useUiStore((state) => state.pushToast);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await login(email, password);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      pushToast({ type: "error", message: getErrorMessage(error) });
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-text">Sign in</h1>
      <p className="mt-1 text-sm text-muted">Use your account credentials to continue.</p>
      <form className="mt-5 space-y-4" onSubmit={onSubmit}>
        <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
        <Button className="w-full" type="submit" loading={isLoading}>
          Sign In
        </Button>
      </form>
      <div className="mt-4 text-sm">
        <Link className="text-primary hover:underline" to="/forgot-password">
          Forgot password?
        </Link>
      </div>
    </div>
  );
}
