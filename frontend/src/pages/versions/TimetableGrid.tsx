import { Fragment, useMemo, useState } from "react";
import type { DragEvent } from "react";
import type { TimetableSessionOut } from "../../api/types";

export interface GridDay {
  day_index: number;
  name: string;
}

export interface GridPeriod {
  period_index: number;
  label: string;
  sublabel?: string;
  isTeaching: boolean;
}

export type ViewAxis = "section" | "teacher" | "room";

interface TimetableGridProps {
  sessions: TimetableSessionOut[];
  days: GridDay[];
  periods: GridPeriod[];
  axis: ViewAxis;
  sectionLabel: (id: number) => string;
  canEdit: boolean;
  selectedSessionId: number | null;
  onSelect: (session: TimetableSessionOut) => void;
  onDropSession: (sessionId: number, dayIndex: number, periodIndex: number) => void;
}

const kindStyles: Record<string, string> = {
  regular: "border-indigo-300 bg-indigo-50 text-indigo-900 dark:border-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-100",
  combined: "border-purple-300 bg-purple-50 text-purple-900 dark:border-purple-700 dark:bg-purple-950/50 dark:text-purple-100",
  elective: "border-teal-300 bg-teal-50 text-teal-900 dark:border-teal-700 dark:bg-teal-950/50 dark:text-teal-100",
};

/**
 * Days are rows, periods are columns. Session chips are positioned as separate grid
 * items spanning `num_periods` columns within their day's row; empty background cells
 * underneath double as drop targets for drag-and-drop moves.
 */
export function TimetableGrid({
  sessions,
  days,
  periods,
  axis,
  sectionLabel,
  canEdit,
  selectedSessionId,
  onSelect,
  onDropSession,
}: TimetableGridProps) {
  const [dragOverCell, setDragOverCell] = useState<string | null>(null);

  const periodColumn = useMemo(() => {
    const map = new Map<number, number>();
    periods.forEach((p, idx) => map.set(p.period_index, idx));
    return map;
  }, [periods]);

  const dayRow = useMemo(() => {
    const map = new Map<number, number>();
    days.forEach((d, idx) => map.set(d.day_index, idx));
    return map;
  }, [days]);

  function secondaryLine(s: TimetableSessionOut): string {
    const parts: string[] = [];
    if (axis !== "teacher" && s.teacher_name) parts.push(s.teacher_name);
    if (axis !== "room" && s.room_code) parts.push(s.room_code);
    if (axis !== "section" && s.section_ids.length > 0) {
      parts.push(s.section_ids.map(sectionLabel).join(", "));
    }
    return parts.join(" · ");
  }

  function handleDragStart(e: DragEvent<HTMLDivElement>, session: TimetableSessionOut) {
    e.dataTransfer.setData("text/plain", String(session.id));
    e.dataTransfer.effectAllowed = "move";
  }

  function handleDrop(e: DragEvent<HTMLDivElement>, dayIndex: number, periodIndex: number) {
    e.preventDefault();
    setDragOverCell(null);
    const raw = e.dataTransfer.getData("text/plain");
    const sessionId = Number(raw);
    if (!raw || Number.isNaN(sessionId)) return;
    onDropSession(sessionId, dayIndex, periodIndex);
  }

  const gridTemplateColumns = `110px repeat(${periods.length}, minmax(86px, 1fr))`;
  const gridTemplateRows = `auto repeat(${days.length}, minmax(60px, auto))`;

  return (
    <div className="thin-scrollbar overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <div
        className="relative grid min-w-max"
        style={{ gridTemplateColumns, gridTemplateRows }}
      >
        {/* Corner cell */}
        <div
          className="sticky left-0 z-10 border-b border-r border-slate-200 bg-slate-50 px-2 py-2 text-xs font-semibold text-slate-500 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400"
          style={{ gridRow: 1, gridColumn: 1 }}
        >
          Day / Period
        </div>

        {/* Period header cells */}
        {periods.map((p, colIdx) => (
          <div
            key={`ph-${p.period_index}`}
            className={`border-b border-r border-slate-200 px-2 py-2 text-center text-xs font-semibold dark:border-slate-700 ${
              p.isTeaching
                ? "bg-slate-50 text-slate-600 dark:bg-slate-800/60 dark:text-slate-300"
                : "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500"
            }`}
            style={{ gridRow: 1, gridColumn: colIdx + 2 }}
          >
            <div>{p.label}</div>
            {p.sublabel && <div className="font-normal text-[10px]">{p.sublabel}</div>}
          </div>
        ))}

        {/* Day label cells + background drop-target cells */}
        {days.map((d, rowIdx) => (
          <Fragment key={`dl-${d.day_index}`}>
            <div
              className="sticky left-0 z-10 border-b border-r border-slate-200 bg-slate-50 px-2 py-2 text-sm font-medium text-slate-700 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-200"
              style={{ gridRow: rowIdx + 2, gridColumn: 1 }}
            >
              {d.name}
            </div>
            {periods.map((p, colIdx) => {
              const cellKey = `${d.day_index}-${p.period_index}`;
              const isDropTarget = canEdit && p.isTeaching;
              return (
                <div
                  key={cellKey}
                  className={`border-b border-r border-slate-100 dark:border-slate-800 ${
                    p.isTeaching ? "" : "bg-slate-50/70 dark:bg-slate-900/40"
                  } ${dragOverCell === cellKey ? "bg-indigo-100 dark:bg-indigo-900/40" : ""}`}
                  style={{ gridRow: rowIdx + 2, gridColumn: colIdx + 2 }}
                  onDragOver={
                    isDropTarget
                      ? (e) => {
                          e.preventDefault();
                          setDragOverCell(cellKey);
                        }
                      : undefined
                  }
                  onDragLeave={isDropTarget ? () => setDragOverCell(null) : undefined}
                  onDrop={isDropTarget ? (e) => handleDrop(e, d.day_index, p.period_index) : undefined}
                />
              );
            })}
          </Fragment>
        ))}

        {/* Session chips, placed on top of the background cells */}
        {sessions.map((s) => {
          const colIdx = periodColumn.get(s.period_index);
          const rowIdx = dayRow.get(s.day_index);
          if (colIdx === undefined || rowIdx === undefined) return null;
          const draggable = canEdit && !s.is_locked;
          const selected = selectedSessionId === s.id;
          return (
            <div
              key={s.id}
              draggable={draggable}
              onDragStart={draggable ? (e) => handleDragStart(e, s) : undefined}
              onDrop={
                canEdit
                  ? (e) => handleDrop(e, s.day_index, s.period_index)
                  : undefined
              }
              onDragOver={canEdit ? (e) => e.preventDefault() : undefined}
              onClick={() => onSelect(s)}
              className={`m-0.5 flex cursor-pointer flex-col justify-center overflow-hidden rounded-md border px-2 py-1 text-xs shadow-sm transition ${
                kindStyles[s.kind] ?? kindStyles.regular
              } ${draggable ? "cursor-grab active:cursor-grabbing" : ""} ${
                selected ? "ring-2 ring-indigo-500 ring-offset-1" : ""
              } ${s.is_locked ? "border-dashed" : ""}`}
              style={{
                gridRow: rowIdx + 2,
                gridColumn: `${colIdx + 2} / span ${s.num_periods}`,
                zIndex: 1,
              }}
              title={`${s.subject_code ?? "Subject"} · ${secondaryLine(s)}`}
            >
              <div className="flex items-center gap-1 font-semibold">
                {s.is_locked && <span aria-label="Locked">🔒</span>}
                <span className="truncate">{s.subject_code ?? `#${s.id}`}</span>
              </div>
              <div className="truncate text-[11px] opacity-80">{secondaryLine(s)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
