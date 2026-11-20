import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { departmentsApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { DepartmentOut } from "../../api/types";
import {
  Button,
  ConfirmDialog,
  Drawer,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  Table,
  TextField,
} from "../../components/ui";
import type { TableColumn } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";

interface FormState {
  name: string;
  code: string;
}

const emptyForm: FormState = { name: "", code: "" };

export default function DepartmentsPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(departmentsApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<DepartmentOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DepartmentOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(emptyForm);
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((dept: DepartmentOut) => {
    setEditing(dept);
    setForm({ name: dept.name, code: dept.code });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.name.trim()) errs.name = "Name is required";
    else if (form.name.length > 120) errs.name = "Max 120 characters";
    if (!form.code.trim()) errs.code = "Code is required";
    else if (form.code.length > 20) errs.code = "Max 20 characters";
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
        await departmentsApi.update(editing.id, form);
      } else {
        await departmentsApi.create(form);
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
      await departmentsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<DepartmentOut>[] = [
    { key: "code", header: "Code", render: (d) => <span className="font-medium">{d.code}</span> },
    { key: "name", header: "Name", render: (d) => d.name },
  ];

  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (d) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(d)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(d)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Departments"
        description="Academic departments that own programs, subjects and teachers."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New department</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState
          title="No departments yet"
          description="Departments group programs, subjects and teachers together."
          action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New department</Button> : undefined}
        />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(d) => d.id} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? "Edit department" : "New department"}
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
            label="Code"
            required
            maxLength={20}
            value={form.code}
            error={fieldErrors.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
            placeholder="CSE"
          />
          <TextField
            label="Name"
            required
            maxLength={120}
            value={form.name}
            error={fieldErrors.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Computer Science & Engineering"
          />
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete department"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
