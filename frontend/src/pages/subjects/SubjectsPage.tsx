import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { departmentsApi, subjectsApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import { SUBJECT_TYPES, type SubjectOut } from "../../api/types";
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
  code: string;
  name: string;
  department_id: string;
  subject_type: string;
  credits: string;
  periods_per_week: string;
  sessions_per_week: string;
  block_size: string;
  spread_across_days: boolean;
  max_per_day: string;
  requires_lab_batches: boolean;
  avoid_last_period: boolean;
  prefer_afternoon: boolean;
}

const subjectTypeOptions = SUBJECT_TYPES.map((t) => ({ value: t, label: t.replace(/_/g, " ") }));

function makeEmptyForm(departmentId = ""): FormState {
  return {
    code: "",
    name: "",
    department_id: departmentId,
    subject_type: "theory",
    credits: "3",
    periods_per_week: "3",
    sessions_per_week: "3",
    block_size: "1",
    spread_across_days: true,
    max_per_day: "1",
    requires_lab_batches: false,
    avoid_last_period: false,
    prefer_afternoon: false,
  };
}

export default function SubjectsPage() {
  const { canWrite, isCoordinator, user } = useAuth();
  const lockedDepartmentId = isCoordinator && user?.department_id ? String(user.department_id) : "";

  const [departmentFilter, setDepartmentFilter] = useState<string>(lockedDepartmentId);
  const { data: departments } = useFetch(departmentsApi.list, []);

  const listFetcher = useCallback(
    () => subjectsApi.list(departmentFilter ? Number(departmentFilter) : undefined),
    [departmentFilter],
  );
  const { data, loading, error, reload } = useFetch(listFetcher, [departmentFilter]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<SubjectOut | null>(null);
  const [form, setForm] = useState<FormState>(makeEmptyForm(lockedDepartmentId));
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SubjectOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const departmentOptions = useMemo(
    () => (departments ?? []).map((d) => ({ value: d.id, label: `${d.code} — ${d.name}` })),
    [departments],
  );
  const departmentName = useCallback(
    (id: number) => departments?.find((d) => d.id === id)?.name ?? `#${id}`,
    [departments],
  );

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(makeEmptyForm(lockedDepartmentId || departmentFilter));
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, [lockedDepartmentId, departmentFilter]);

  const openEdit = useCallback((s: SubjectOut) => {
    setEditing(s);
    setForm({
      code: s.code,
      name: s.name,
      department_id: String(s.department_id),
      subject_type: s.subject_type,
      credits: String(s.credits),
      periods_per_week: String(s.periods_per_week),
      sessions_per_week: String(s.sessions_per_week),
      block_size: String(s.block_size),
      spread_across_days: s.spread_across_days,
      max_per_day: String(s.max_per_day),
      requires_lab_batches: s.requires_lab_batches,
      avoid_last_period: s.avoid_last_period,
      prefer_afternoon: s.prefer_afternoon,
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.code.trim()) errs.code = "Code is required";
    if (!form.name.trim()) errs.name = "Name is required";
    if (!form.department_id) errs.department_id = "Department is required";
    const credits = Number(form.credits);
    if (!credits || credits <= 0 || credits > 20) errs.credits = "Must be between 0 and 20";
    const ppw = Number(form.periods_per_week);
    if (!ppw || ppw <= 0 || ppw > 40) errs.periods_per_week = "Must be between 1 and 40";
    const spw = Number(form.sessions_per_week);
    if (!spw || spw <= 0 || spw > 40) errs.sessions_per_week = "Must be between 1 and 40";
    const block = Number(form.block_size);
    if (!block || block <= 0 || block > 10) errs.block_size = "Must be between 1 and 10";
    const maxPerDay = Number(form.max_per_day);
    if (!maxPerDay || maxPerDay <= 0 || maxPerDay > 10) errs.max_per_day = "Must be between 1 and 10";
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
      code: form.code,
      name: form.name,
      department_id: Number(form.department_id),
      subject_type: form.subject_type as SubjectOut["subject_type"],
      credits: Number(form.credits),
      periods_per_week: Number(form.periods_per_week),
      sessions_per_week: Number(form.sessions_per_week),
      block_size: Number(form.block_size),
      spread_across_days: form.spread_across_days,
      max_per_day: Number(form.max_per_day),
      requires_lab_batches: form.requires_lab_batches,
      avoid_last_period: form.avoid_last_period,
      prefer_afternoon: form.prefer_afternoon,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        await subjectsApi.update(editing.id, payload);
      } else {
        await subjectsApi.create(payload);
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
      await subjectsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<SubjectOut>[] = [
    { key: "code", header: "Code", render: (s) => <span className="font-medium">{s.code}</span> },
    { key: "name", header: "Name", render: (s) => s.name },
    { key: "department", header: "Department", render: (s) => departmentName(s.department_id) },
    { key: "type", header: "Type", render: (s) => <Badge tone="indigo">{s.subject_type.replace(/_/g, " ")}</Badge> },
    { key: "sessions", header: "Sessions/wk", render: (s) => s.sessions_per_week },
    { key: "periods", header: "Periods/wk", render: (s) => s.periods_per_week },
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
        title="Subjects"
        description="Courses taught to sections, with weekly load and scheduling constraints."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New subject</Button> : undefined}
      />

      {!isCoordinator && (
        <div className="mb-4 max-w-xs">
          <SelectField
            label="Filter by department"
            options={departmentOptions}
            placeholder="All departments"
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
          />
        </div>
      )}

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No subjects yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New subject</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(s) => s.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit subject · ${editing.code}` : "New subject"}
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
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {formError && <ErrorState message={formError} />}
          <div className="grid grid-cols-2 gap-3">
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
              maxLength={150}
              value={form.name}
              error={fieldErrors.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>
          <SelectField
            label="Department"
            required
            disabled={!!lockedDepartmentId}
            options={departmentOptions}
            placeholder="Select a department"
            value={form.department_id}
            error={fieldErrors.department_id}
            onChange={(e) => setForm({ ...form, department_id: e.target.value })}
          />
          <SelectField
            label="Subject type"
            options={subjectTypeOptions}
            value={form.subject_type}
            onChange={(e) => setForm({ ...form, subject_type: e.target.value })}
          />
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Credits"
              type="number"
              step="0.5"
              min={0}
              max={20}
              value={form.credits}
              error={fieldErrors.credits}
              onChange={(e) => setForm({ ...form, credits: e.target.value })}
            />
            <TextField
              label="Periods per week"
              type="number"
              min={1}
              max={40}
              value={form.periods_per_week}
              error={fieldErrors.periods_per_week}
              onChange={(e) => setForm({ ...form, periods_per_week: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Sessions per week"
              type="number"
              min={1}
              max={40}
              value={form.sessions_per_week}
              error={fieldErrors.sessions_per_week}
              onChange={(e) => setForm({ ...form, sessions_per_week: e.target.value })}
              hint="How many separate class meetings per week"
            />
            <TextField
              label="Block size (periods/session)"
              type="number"
              min={1}
              max={10}
              value={form.block_size}
              error={fieldErrors.block_size}
              onChange={(e) => setForm({ ...form, block_size: e.target.value })}
            />
          </div>
          <TextField
            label="Max sessions per day"
            type="number"
            min={1}
            max={10}
            value={form.max_per_day}
            error={fieldErrors.max_per_day}
            onChange={(e) => setForm({ ...form, max_per_day: e.target.value })}
          />
          <div className="flex flex-col gap-2.5 rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
            <CheckboxField
              label="Spread across days"
              checked={form.spread_across_days}
              onChange={(e) => setForm({ ...form, spread_across_days: e.target.checked })}
              hint="Prefer different days rather than clustering sessions"
            />
            <CheckboxField
              label="Requires lab batches"
              checked={form.requires_lab_batches}
              onChange={(e) => setForm({ ...form, requires_lab_batches: e.target.checked })}
              hint="Schedule separately per lab batch instead of the whole section"
            />
            <CheckboxField
              label="Avoid last period"
              checked={form.avoid_last_period}
              onChange={(e) => setForm({ ...form, avoid_last_period: e.target.checked })}
            />
            <CheckboxField
              label="Prefer afternoon"
              checked={form.prefer_afternoon}
              onChange={(e) => setForm({ ...form, prefer_afternoon: e.target.checked })}
            />
          </div>
        </form>
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete subject"
        message={`Delete "${deleteTarget?.name}"? Related allocations will be affected.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
