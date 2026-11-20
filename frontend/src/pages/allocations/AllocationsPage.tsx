import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import {
  allocationsApi,
  labBatchesApi,
  roomsApi,
  sectionsApi,
  subjectsApi,
  teachersApi,
} from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { AllocationOut } from "../../api/types";
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
} from "../../components/ui";
import type { TableColumn } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";

interface FormState {
  subject_id: string;
  section_id: string;
  lab_batch_id: string;
  teacher_id: string;
  is_fixed_teacher: boolean;
  room_id: string;
  is_fixed_room: boolean;
}

const emptyForm: FormState = {
  subject_id: "",
  section_id: "",
  lab_batch_id: "",
  teacher_id: "",
  is_fixed_teacher: false,
  room_id: "",
  is_fixed_room: false,
};

export default function AllocationsPage() {
  const { canWrite } = useAuth();
  const [sectionFilter, setSectionFilter] = useState("");

  const { data: subjects } = useFetch(subjectsApi.list, []);
  const { data: sections } = useFetch(sectionsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);
  const { data: rooms } = useFetch(roomsApi.list, []);
  const { data: labBatches } = useFetch(labBatchesApi.list, []);

  const listFetcher = useCallback(
    () => allocationsApi.list(sectionFilter ? { section_id: Number(sectionFilter) } : undefined),
    [sectionFilter],
  );
  const { data, loading, error, reload } = useFetch(listFetcher, [sectionFilter]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<AllocationOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AllocationOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const subjectOptions = useMemo(
    () => (subjects ?? []).map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })),
    [subjects],
  );
  const sectionOptions = useMemo(
    () => (sections ?? []).map((s) => ({ value: s.id, label: s.name })),
    [sections],
  );
  const teacherOptions = useMemo(
    () => (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` })),
    [teachers],
  );
  const roomOptions = useMemo(() => (rooms ?? []).map((r) => ({ value: r.id, label: `${r.code} — ${r.name}` })), [rooms]);
  const labBatchOptions = useMemo(
    () => (labBatches ?? []).filter((b) => String(b.section_id) === form.section_id).map((b) => ({ value: b.id, label: b.name })),
    [labBatches, form.section_id],
  );

  const nameOf = useCallback(
    (list: { id: number; code?: string; name: string }[] | undefined, id: number | null) => {
      if (id === null) return "—";
      const item = list?.find((x) => x.id === id);
      if (!item) return `#${id}`;
      return item.code ? `${item.code} — ${item.name}` : item.name;
    },
    [],
  );

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm({ ...emptyForm, section_id: sectionFilter });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, [sectionFilter]);

  const openEdit = useCallback((a: AllocationOut) => {
    setEditing(a);
    setForm({
      subject_id: String(a.subject_id),
      section_id: String(a.section_id),
      lab_batch_id: a.lab_batch_id ? String(a.lab_batch_id) : "",
      teacher_id: a.teacher_id ? String(a.teacher_id) : "",
      is_fixed_teacher: a.is_fixed_teacher,
      room_id: a.room_id ? String(a.room_id) : "",
      is_fixed_room: a.is_fixed_room,
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.subject_id) errs.subject_id = "Subject is required";
    if (!form.section_id) errs.section_id = "Section is required";
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
      subject_id: Number(form.subject_id),
      section_id: Number(form.section_id),
      lab_batch_id: form.lab_batch_id ? Number(form.lab_batch_id) : null,
      teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
      is_fixed_teacher: form.is_fixed_teacher,
      room_id: form.room_id ? Number(form.room_id) : null,
      is_fixed_room: form.is_fixed_room,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        await allocationsApi.update(editing.id, payload);
      } else {
        await allocationsApi.create(payload);
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
      await allocationsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<AllocationOut>[] = [
    { key: "subject", header: "Subject", render: (a) => nameOf(subjects, a.subject_id) },
    { key: "section", header: "Section", render: (a) => nameOf(sections, a.section_id) },
    { key: "batch", header: "Lab batch", render: (a) => (a.lab_batch_id ? nameOf(labBatches, a.lab_batch_id) : "—") },
    {
      key: "teacher",
      header: "Teacher",
      render: (a) => (
        <span className="flex items-center gap-1.5">
          {nameOf(teachers, a.teacher_id)}
          {a.is_fixed_teacher && <Badge tone="amber">fixed</Badge>}
        </span>
      ),
    },
    {
      key: "room",
      header: "Room",
      render: (a) => (
        <span className="flex items-center gap-1.5">
          {nameOf(rooms, a.room_id)}
          {a.is_fixed_room && <Badge tone="amber">fixed</Badge>}
        </span>
      ),
    },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (a) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(a)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(a)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Allocations"
        description="Which subject a section (or lab batch) takes, and its optional fixed teacher/room."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New allocation</Button> : undefined}
      />

      <div className="mb-4 max-w-xs">
        <SelectField
          label="Filter by section"
          options={sectionOptions}
          placeholder="All sections"
          value={sectionFilter}
          onChange={(e) => setSectionFilter(e.target.value)}
        />
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No allocations yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New allocation</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(a) => a.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? "Edit allocation" : "New allocation"}
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
          <SelectField
            label="Section"
            required
            options={sectionOptions}
            placeholder="Select a section"
            value={form.section_id}
            error={fieldErrors.section_id}
            onChange={(e) => setForm({ ...form, section_id: e.target.value, lab_batch_id: "" })}
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
            label="Lab batch"
            options={labBatchOptions}
            placeholder="Whole section"
            value={form.lab_batch_id}
            error={fieldErrors.lab_batch_id}
            onChange={(e) => setForm({ ...form, lab_batch_id: e.target.value })}
            hint={form.section_id ? undefined : "Select a section first"}
          />
          <div>
            <SelectField
              label="Teacher"
              options={teacherOptions}
              placeholder="Let the solver assign"
              value={form.teacher_id}
              error={fieldErrors.teacher_id}
              onChange={(e) => setForm({ ...form, teacher_id: e.target.value })}
            />
            {form.teacher_id && (
              <div className="mt-2">
                <CheckboxField
                  label="Fix this teacher (solver may not change it)"
                  checked={form.is_fixed_teacher}
                  onChange={(e) => setForm({ ...form, is_fixed_teacher: e.target.checked })}
                />
              </div>
            )}
          </div>
          <div>
            <SelectField
              label="Room"
              options={roomOptions}
              placeholder="Let the solver assign"
              value={form.room_id}
              error={fieldErrors.room_id}
              onChange={(e) => setForm({ ...form, room_id: e.target.value })}
            />
            {form.room_id && (
              <div className="mt-2">
                <CheckboxField
                  label="Fix this room (solver may not change it)"
                  checked={form.is_fixed_room}
                  onChange={(e) => setForm({ ...form, is_fixed_room: e.target.checked })}
                />
              </div>
            )}
          </div>
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete allocation"
        busy={deleting}
        message="Delete this allocation? This cannot be undone."
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
