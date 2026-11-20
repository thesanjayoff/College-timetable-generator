import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { programsApi, sectionsApi, timeStructuresApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { SectionOut } from "../../api/types";
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
import { LabBatchesPanel } from "./LabBatchesPanel";

interface FormState {
  program_id: string;
  semester_number: string;
  name: string;
  strength: string;
  time_structure_id: string;
  max_periods_per_day: string;
  max_consecutive_periods: string;
}

const emptyForm: FormState = {
  program_id: "",
  semester_number: "1",
  name: "",
  strength: "60",
  time_structure_id: "",
  max_periods_per_day: "",
  max_consecutive_periods: "",
};

export default function SectionsPage() {
  const { canWrite } = useAuth();
  const [programFilter, setProgramFilter] = useState<string>("");

  const { data: programs } = useFetch(programsApi.list, []);
  const { data: timeStructures } = useFetch(timeStructuresApi.list, []);

  const listFetcher = useCallback(
    () => sectionsApi.list(programFilter ? Number(programFilter) : undefined),
    [programFilter],
  );
  const { data, loading, error, reload } = useFetch(listFetcher, [programFilter]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<SectionOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SectionOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const programOptions = useMemo(
    () => (programs ?? []).map((p) => ({ value: p.id, label: `${p.code} — ${p.name}` })),
    [programs],
  );
  const programName = useCallback(
    (id: number) => {
      const p = programs?.find((x) => x.id === id);
      return p ? `${p.code} — ${p.name}` : `#${id}`;
    },
    [programs],
  );
  const timeStructureOptions = useMemo(
    () => (timeStructures ?? []).map((t) => ({ value: t.id, label: t.name })),
    [timeStructures],
  );

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm({ ...emptyForm, program_id: programFilter });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, [programFilter]);

  const openEdit = useCallback((s: SectionOut) => {
    setEditing(s);
    setForm({
      program_id: String(s.program_id),
      semester_number: String(s.semester_number),
      name: s.name,
      strength: String(s.strength),
      time_structure_id: s.time_structure_id ? String(s.time_structure_id) : "",
      max_periods_per_day: s.max_periods_per_day ? String(s.max_periods_per_day) : "",
      max_consecutive_periods: s.max_consecutive_periods ? String(s.max_consecutive_periods) : "",
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.program_id) errs.program_id = "Program is required";
    if (!form.name.trim()) errs.name = "Name is required";
    const sem = Number(form.semester_number);
    if (!sem || sem <= 0 || sem > 20) errs.semester_number = "Must be between 1 and 20";
    const strength = Number(form.strength);
    if (!strength || strength <= 0) errs.strength = "Must be a positive number";
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
      program_id: Number(form.program_id),
      semester_number: Number(form.semester_number),
      name: form.name,
      strength: Number(form.strength),
      time_structure_id: form.time_structure_id ? Number(form.time_structure_id) : null,
      max_periods_per_day: form.max_periods_per_day ? Number(form.max_periods_per_day) : null,
      max_consecutive_periods: form.max_consecutive_periods ? Number(form.max_consecutive_periods) : null,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await sectionsApi.update(editing.id, payload);
        setEditing(updated);
      } else {
        const created = await sectionsApi.create(payload);
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
      await sectionsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<SectionOut>[] = [
    { key: "name", header: "Section", render: (s) => <span className="font-medium">{s.name}</span> },
    { key: "program", header: "Program", render: (s) => programName(s.program_id) },
    { key: "semester", header: "Semester", render: (s) => s.semester_number },
    { key: "strength", header: "Strength", render: (s) => s.strength },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (s) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(s)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(s)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Sections"
        description="Class sections within a program and semester (e.g. CSE Sem 3 - A)."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New section</Button> : undefined}
      />

      <div className="mb-4 max-w-xs">
        <SelectField
          label="Filter by program"
          options={programOptions}
          placeholder="All programs"
          value={programFilter}
          onChange={(e) => setProgramFilter(e.target.value)}
        />
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No sections yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New section</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(s) => s.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit section · ${editing.name}` : "New section"}
        widthClassName="max-w-2xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : editing ? "Save changes" : "Create section"}
            </Button>
          </>
        }
      >
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          <SelectField
            label="Program"
            required
            options={programOptions}
            placeholder="Select a program"
            value={form.program_id}
            error={fieldErrors.program_id}
            onChange={(e) => setForm({ ...form, program_id: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Semester number"
              type="number"
              min={1}
              max={20}
              required
              value={form.semester_number}
              error={fieldErrors.semester_number}
              onChange={(e) => setForm({ ...form, semester_number: e.target.value })}
            />
            <TextField
              label="Section name"
              required
              maxLength={40}
              value={form.name}
              error={fieldErrors.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="A"
            />
          </div>
          <TextField
            label="Strength (students)"
            type="number"
            min={1}
            required
            value={form.strength}
            error={fieldErrors.strength}
            onChange={(e) => setForm({ ...form, strength: e.target.value })}
          />
          <SelectField
            label="Time structure override"
            options={timeStructureOptions}
            placeholder="Inherit from program"
            value={form.time_structure_id}
            onChange={(e) => setForm({ ...form, time_structure_id: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Max periods/day"
              type="number"
              min={1}
              value={form.max_periods_per_day}
              onChange={(e) => setForm({ ...form, max_periods_per_day: e.target.value })}
              placeholder="No limit"
            />
            <TextField
              label="Max consecutive periods"
              type="number"
              min={1}
              value={form.max_consecutive_periods}
              onChange={(e) => setForm({ ...form, max_consecutive_periods: e.target.value })}
              placeholder="No limit"
            />
          </div>
        </form>

        {editing && (
          <div className="mt-6">
            <LabBatchesPanel sectionId={editing.id} readOnly={!canWrite} />
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete section"
        message={`Delete "${deleteTarget?.name}"? Its lab batches and allocations will be affected.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
