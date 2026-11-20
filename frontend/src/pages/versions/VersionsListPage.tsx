import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useFetch } from "../../hooks/useFetch";
import { versionsApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import type { VersionOut } from "../../api/types";
import {
  Badge,
  Button,
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
import { statusTone, solveStatusTone } from "./versionStatus";

export default function VersionsListPage() {
  const { canWrite, isViewer } = useAuth();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useFetch(versionsApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [name, setName] = useState("");
  const [parentId, setParentId] = useState("");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<VersionOut | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [rowBusyId, setRowBusyId] = useState<number | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  const parentOptions = useMemo(
    () => (data ?? []).map((v) => ({ value: v.id, label: `#${v.id} — ${v.name}` })),
    [data],
  );

  const openCreate = useCallback(() => {
    setName("");
    setParentId("");
    setNotes("");
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("Name is required");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await versionsApi.create({
        name,
        parent_version_id: parentId ? Number(parentId) : null,
        notes: notes.trim() || null,
      });
      setDrawerOpen(false);
      navigate(`/versions/${created.id}`);
    } catch (err) {
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await versionsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  async function handlePublish(v: VersionOut) {
    setRowBusyId(v.id);
    setRowError(null);
    try {
      await versionsApi.publish(v.id);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setRowBusyId(null);
    }
  }

  async function handleRollback(v: VersionOut) {
    setRowBusyId(v.id);
    setRowError(null);
    try {
      await versionsApi.rollback(v.id);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setRowBusyId(null);
    }
  }

  const columns: TableColumn<VersionOut>[] = [
    {
      key: "name",
      header: "Name",
      render: (v) => (
        <span className="font-medium text-slate-900 dark:text-slate-50">
          #{v.id} — {v.name}
        </span>
      ),
    },
    { key: "status", header: "Status", render: (v) => <Badge tone={statusTone(v.status)}>{v.status}</Badge> },
    {
      key: "hard_violations",
      header: "Hard violations",
      render: (v) =>
        v.hard_violations > 0 ? (
          <span className="font-semibold text-rose-600 dark:text-rose-400">{v.hard_violations}</span>
        ) : (
          <span className="text-slate-500 dark:text-slate-400">0</span>
        ),
    },
    { key: "soft_score", header: "Soft score", render: (v) => v.soft_score.toFixed(1) },
    {
      key: "solve_status",
      header: "Solve status",
      render: (v) => (v.solve_status ? <Badge tone={solveStatusTone(v.solve_status)}>{v.solve_status}</Badge> : "—"),
    },
    { key: "created_at", header: "Created", render: (v) => new Date(v.created_at).toLocaleString() },
    {
      key: "actions",
      header: "",
      className: "text-right",
      render: (v) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => navigate(`/versions/${v.id}`)}>
            Open
          </Button>
          {canWrite && v.status === "draft" && (
            <Button
              size="sm"
              variant="primary"
              disabled={v.hard_violations > 0 || rowBusyId === v.id}
              title={v.hard_violations > 0 ? "Resolve all hard violations before publishing" : undefined}
              onClick={() => handlePublish(v)}
            >
              Publish
            </Button>
          )}
          {canWrite && v.status === "published" && (
            <Button size="sm" variant="secondary" disabled={rowBusyId === v.id} onClick={() => handleRollback(v)}>
              Rollback
            </Button>
          )}
          {canWrite && v.status === "draft" && (
            <Button size="sm" variant="danger" onClick={() => setDeleteTarget(v)}>
              Delete
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Timetable Versions"
        description="Draft, published and archived timetable versions. Branch a new draft from an existing version to experiment safely."
        action={
          !isViewer ? (
            <Button variant="primary" onClick={openCreate}>
              + New version
            </Button>
          ) : undefined
        }
      />

      {rowError && <div className="mb-4"><ErrorState message={rowError} /></div>}
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState
          title="No versions yet"
          description="Create your first draft version to start building a timetable."
          action={
            !isViewer ? (
              <Button variant="primary" onClick={openCreate}>
                + New version
              </Button>
            ) : undefined
          }
        />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(v) => v.id} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="New timetable version"
        subtitle="Start from scratch, or branch from an existing version to copy its sessions."
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Creating…" : "Create version"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          <TextField
            label="Name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Fall 2026 draft"
          />
          <SelectField
            label="Branch from (optional)"
            placeholder="Start empty"
            options={parentOptions}
            value={parentId}
            onChange={(e) => setParentId(e.target.value)}
            hint="Copies every session from the chosen version into the new one."
          />
          <TextField
            label="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete version"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
