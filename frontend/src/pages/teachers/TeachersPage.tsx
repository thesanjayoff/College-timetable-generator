import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { departmentsApi, teachersApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import type { TeacherOut } from "../../api/types";
import { DAY_NAMES } from "../../api/types";
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
import { TeacherPreferencesPanel } from "./TeacherPreferencesPanel";
import { TeacherSubjectsPanel } from "./TeacherSubjectsPanel";
import { TeacherUnavailabilityPanel } from "./TeacherUnavailabilityPanel";

interface FormState {
  code: string;
  name: string;
  department_id: string;
  email: string;
  phone: string;
  max_periods_per_day: string;
  max_periods_per_week: string;
  max_consecutive_periods: string;
  is_visiting: boolean;
  visiting_days: number[];
}

function makeEmptyForm(departmentId = ""): FormState {
  return {
    code: "",
    name: "",
    department_id: departmentId,
    email: "",
    phone: "",
    max_periods_per_day: "6",
    max_periods_per_week: "24",
    max_consecutive_periods: "4",
    is_visiting: false,
    visiting_days: [],
  };
}

type DrawerTab = "details" | "subjects" | "unavailability" | "preferences";

export default function TeachersPage() {
  const { canWrite, isCoordinator, user } = useAuth();
  const lockedDepartmentId = isCoordinator && user?.department_id ? String(user.department_id) : "";

  const [departmentFilter, setDepartmentFilter] = useState<string>(lockedDepartmentId);
  const { data: departments } = useFetch(departmentsApi.list, []);

  const listFetcher = useCallback(
    () => teachersApi.list(departmentFilter ? Number(departmentFilter) : undefined),
    [departmentFilter],
  );
  const { data, loading, error, reload } = useFetch(listFetcher, [departmentFilter]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tab, setTab] = useState<DrawerTab>("details");
  const [editing, setEditing] = useState<TeacherOut | null>(null);
  const [form, setForm] = useState<FormState>(makeEmptyForm(lockedDepartmentId));
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TeacherOut | null>(null);
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
    setTab("details");
    setForm(makeEmptyForm(lockedDepartmentId || departmentFilter));
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, [lockedDepartmentId, departmentFilter]);

  const openEdit = useCallback((t: TeacherOut) => {
    setEditing(t);
    setTab("details");
    setForm({
      code: t.code,
      name: t.name,
      department_id: String(t.department_id),
      email: t.email ?? "",
      phone: t.phone ?? "",
      max_periods_per_day: String(t.max_periods_per_day),
      max_periods_per_week: String(t.max_periods_per_week),
      max_consecutive_periods: String(t.max_consecutive_periods),
      is_visiting: t.is_visiting,
      visiting_days: t.visiting_days ?? [],
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function toggleVisitingDay(day: number) {
    setForm((f) => ({
      ...f,
      visiting_days: f.visiting_days.includes(day)
        ? f.visiting_days.filter((d) => d !== day)
        : [...f.visiting_days, day].sort(),
    }));
  }

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.code.trim()) errs.code = "Code is required";
    if (!form.name.trim()) errs.name = "Name is required";
    if (!form.department_id) errs.department_id = "Department is required";
    const perDay = Number(form.max_periods_per_day);
    if (!perDay || perDay <= 0 || perDay > 12) errs.max_periods_per_day = "Must be between 1 and 12";
    const perWeek = Number(form.max_periods_per_week);
    if (!perWeek || perWeek <= 0 || perWeek > 60) errs.max_periods_per_week = "Must be between 1 and 60";
    const consecutive = Number(form.max_consecutive_periods);
    if (!consecutive || consecutive <= 0 || consecutive > 12) {
      errs.max_consecutive_periods = "Must be between 1 and 12";
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
      code: form.code,
      name: form.name,
      department_id: Number(form.department_id),
      email: form.email.trim() || null,
      phone: form.phone.trim() || null,
      max_periods_per_day: Number(form.max_periods_per_day),
      max_periods_per_week: Number(form.max_periods_per_week),
      max_consecutive_periods: Number(form.max_consecutive_periods),
      is_visiting: form.is_visiting,
      visiting_days: form.is_visiting && form.visiting_days.length > 0 ? form.visiting_days : null,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await teachersApi.update(editing.id, payload);
        setEditing(updated);
      } else {
        const created = await teachersApi.create(payload);
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
      await teachersApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<TeacherOut>[] = [
    { key: "code", header: "Code", render: (t) => <span className="font-medium">{t.code}</span> },
    { key: "name", header: "Name", render: (t) => t.name },
    { key: "department", header: "Department", render: (t) => departmentName(t.department_id) },
    {
      key: "visiting",
      header: "Visiting",
      render: (t) => (t.is_visiting ? <Badge tone="amber">Visiting</Badge> : <Badge tone="slate">Regular</Badge>),
    },
    { key: "load", header: "Max/day · week", render: (t) => `${t.max_periods_per_day} · ${t.max_periods_per_week}` },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (t) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(t)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(t)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  const tabs: { key: DrawerTab; label: string }[] = [
    { key: "details", label: "Details" },
    { key: "subjects", label: "Subjects" },
    { key: "unavailability", label: "Unavailability" },
    { key: "preferences", label: "Preferences" },
  ];

  return (
    <div>
      <PageHeader
        title="Teachers"
        description="Faculty members, their eligible subjects, availability and preferences."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New teacher</Button> : undefined}
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
        <EmptyState title="No teachers yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New teacher</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(t) => t.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit teacher · ${editing.name}` : "New teacher"}
        widthClassName="max-w-2xl"
        footer={
          tab === "details" ? (
            <>
              <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
                Close
              </Button>
              <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Saving…" : editing ? "Save changes" : "Create teacher"}
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
          )
        }
      >
        {editing && (
          <div className="mb-4 flex gap-1 border-b border-slate-200 dark:border-slate-700">
            {tabs.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={`border-b-2 px-3 py-2 text-sm font-medium transition ${
                  tab === t.key
                    ? "border-indigo-600 text-indigo-700 dark:border-indigo-400 dark:text-indigo-300"
                    : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {tab === "details" && (
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
                maxLength={120}
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
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              <TextField
                label="Phone"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <TextField
                label="Max/day"
                type="number"
                min={1}
                max={12}
                value={form.max_periods_per_day}
                error={fieldErrors.max_periods_per_day}
                onChange={(e) => setForm({ ...form, max_periods_per_day: e.target.value })}
              />
              <TextField
                label="Max/week"
                type="number"
                min={1}
                max={60}
                value={form.max_periods_per_week}
                error={fieldErrors.max_periods_per_week}
                onChange={(e) => setForm({ ...form, max_periods_per_week: e.target.value })}
              />
              <TextField
                label="Max consecutive"
                type="number"
                min={1}
                max={12}
                value={form.max_consecutive_periods}
                error={fieldErrors.max_consecutive_periods}
                onChange={(e) => setForm({ ...form, max_consecutive_periods: e.target.value })}
              />
            </div>
            <div className="rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
              <CheckboxField
                label="Visiting faculty"
                checked={form.is_visiting}
                onChange={(e) => setForm({ ...form, is_visiting: e.target.checked })}
                hint="Only available on specific days"
              />
              {form.is_visiting && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {DAY_NAMES.map((name, idx) => (
                    <label
                      key={idx}
                      className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-medium transition ${
                        form.visiting_days.includes(idx)
                          ? "border-indigo-500 bg-indigo-50 text-indigo-700 dark:border-indigo-400 dark:bg-indigo-500/15 dark:text-indigo-300"
                          : "border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-300"
                      }`}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={form.visiting_days.includes(idx)}
                        onChange={() => toggleVisitingDay(idx)}
                      />
                      {name}
                    </label>
                  ))}
                </div>
              )}
            </div>
          </form>
        )}

        {tab === "subjects" && editing && <TeacherSubjectsPanel teacherId={editing.id} readOnly={!canWrite} />}
        {tab === "unavailability" && editing && (
          <TeacherUnavailabilityPanel teacherId={editing.id} readOnly={!canWrite} />
        )}
        {tab === "preferences" && editing && (
          <TeacherPreferencesPanel teacherId={editing.id} readOnly={!canWrite} />
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete teacher"
        message={`Delete "${deleteTarget?.name}"? Related allocations will be affected.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
