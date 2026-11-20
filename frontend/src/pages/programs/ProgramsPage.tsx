import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { departmentsApi, programsApi, timeStructuresApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { ProgramOut } from "../../api/types";
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

interface FormState {
  department_id: string;
  name: string;
  code: string;
  duration_semesters: string;
  time_structure_id: string;
}

const emptyForm: FormState = {
  department_id: "",
  name: "",
  code: "",
  duration_semesters: "8",
  time_structure_id: "",
};

export default function ProgramsPage() {
  const { canWrite } = useAuth();
  const [departmentFilter, setDepartmentFilter] = useState<string>("");

  const { data: departments } = useFetch(departmentsApi.list, []);
  const { data: timeStructures } = useFetch(timeStructuresApi.list, []);

  const listFetcher = useCallback(
    () => programsApi.list(departmentFilter ? Number(departmentFilter) : undefined),
    [departmentFilter],
  );
  const { data, loading, error, reload } = useFetch(listFetcher, [departmentFilter]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<ProgramOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ProgramOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const departmentOptions = useMemo(
    () => (departments ?? []).map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })),
    [departments],
  );
  const departmentName = useCallback(
    (id: number) => departments?.find((d) => d.id === id)?.name ?? `#${id}`,
    [departments],
  );
  const timeStructureOptions = useMemo(
    () => (timeStructures ?? []).map((t) => ({ value: t.id, label: t.name })),
    [timeStructures],
  );
  const timeStructureName = useCallback(
    (id: number | null) => (id ? timeStructures?.find((t) => t.id === id)?.name ?? `#${id}` : "—"),
    [timeStructures],
  );

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm({ ...emptyForm, department_id: departmentFilter });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, [departmentFilter]);

  const openEdit = useCallback((p: ProgramOut) => {
    setEditing(p);
    setForm({
      department_id: String(p.department_id),
      name: p.name,
      code: p.code,
      duration_semesters: String(p.duration_semesters),
      time_structure_id: p.time_structure_id ? String(p.time_structure_id) : "",
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.department_id) errs.department_id = "Department is required";
    if (!form.name.trim()) errs.name = "Name is required";
    if (!form.code.trim()) errs.code = "Code is required";
    const duration = Number(form.duration_semesters);
    if (!form.duration_semesters || duration <= 0 || duration > 20) {
      errs.duration_semesters = "Must be between 1 and 20";
    }
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
      department_id: Number(form.department_id),
      name: form.name,
      code: form.code,
      duration_semesters: Number(form.duration_semesters),
      time_structure_id: form.time_structure_id ? Number(form.time_structure_id) : null,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        await programsApi.update(editing.id, payload);
      } else {
        await programsApi.create(payload);
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
      await programsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<ProgramOut>[] = [
    { key: "code", header: "Code", render: (p) => <span className="font-medium">{p.code}</span> },
    { key: "name", header: "Name", render: (p) => p.name },
    { key: "department", header: "Department", render: (p) => departmentName(p.department_id) },
    { key: "duration", header: "Duration (sem)", render: (p) => p.duration_semesters },
    { key: "time_structure", header: "Time structure", render: (p) => timeStructureName(p.time_structure_id) },
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
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(p)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Programs"
        description="Degree programs within a department (e.g. B.Tech CSE)."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New program</Button> : undefined}
      />

      <div className="mb-4 max-w-xs">
        <SelectField
          label="Filter by department"
          options={departmentOptions}
          placeholder="All departments"
          value={departmentFilter}
          onChange={(e) => setDepartmentFilter(e.target.value)}
        />
      </div>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState
          title="No programs yet"
          action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New program</Button> : undefined}
        />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(p) => p.id} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? "Edit program" : "New program"}
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
            label="Department"
            required
            options={departmentOptions}
            placeholder="Select a department"
            value={form.department_id}
            error={fieldErrors.department_id}
            onChange={(e) => setForm({ ...form, department_id: e.target.value })}
          />
          <TextField
            label="Code"
            required
            maxLength={20}
            value={form.code}
            error={fieldErrors.code}
            onChange={(e) => setForm({ ...form, code: e.target.value })}
          />
          <TextField
            label="Name"
            required
            maxLength={120}
            value={form.name}
            error={fieldErrors.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <TextField
            label="Duration (semesters)"
            type="number"
            min={1}
            max={20}
            required
            value={form.duration_semesters}
            error={fieldErrors.duration_semesters}
            onChange={(e) => setForm({ ...form, duration_semesters: e.target.value })}
          />
          <SelectField
            label="Default time structure"
            options={timeStructureOptions}
            placeholder="None"
            value={form.time_structure_id}
            error={fieldErrors.time_structure_id}
            onChange={(e) => setForm({ ...form, time_structure_id: e.target.value })}
            hint="Sections inherit this unless overridden per-section."
          />
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete program"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
