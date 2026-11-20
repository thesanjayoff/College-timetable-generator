import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { departmentsApi, teachersApi, usersApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import { USER_ROLES, type UserOut, type UserRole } from "../../api/types";
import {
  Badge,
  Button,
  CheckboxField,
  ConfirmDialog,
  Drawer,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SelectField,
  Table,
  TextField,
} from "../../components/ui";
import type { TableColumn } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";

interface FormState {
  email: string;
  name: string;
  role: UserRole;
  department_id: string;
  teacher_id: string;
  is_active: boolean;
  password: string;
}

function emptyForm(): FormState {
  return { email: "", name: "", role: "viewer", department_id: "", teacher_id: "", is_active: true, password: "" };
}

const roleOptions = USER_ROLES.map((r) => ({ value: r, label: r }));
const roleTone: Record<UserRole, "indigo" | "amber" | "slate"> = {
  admin: "indigo",
  coordinator: "amber",
  viewer: "slate",
};

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const { data, loading, error, reload } = useFetch(usersApi.list, []);
  const { data: departments } = useFetch(departmentsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<UserOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<UserOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const departmentOptions = useMemo(() => (departments ?? []).map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })), [departments]);
  const teacherOptions = useMemo(() => (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` })), [teachers]);
  const departmentName = useCallback((id: number | null) => (id ? departments?.find((d) => d.id === id)?.name ?? `#${id}` : "—"), [departments]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(emptyForm());
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((u: UserOut) => {
    setEditing(u);
    setForm({
      email: u.email,
      name: u.name,
      role: u.role,
      department_id: u.department_id ? String(u.department_id) : "",
      teacher_id: u.teacher_id ? String(u.teacher_id) : "",
      is_active: u.is_active,
      password: "",
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.email.trim() || !form.email.includes("@")) errs.email = "A valid email is required";
    if (!form.name.trim()) errs.name = "Name is required";
    if (!editing && form.password.length < 6) errs.password = "Password must be at least 6 characters";
    if (form.password && form.password.length < 6) errs.password = "Password must be at least 6 characters";
    return errs;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const payload: Record<string, unknown> = {
          email: form.email,
          name: form.name,
          role: form.role,
          department_id: form.department_id ? Number(form.department_id) : null,
          teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
          is_active: form.is_active,
        };
        if (form.password) payload.password = form.password;
        await usersApi.update(editing.id, payload);
      } else {
        await usersApi.create({
          email: form.email,
          name: form.name,
          role: form.role,
          department_id: form.department_id ? Number(form.department_id) : null,
          teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
          is_active: form.is_active,
          password: form.password,
        });
      }
      setDrawerOpen(false);
      reload();
    } catch (err) {
      setFieldErrors(getFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await usersApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<UserOut>[] = [
    { key: "name", header: "Name", render: (u) => <span className="font-medium">{u.name}</span> },
    { key: "email", header: "Email", render: (u) => u.email },
    { key: "role", header: "Role", render: (u) => <Badge tone={roleTone[u.role]}>{u.role}</Badge> },
    { key: "department", header: "Department", render: (u) => departmentName(u.department_id) },
    {
      key: "status",
      header: "Status",
      render: (u) => (u.is_active ? <Badge tone="green">Active</Badge> : <Badge tone="rose">Inactive</Badge>),
    },
    {
      key: "actions",
      header: "",
      className: "text-right",
      render: (u) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(u)}>
            Edit
          </Button>
          <Button
            size="sm"
            variant="danger"
            disabled={u.id === currentUser?.id}
            onClick={() => setDeleteTarget(u)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Users"
        description="Accounts that can sign in to this admin tool, with role-based access."
        action={<Button variant="primary" onClick={openCreate}>+ New user</Button>}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No users yet" action={<Button variant="primary" onClick={openCreate}>+ New user</Button>} />
      )}
      {!loading && !error && data && data.length > 0 && <Table columns={columns} rows={data} rowKey={(u) => u.id} />}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit user · ${editing.name}` : "New user"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : "Save"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          <TextField
            label="Name"
            required
            maxLength={120}
            value={form.name}
            error={fieldErrors.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <TextField
            label="Email"
            type="email"
            required
            value={form.email}
            error={fieldErrors.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <SelectField
            label="Role"
            options={roleOptions}
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
          />
          <SelectField
            label="Department"
            options={departmentOptions}
            placeholder="None"
            value={form.department_id}
            onChange={(e) => setForm({ ...form, department_id: e.target.value })}
            hint={form.role === "coordinator" ? "Required to scope a coordinator's write access" : undefined}
          />
          <SelectField
            label="Linked teacher profile"
            options={teacherOptions}
            placeholder="None"
            value={form.teacher_id}
            onChange={(e) => setForm({ ...form, teacher_id: e.target.value })}
          />
          <TextField
            label={editing ? "New password" : "Password"}
            type="password"
            required={!editing}
            value={form.password}
            error={fieldErrors.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder={editing ? "Leave blank to keep current password" : undefined}
          />
          <CheckboxField
            label="Active"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            hint="Inactive users cannot sign in"
          />
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete user"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
