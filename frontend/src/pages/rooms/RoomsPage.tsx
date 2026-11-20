import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { roomsApi } from "../../api/resources";
import { getErrorMessage, getFieldErrors } from "../../api/client";
import { ROOM_TYPES, type RoomOut } from "../../api/types";
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
import { RoomUnavailabilityPanel } from "./RoomUnavailabilityPanel";

interface FormState {
  code: string;
  name: string;
  room_type: string;
  capacity: string;
  lab_category: string;
  equipment_tags: string;
  building: string;
  floor: string;
}

const emptyForm: FormState = {
  code: "",
  name: "",
  room_type: "classroom",
  capacity: "60",
  lab_category: "",
  equipment_tags: "",
  building: "",
  floor: "",
};

const roomTypeOptions = ROOM_TYPES.map((t) => ({ value: t, label: t.replace("_", " ") }));

export default function RoomsPage() {
  const { canWrite } = useAuth();
  const { data, loading, error, reload } = useFetch(roomsApi.list, []);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<RoomOut | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<RoomOut | null>(null);
  const [deleting, setDeleting] = useState(false);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(emptyForm);
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  const openEdit = useCallback((room: RoomOut) => {
    setEditing(room);
    setForm({
      code: room.code,
      name: room.name,
      room_type: room.room_type,
      capacity: String(room.capacity),
      lab_category: room.lab_category ?? "",
      equipment_tags: (room.equipment_tags ?? []).join(", "),
      building: room.building ?? "",
      floor: room.floor !== null ? String(room.floor) : "",
    });
    setFieldErrors({});
    setFormError(null);
    setDrawerOpen(true);
  }, []);

  function validate(): Record<string, string> {
    const errs: Record<string, string> = {};
    if (!form.code.trim()) errs.code = "Code is required";
    if (!form.name.trim()) errs.name = "Name is required";
    const capacity = Number(form.capacity);
    if (!capacity || capacity <= 0) errs.capacity = "Must be a positive number";
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
      room_type: form.room_type as RoomOut["room_type"],
      capacity: Number(form.capacity),
      lab_category: form.lab_category.trim() || null,
      equipment_tags: form.equipment_tags.trim()
        ? form.equipment_tags.split(",").map((t) => t.trim()).filter(Boolean)
        : null,
      building: form.building.trim() || null,
      floor: form.floor ? Number(form.floor) : null,
    };
    setSubmitting(true);
    setFormError(null);
    try {
      if (editing) {
        const updated = await roomsApi.update(editing.id, payload);
        setEditing(updated);
      } else {
        const created = await roomsApi.create(payload);
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
      await roomsApi.remove(deleteTarget.id);
      setDeleteTarget(null);
      reload();
    } catch (err) {
      setFormError(getErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }

  const columns: TableColumn<RoomOut>[] = [
    { key: "code", header: "Code", render: (r) => <span className="font-medium">{r.code}</span> },
    { key: "name", header: "Name", render: (r) => r.name },
    { key: "type", header: "Type", render: (r) => <Badge tone="indigo">{r.room_type.replace("_", " ")}</Badge> },
    { key: "capacity", header: "Capacity", render: (r) => r.capacity },
    { key: "location", header: "Location", render: (r) => [r.building, r.floor !== null ? `Floor ${r.floor}` : null].filter(Boolean).join(" · ") || "—" },
  ];
  if (canWrite) {
    columns.push({
      key: "actions",
      header: "",
      className: "text-right",
      render: (r) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => openEdit(r)}>
            Edit
          </Button>
          <Button size="sm" variant="danger" onClick={() => setDeleteTarget(r)}>
            Delete
          </Button>
        </div>
      ),
    });
  }

  return (
    <div>
      <PageHeader
        title="Rooms"
        description="Classrooms, labs and seminar halls available for scheduling."
        action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New room</Button> : undefined}
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && data.length === 0 && (
        <EmptyState title="No rooms yet" action={canWrite ? <Button variant="primary" onClick={openCreate}>+ New room</Button> : undefined} />
      )}
      {!loading && !error && data && data.length > 0 && (
        <Table columns={columns} rows={data} rowKey={(r) => r.id} onRowClick={canWrite ? openEdit : undefined} />
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editing ? `Edit room · ${editing.code}` : "New room"}
        widthClassName="max-w-2xl"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDrawerOpen(false)}>
              Close
            </Button>
            <Button variant="primary" onClick={handleSubmit} disabled={submitting}>
              {submitting ? "Saving…" : editing ? "Save changes" : "Create room"}
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
              placeholder="LH-101"
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
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Room type"
              options={roomTypeOptions}
              value={form.room_type}
              onChange={(e) => setForm({ ...form, room_type: e.target.value })}
            />
            <TextField
              label="Capacity"
              type="number"
              min={1}
              required
              value={form.capacity}
              error={fieldErrors.capacity}
              onChange={(e) => setForm({ ...form, capacity: e.target.value })}
            />
          </div>
          {form.room_type === "lab" && (
            <TextField
              label="Lab category"
              value={form.lab_category}
              onChange={(e) => setForm({ ...form, lab_category: e.target.value })}
              placeholder="e.g. Computer Lab, Electronics Lab"
            />
          )}
          <TextField
            label="Equipment tags"
            value={form.equipment_tags}
            onChange={(e) => setForm({ ...form, equipment_tags: e.target.value })}
            placeholder="projector, smart board (comma separated)"
          />
          <div className="grid grid-cols-2 gap-3">
            <TextField
              label="Building"
              value={form.building}
              onChange={(e) => setForm({ ...form, building: e.target.value })}
            />
            <TextField
              label="Floor"
              type="number"
              value={form.floor}
              onChange={(e) => setForm({ ...form, floor: e.target.value })}
            />
          </div>
        </form>

        {editing && (
          <div className="mt-6">
            <RoomUnavailabilityPanel roomId={editing.id} readOnly={!canWrite} />
          </div>
        )}
      </Drawer>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Delete room"
        message={`Delete "${deleteTarget?.name}"? This cannot be undone.`}
        busy={deleting}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
