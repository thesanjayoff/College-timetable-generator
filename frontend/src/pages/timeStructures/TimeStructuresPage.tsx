import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { timeStructuresApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { TimeStructureOut } from "../../api/types";
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
  Table,
  TextField,
} from "../../components/ui";
import type { TableColumn } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { DayBuilderPanel } from "./DayBuilderPanel";
import { PeriodBuilderPanel } from "./PeriodBuilderPanel";

export default function TimeStructuresPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(timeStructuresApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<TimeStructureOut | null>(null);
  const [name, setName] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TimeStructureOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openCreate = useCallback(() => {
    setEditing(null);
    setName("");
    setIsDefault(false);
    setNameError(undefined);
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((ts: TimeStructureOut) => {
    setEditing(ts);
    setName(ts.name);
    setIsDefault(ts.is_default);
    setNameError(undefined);
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const refreshEditing = useCallback(async () => {
    if (!editing) return;
    const latest = await timeStructuresApi.get(editing.id);
    setEditing(latest);
    reload();
  }, [editing, reload]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setNameError("Name is required");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await timeStructuresApi.update(editing.id, { name, is_default: isDefault });
        setEditing(updated);
      } else {
        const created = await timeStructuresApi.create({ name, is_default: isDefault, days: [], periods: [] });
        setEditing(created);
      }
      reload();
    } catch (err) {
      setNameError(getFieldErrors(err).name);
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await timeStructuresApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<TimeStructureOut>[] = [
    { key: "name", header: "Name", render: (ts) => <span className="font-medium">{ts.name}</span> },
    {
      key: "default",
      header: "Default",
      render: (ts) => (ts.is_default ? <Badge tone="green">Default</Badge> : null),
    },
    { key: "days", header: "Working days", render: (ts) => ts.days.length },
    { key: "periods", header: "Periods", render: (ts) => ts.periods.length },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (ts) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(ts)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(ts)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Time Structures"
        description="Weekly schedule templates — which days run classes and the period slots within a day."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New time structure</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState
          title="No time structures yet"
          description="Create one to define working days and period timings for programs and sections."
          action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New time structure</Button> : undefined}
        />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(ts) => ts.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit time structure · ${editing.name}` : "New time structure"}
        widthClassName="max-w-3xl"
        footer={
          <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
            Close
          </Button>
        }
      >
        <form onSubmit={handleSubmit} className="mb-5 flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          <div className="flex items-end gap-3">
            <TextField
              label="Name"
              required
              maxLength={120}
              value={name}
              error={nameError}
              onChange={(e) => setName(e.target.value)}
              placeholder="Standard week"
              containerClassName="flex-1"
            />
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Saving…" : editing ? "Save name" : "Create"}
            </Button>
          </div>
          <CheckboxField
            label="Set as default time structure"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            hint="Used for new programs/sections unless overridden"
          />
        </form>

        {editing && (
          <div className="flex flex-col gap-4">
            <DayBuilderPanel timeStructure={editing} onChanged={refreshEditing} readOnly={!canWrite} />
            <PeriodBuilderPanel timeStructure={editing} onChanged={refreshEditing} readOnly={!canWrite} />
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete time structure"
        message={`Delete "${deleteTarget?.name}"? Programs/sections using it will lose this reference.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
