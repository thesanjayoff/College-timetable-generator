import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { electivesApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { ElectiveBasketOut } from "../../api/types";
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
import { ElectiveOptionsPanel } from "./ElectiveOptionsPanel";
import { ElectiveParticipationsPanel } from "./ElectiveParticipationsPanel";

interface FormState {
  name: string;
  sessions_per_week: string;
  block_size: string;
}

const emptyForm: FormState = { name: "", sessions_per_week: "3", block_size: "1" };

export default function ElectivesPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(electivesApi.listBaskets, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<ElectiveBasketOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ElectiveBasketOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(emptyForm);
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((b: ElectiveBasketOut) => {
    setEditing(b);
    setForm({ name: b.name, sessions_per_week: String(b.sessions_per_week), block_size: String(b.block_size) });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.name.trim()) errs.name = "Name is required";
    const sessions = Number(form.sessions_per_week);
    if (!sessions || sessions <= 0 || sessions > 40) errs.sessions_per_week = "Must be between 1 and 40";
    const block = Number(form.block_size);
    if (!block || block <= 0 || block > 10) errs.block_size = "Must be between 1 and 10";
    return errs;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }
    const payload = {
      name: form.name,
      sessions_per_week: Number(form.sessions_per_week),
      block_size: Number(form.block_size),
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await electivesApi.updateBasket(editing.id, payload);
        setEditing(updated);
      } else {
        const created = await electivesApi.createBasket(payload);
        setEditing(created);
      }
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
      await electivesApi.removeBasket(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<ElectiveBasketOut>[] = [
    { key: "name", header: "Basket", render: (b) => <span className="font-medium">{b.name}</span> },
    { key: "sessions", header: "Sessions/wk", render: (b) => b.sessions_per_week },
    { key: "block", header: "Block size", render: (b) => b.block_size },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (b) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(b)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(b)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Electives"
        description="Baskets of elective subjects that sections' students choose between."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New basket</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No elective baskets yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New basket</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(b) => b.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit basket · ${editing.name}` : "New elective basket"}
        widthClassName="max-w-2xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : editing ? "Save changes" : "Create basket"}
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
            placeholder="Open Elective Basket 1"
          />
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Sessions per week"
              type="number"
              min={1}
              max={40}
              value={form.sessions_per_week}
              error={fieldErrors.sessions_per_week}
              onChange={(e) => setForm({ ...form, sessions_per_week: e.target.value })}
            />
            <TextField
              label="Block size"
              type="number"
              min={1}
              max={10}
              value={form.block_size}
              error={fieldErrors.block_size}
              onChange={(e) => setForm({ ...form, block_size: e.target.value })}
            />
          </div>
        </form>

        {editing && (
          <div className="mt-6 flex flex-col gap-4">
            <ElectiveOptionsPanel basketId={editing.id} readOnly={!canWrite} />
            <ElectiveParticipationsPanel basketId={editing.id} readOnly={!canWrite} />
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete elective basket"
        message={`Delete "${deleteTarget?.name}"? Its options and participations will be removed.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
