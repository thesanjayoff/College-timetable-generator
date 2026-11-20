import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { weightProfilesApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import { WEIGHT_CATEGORIES, type WeightProfileOut } from "../../api/types";
import {
  Badge,
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

function defaultWeights(): Record<string, number> {
  const result: Record<string, number> = {};
  for (const cat of WEIGHT_CATEGORIES) result[cat.key] = 5;
  return result;
}

export default function WeightProfilesPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(weightProfilesApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<WeightProfileOut | null>(null);
  const [name, setName] = useState("");
  const [weights, setWeights] = useState<Record<string, number>>(defaultWeights());
  const [nameError, setNameError] = useState<string | undefined>(undefined);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<WeightProfileOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const groups = useMemo(() => {
    const map = new Map<string, typeof WEIGHT_CATEGORIES>();
    for (const cat of WEIGHT_CATEGORIES) {
      const list = map.get(cat.group) ?? [];
      list.push(cat);
      map.set(cat.group, list);
    }
    return Array.from(map.entries());
  }, []);

  const openCreate = useCallback(() => {
    setEditing(null);
    setName("");
    setWeights(defaultWeights());
    setNameError(undefined);
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((profile: WeightProfileOut) => {
    setEditing(profile);
    setName(profile.name);
    setWeights({ ...defaultWeights(), ...profile.weights });
    setNameError(undefined);
    setFormError(null);
    setDrawerOpen(true);
  }, []);

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
        await weightProfilesApi.update(editing.id, { name, weights });
      } else {
        await weightProfilesApi.create({ name, is_preset: false, weights });
      }
      setDrawerOpen(false);
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
      await weightProfilesApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<WeightProfileOut>[] = [
    {
      key: "name",
      header: "Profile",
      render: (p) => (
        <span className="flex items-center gap-2 font-medium">
          {p.name}
          {p.is_preset && <Badge tone="indigo">preset</Badge>}
        </span>
      ),
    },
    { key: "categories", header: "Weighted categories", render: (p) => Object.keys(p.weights).length },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (p) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(p)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" disabled={p.is_preset} onClick={() => setDeleteTarget(p)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Weight Profiles"
        description="Soft-objective weights the solver balances. Presets are seeded by the backend; create your own to tune priorities."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New profile</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No weight profiles yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New profile</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(p) => p.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit profile · ${editing.name}` : "New weight profile"}
        widthClassName="max-w-2xl"
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
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          {formError && <ErrorState message={formError} />}
          <TextField
            label="Profile name"
            required
            maxLength={80}
            value={name}
            error={nameError}
            onChange={(e) => setName(e.target.value)}
            placeholder="my_custom_profile"
          />

          {groups.map(([group, cats]) => (
            <div key={group}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {group}
              </p>
              <div className="flex flex-col gap-3">
                {cats.map((cat) => (
                  <div key={cat.key} className="flex items-center gap-3">
                    <label className="w-56 shrink-0 text-sm text-slate-700 dark:text-slate-200">{cat.label}</label>
                    <input
                      type="range"
                      min={0}
                      max={30}
                      step={0.5}
                      value={weights[cat.key] ?? 0}
                      onChange={(e) => setWeights({ ...weights, [cat.key]: Number(e.target.value) })}
                      className="flex-1 accent-indigo-600"
                    />
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.5}
                      value={weights[cat.key] ?? 0}
                      onChange={(e) => setWeights({ ...weights, [cat.key]: Number(e.target.value) || 0 })}
                      className="w-16 rounded-md border border-slate-300 bg-white px-2 py-1 text-right text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete weight profile"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
