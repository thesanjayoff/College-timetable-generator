import { useState } from "react";
import type { FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { usersApi } from "../api/resources";
import { getErrorMessage, getFieldErrors } from "../api/client";
import { Badge, Button, Card, ErrorState, PageHeader, TextField } from "../components/ui";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [name, setName] = useState(user?.name ?? "");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = "Name is required";
    if (password && password.length < 6) errs.password = "Password must be at least 6 characters";
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setSuccess(false);
    try {
      const payload: { name?: string; password?: string } = { name };
      if (password) payload.password = password;
      await usersApi.updateMe(payload);
      await refreshUser();
      setPassword("");
      setSuccess(true);
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!user) return null;

  return (
    <div>
      <PageHeader title="My Profile" description="Update your display name and password." />

      <Card className="max-w-lg p-5">
        <div className="mb-5 flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-200 text-sm font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
            {user.name.slice(0, 1).toUpperCase()}
          </span>
          <div>
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">{user.email}</p>
            <Badge tone="indigo">{user.role}</Badge>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          {success && (
            <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">
              Profile updated.
            </p>
          )}
          <TextField
            label="Name"
            required
            value={name}
            error={fieldErrors.name}
            onChange={(e) => setName(e.target.value)}
          />
          <TextField
            label="New password"
            type="password"
            value={password}
            error={fieldErrors.password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Leave blank to keep current password"
          />
          <div>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
