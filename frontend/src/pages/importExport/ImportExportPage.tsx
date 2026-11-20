import { useMemo, useRef, useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { exportsApi, importApi, roomsApi, sectionsApi, teachersApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import type { ImportReportOut } from "../../api/types";
import {
  Badge,
  Button,
  Card,
  ErrorState,
  PageHeader,
  SelectField,
  Table,
  TextField,
} from "../../components/ui";
import type { TableColumn } from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { downloadBlob } from "../../lib/download";
import { useVersionIdParam, VersionPicker } from "../versions/VersionPicker";

type ExportFormat = "excel" | "pdf" | "ical";
type ExportTarget = "section" | "teacher" | "room" | "all-sections" | "all-teachers";

const TARGETS_BY_FORMAT: Record<ExportFormat, { value: ExportTarget; label: string }[]> = {
  excel: [
    { value: "section", label: "Single section" },
    { value: "teacher", label: "Single teacher" },
    { value: "room", label: "Single room" },
    { value: "all-sections", label: "All sections (one workbook)" },
    { value: "all-teachers", label: "All teachers (one workbook)" },
  ],
  pdf: [
    { value: "section", label: "Single section" },
    { value: "teacher", label: "Single teacher" },
    { value: "room", label: "Single room" },
  ],
  ical: [
    { value: "section", label: "Single section" },
    { value: "teacher", label: "Single teacher" },
  ],
};

export default function ImportExportPage() {
  const { canWrite } = useAuth();
  const [versionId, setVersionId] = useVersionIdParam();

  const { data: sections } = useFetch(sectionsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);
  const { data: rooms } = useFetch(roomsApi.list, []);

  const [format, setFormat] = useState<ExportFormat>("excel");
  const [target, setTarget] = useState<ExportTarget>("section");
  const [entityId, setEntityId] = useState("");
  const [collegeName, setCollegeName] = useState("");
  const [termStart, setTermStart] = useState(() => new Date().toISOString().slice(0, 10));
  const [termWeeks, setTermWeeks] = useState("16");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const entityOptions = useMemo(() => {
    if (target === "section") return (sections ?? []).map((s) => ({ value: s.id, label: s.name }));
    if (target === "teacher") return (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` }));
    if (target === "room") return (rooms ?? []).map((r) => ({ value: r.id, label: `${r.code} — ${r.name}` }));
    return [];
  }, [target, sections, teachers, rooms]);

  const needsEntity = target === "section" || target === "teacher" || target === "room";

  function handleFormatChange(next: ExportFormat) {
    setFormat(next);
    const available = TARGETS_BY_FORMAT[next];
    if (!available.some((t) => t.value === target)) {
      setTarget(available[0].value);
      setEntityId("");
    }
  }

  async function handleExport() {
    if (versionId === null) return;
    setExporting(true);
    setExportError(null);
    try {
      let result: { blob: Blob; filename: string };
      const id = Number(entityId);
      if (format === "excel") {
        if (target === "section") result = await exportsApi.excelSection(versionId, id, collegeName);
        else if (target === "teacher") result = await exportsApi.excelTeacher(versionId, id, collegeName);
        else if (target === "room") result = await exportsApi.excelRoom(versionId, id, collegeName);
        else if (target === "all-sections") result = await exportsApi.excelAllSections(versionId, collegeName);
        else result = await exportsApi.excelAllTeachers(versionId, collegeName);
      } else if (format === "pdf") {
        if (target === "section") result = await exportsApi.pdfSection(versionId, id, collegeName);
        else if (target === "teacher") result = await exportsApi.pdfTeacher(versionId, id, collegeName);
        else result = await exportsApi.pdfRoom(versionId, id, collegeName);
      } else {
        if (target === "section") result = await exportsApi.icalSection(versionId, id, termStart, Number(termWeeks) || 16);
        else result = await exportsApi.icalTeacher(versionId, id, termStart, Number(termWeeks) || 16);
      }
      downloadBlob(result.blob, result.filename);
    } catch (err) {
      setExportError(getErrorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  const canExport = versionId !== null && (!needsEntity || !!entityId) && (format !== "ical" || !!termStart);

  // ---- Import state ----
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [importing, setImporting] = useState<"validate" | "import" | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [report, setReport] = useState<ImportReportOut | null>(null);
  const [templateError, setTemplateError] = useState<string | null>(null);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  async function handleDownloadTemplate() {
    setDownloadingTemplate(true);
    setTemplateError(null);
    try {
      const result = await importApi.downloadTemplate();
      downloadBlob(result.blob, result.filename);
    } catch (err) {
      setTemplateError(getErrorMessage(err));
    } finally {
      setDownloadingTemplate(false);
    }
  }

  async function handleImport(dryRun: boolean) {
    if (!file) return;
    setImporting(dryRun ? "validate" : "import");
    setImportError(null);
    setReport(null);
    try {
      const result = await importApi.importExcel(file, dryRun);
      setReport(result);
    } catch (err) {
      setImportError(getErrorMessage(err));
    } finally {
      setImporting(null);
    }
  }

  const errorColumns: TableColumn<ImportReportOut["errors"][number]>[] = [
    { key: "sheet", header: "Sheet", render: (e) => e.sheet },
    { key: "row", header: "Row", render: (e) => e.row },
    { key: "column", header: "Column", render: (e) => e.column },
    { key: "message", header: "Problem", render: (e) => e.message },
  ];

  return (
    <div>
      <PageHeader
        title="Import / Export"
        description="Bulk import master data from a spreadsheet, and export a version's timetable to Excel, PDF or iCal."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="px-5 py-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-100">Export a timetable</h2>
          <div className="flex flex-col gap-3">
            <VersionPicker value={versionId} onChange={setVersionId} hint="Which version's sessions to export" />

            <div className="grid grid-cols-2 gap-3">
              <SelectField
                label="Format"
                options={[
                  { value: "excel", label: "Excel" },
                  { value: "pdf", label: "PDF" },
                  { value: "ical", label: "iCal" },
                ]}
                value={format}
                onChange={(e) => handleFormatChange(e.target.value as ExportFormat)}
              />
              <SelectField
                label="Target"
                options={TARGETS_BY_FORMAT[format]}
                value={target}
                onChange={(e) => {
                  setTarget(e.target.value as ExportTarget);
                  setEntityId("");
                }}
              />
            </div>

            {needsEntity && (
              <SelectField
                label={target === "section" ? "Section" : target === "teacher" ? "Teacher" : "Room"}
                options={entityOptions}
                placeholder="Select…"
                value={entityId}
                onChange={(e) => setEntityId(e.target.value)}
              />
            )}

            {format !== "ical" && (
              <TextField
                label="College name (optional)"
                value={collegeName}
                onChange={(e) => setCollegeName(e.target.value)}
                placeholder="Printed on the exported sheet"
              />
            )}

            {format === "ical" && (
              <div className="grid grid-cols-2 gap-3">
                <TextField
                  label="Term start date"
                  type="date"
                  value={termStart}
                  onChange={(e) => setTermStart(e.target.value)}
                />
                <TextField
                  label="Term length (weeks)"
                  type="number"
                  min={1}
                  value={termWeeks}
                  onChange={(e) => setTermWeeks(e.target.value)}
                />
              </div>
            )}

            {exportError && <ErrorState message={exportError} />}

            <div>
              <Button variant="primary" disabled={!canExport || exporting} onClick={handleExport}>
                {exporting ? "Downloading…" : "Download export"}
              </Button>
            </div>
          </div>
        </Card>

        <Card className="px-5 py-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-100">Bulk import master data</h2>
          <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
            Fill in the template workbook, then validate it before importing. Nothing is written to the database if any
            row fails validation — fix every reported error and re-upload.
          </p>

          {templateError && <div className="mb-3"><ErrorState message={templateError} /></div>}
          <div className="mb-4">
            <Button variant="secondary" disabled={downloadingTemplate} onClick={handleDownloadTemplate}>
              {downloadingTemplate ? "Preparing…" : "Download template"}
            </Button>
          </div>

          {canWrite ? (
            <>
              <div className="mb-3">
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
                  Workbook file
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  className="block w-full text-sm text-slate-600 dark:text-slate-300"
                />
              </div>

              {importError && <div className="mb-3"><ErrorState message={importError} /></div>}

              <div className="flex gap-2">
                <Button variant="secondary" disabled={!file || importing !== null} onClick={() => handleImport(true)}>
                  {importing === "validate" ? "Validating…" : "Validate only"}
                </Button>
                <Button variant="primary" disabled={!file || importing !== null} onClick={() => handleImport(false)}>
                  {importing === "import" ? "Importing…" : "Validate and import"}
                </Button>
              </div>

              {report && (
                <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
                  <div className="mb-2 flex items-center gap-2">
                    <Badge tone={report.committed ? "green" : report.errors.length > 0 ? "rose" : "amber"}>
                      {report.committed ? "Imported" : report.errors.length > 0 ? "Validation failed" : "Validated — not imported"}
                    </Badge>
                  </div>
                  {Object.keys(report.created_counts).length > 0 && (
                    <div className="mb-3 flex flex-wrap gap-3 text-sm text-slate-600 dark:text-slate-300">
                      {Object.entries(report.created_counts).map(([k, v]) => (
                        <span key={k}>
                          {k.replace(/_/g, " ")}: <span className="font-medium">{v}</span>
                        </span>
                      ))}
                    </div>
                  )}
                  {report.errors.length > 0 ? (
                    <Table
                      columns={errorColumns}
                      rows={report.errors}
                      rowKey={(e) => `${e.sheet}-${e.row}-${e.column}-${e.message}`}
                    />
                  ) : (
                    <p className="text-sm text-emerald-600 dark:text-emerald-400">No errors found.</p>
                  )}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-500 dark:text-slate-400">You have read-only access — importing is disabled.</p>
          )}
        </Card>
      </div>
    </div>
  );
}
