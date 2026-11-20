import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { combinedClassesApi, subjectsApi, teachersApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import { ROOM_TYPES, type CombinedClassOut, type RoomType } from "../../api/types";
import {
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
import { CombinedClassSectionsPanel } from "./CombinedClassSectionsPanel";

interface FormState {
  name: string;
  subject_id: string;
  teacher_id: string;
  sessions_per_week: string;
  block_size: string;
  room_type_required: string;
}

const emptyForm: FormState = {
  name: "",
  subject_id: "",
  teacher_id: "",
  sessions_per_week: "1",
  block_size: "1",
  room_type_required: "seminar_hall",
};

const roomTypeOptions = ROOM_TYPES.map((t) => ({ value: t, label: t.replace("_", " ") }));

export default function CombinedClassesPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(combinedClassesApi.list, []);
  const { data: subjects } = useFetch(subjectsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<CombinedClassOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CombinedClassOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const subjectOptions = useMemo(() => (subjects ?? []).map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })), [subjects]);
  const teacherOptions = useMemo(() => (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` })), [teachers]);
  const subjectName = useCallback((id: number) => subjects?.find((s) => s.id === id)?.name ?? `#${id}`, [subjects]);
  const teacherName = useCallback((id: number | null) => (id ? teachers?.find((t) => t.id === id)?.name ?? `#${id}` : "—"), [teachers]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(emptyForm);
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((cc: CombinedClassOut) => {
    setEditing(cc);
    setForm({
      name: cc.name,
      subject_id: String(cc.subject_id),
      teacher_id: cc.teacher_id ? String(cc.teacher_id) : "",
      sessions_per_week: String(cc.sessions_per_week),
      block_size: String(cc.block_size),
      room_type_required: cc.room_type_required,
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.name.trim()) errs.name = "Name is required";
    if (!form.subject_id) errs.subject_id = "Subject is required";
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
      subject_id: Number(form.subject_id),
      teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
      sessions_per_week: Number(form.sessions_per_week),
      block_size: Number(form.block_size),
      room_type_required: form.room_type_required as RoomType,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await combinedClassesApi.update(editing.id, payload);
        setEditing(updated);
      } else {
        const created = await combinedClassesApi.create(payload);
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
      await combinedClassesApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<CombinedClassOut>[] = [
    { key: "name", header: "Name", render: (cc) => <span className="font-medium">{cc.name}</span> },
    { key: "subject", header: "Subject", render: (cc) => subjectName(cc.subject_id) },
    { key: "teacher", header: "Teacher", render: (cc) => teacherName(cc.teacher_id) },
    { key: "sessions", header: "Sessions/wk", render: (cc) => cc.sessions_per_week },
    { key: "room_type", header: "Room type", render: (cc) => cc.room_type_required.replace("_", " ") },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (cc) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(cc)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(cc)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Combined Classes"
        description="A single session shared by multiple sections (e.g. a guest lecture in a seminar hall)."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New combined class</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No combined classes yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New combined class</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(cc) => cc.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit combined class · ${editing.name}` : "New combined class"}
        widthClassName="max-w-2xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : editing ? "Save changes" : "Create"}
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
          <SelectField
            label="Subject"
            required
            options={subjectOptions}
            placeholder="Select a subject"
            value={form.subject_id}
            error={fieldErrors.subject_id}
            onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
          />
          <SelectField
            label="Teacher"
            options={teacherOptions}
            placeholder="Unassigned"
            value={form.teacher_id}
            onChange={(e) => setForm({ ...form, teacher_id: e.target.value })}
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
          <SelectField
            label="Required room type"
            options={roomTypeOptions}
            value={form.room_type_required}
            onChange={(e) => setForm({ ...form, room_type_required: e.target.value })}
          />
        </form>

        {editing && (
          <div className="mt-6">
            <CombinedClassSectionsPanel combinedClassId={editing.id} readOnly={!canWrite} />
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete combined class"
        message={`Delete "${deleteTarget?.name}"? Its section links will be removed.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
