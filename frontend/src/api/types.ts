// Mirrors backend/app/models/enums.py — keep values in sync with the Python enums.

export type SubjectType =
  | "theory"
  | "lab"
  | "tutorial"
  | "project"
  | "library"
  | "sports"
  | "mentoring"
  | "open_elective"
  | "professional_elective";

export const SUBJECT_TYPES: SubjectType[] = [
  "theory",
  "lab",
  "tutorial",
  "project",
  "library",
  "sports",
  "mentoring",
  "open_elective",
  "professional_elective",
];

export type RoomType = "classroom" | "lab" | "seminar_hall";
export const ROOM_TYPES: RoomType[] = ["classroom", "lab", "seminar_hall"];

export type PeriodKind = "teaching" | "break" | "lunch";
export const PERIOD_KINDS: PeriodKind[] = ["teaching", "break", "lunch"];

export type SessionKind = "regular" | "combined" | "elective";

export type UserRole = "admin" | "coordinator" | "viewer";
export const USER_ROLES: UserRole[] = ["admin", "coordinator", "viewer"];

export type VersionStatus = "draft" | "published" | "archived";

export type PreferenceType =
  | "preferred_day"
  | "free_day"
  | "no_first_period"
  | "no_last_period"
  | "avoid_back_to_back"
  | "same_room";

export const PREFERENCE_TYPES: PreferenceType[] = [
  "preferred_day",
  "free_day",
  "no_first_period",
  "no_last_period",
  "avoid_back_to_back",
  "same_room",
];

export type SolveStatus =
  | "pending"
  | "running"
  | "feasible"
  | "optimal"
  | "infeasible"
  | "stopped"
  | "failed";

export const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// ---- Auth / Users ----

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: number;
  email: string;
  name: string;
  role: UserRole;
  department_id: number | null;
  teacher_id: number | null;
  is_active: boolean;
}

export interface UserCreate {
  email: string;
  name: string;
  role: UserRole;
  department_id?: number | null;
  teacher_id?: number | null;
  is_active?: boolean;
  password: string;
}

export interface UserUpdate {
  email?: string;
  name?: string;
  role?: UserRole;
  department_id?: number | null;
  teacher_id?: number | null;
  is_active?: boolean;
  password?: string;
}

export interface UserSelfUpdate {
  name?: string;
  password?: string;
}

// ---- Departments / Programs / Sections ----

export interface DepartmentOut {
  id: number;
  name: string;
  code: string;
}
export type DepartmentCreate = Omit<DepartmentOut, "id">;
export type DepartmentUpdate = Partial<DepartmentCreate>;

export interface ProgramOut {
  id: number;
  department_id: number;
  name: string;
  code: string;
  duration_semesters: number;
  time_structure_id: number | null;
}
export type ProgramCreate = Omit<ProgramOut, "id">;
export type ProgramUpdate = Partial<ProgramCreate>;

export interface SectionOut {
  id: number;
  program_id: number;
  semester_number: number;
  name: string;
  strength: number;
  time_structure_id: number | null;
  max_periods_per_day: number | null;
  max_consecutive_periods: number | null;
}
export type SectionCreate = Omit<SectionOut, "id">;
export type SectionUpdate = Partial<SectionCreate>;

export interface LabBatchOut {
  id: number;
  section_id: number;
  name: string;
  strength: number;
}
export interface LabBatchNestedCreate {
  name: string;
  strength: number;
}
export type LabBatchUpdate = Partial<LabBatchNestedCreate> & { section_id?: number };

// ---- Rooms ----

export interface RoomOut {
  id: number;
  code: string;
  name: string;
  room_type: RoomType;
  capacity: number;
  lab_category: string | null;
  equipment_tags: string[] | null;
  building: string | null;
  floor: number | null;
}
export type RoomCreate = Omit<RoomOut, "id">;
export type RoomUpdate = Partial<RoomCreate>;

export interface RoomUnavailabilityOut {
  id: number;
  room_id: number;
  day_index: number;
  period_index: number | null;
}
export interface RoomUnavailabilityNestedCreate {
  day_index: number;
  period_index?: number | null;
}

// ---- Subjects ----

export interface SubjectOut {
  id: number;
  code: string;
  name: string;
  department_id: number;
  subject_type: SubjectType;
  credits: number;
  periods_per_week: number;
  sessions_per_week: number;
  block_size: number;
  spread_across_days: boolean;
  max_per_day: number;
  requires_lab_batches: boolean;
  avoid_last_period: boolean;
  prefer_afternoon: boolean;
}
export type SubjectCreate = Omit<SubjectOut, "id">;
export type SubjectUpdate = Partial<SubjectCreate>;

// ---- Teachers ----

export interface TeacherOut {
  id: number;
  code: string;
  name: string;
  department_id: number;
  email: string | null;
  phone: string | null;
  max_periods_per_day: number;
  max_periods_per_week: number;
  max_consecutive_periods: number;
  is_visiting: boolean;
  visiting_days: number[] | null;
}
export type TeacherCreate = Omit<TeacherOut, "id">;
export type TeacherUpdate = Partial<TeacherCreate>;

export interface TeacherSubjectOut {
  id: number;
  teacher_id: number;
  subject_id: number;
}
export interface TeacherSubjectNestedCreate {
  subject_id: number;
}

export interface TeacherUnavailabilityOut {
  id: number;
  teacher_id: number;
  day_index: number;
  period_index: number | null;
}
export interface TeacherUnavailabilityNestedCreate {
  day_index: number;
  period_index?: number | null;
}

export interface TeacherPreferenceOut {
  id: number;
  teacher_id: number;
  preference_type: PreferenceType;
  day_index: number | null;
  weight: number;
}
export interface TeacherPreferenceNestedCreate {
  preference_type: PreferenceType;
  day_index?: number | null;
  weight?: number;
}
export type TeacherPreferenceUpdate = Partial<TeacherPreferenceNestedCreate>;

// ---- Time structures ----

export interface WorkingDayOut {
  id: number;
  time_structure_id: number;
  day_index: number;
  name: string;
  max_period_index: number | null;
}
export interface WorkingDayNestedCreate {
  day_index: number;
  name: string;
  max_period_index?: number | null;
}
export type WorkingDayUpdate = Partial<WorkingDayNestedCreate>;

export interface PeriodSlotOut {
  id: number;
  time_structure_id: number;
  period_index: number;
  label: string;
  start_time: string;
  end_time: string;
  kind: PeriodKind;
  teaching_order: number | null;
}
export interface PeriodSlotNestedCreate {
  period_index: number;
  label: string;
  start_time: string;
  end_time: string;
  kind: PeriodKind;
  teaching_order?: number | null;
}
export type PeriodSlotUpdate = Partial<PeriodSlotNestedCreate>;

export interface TimeStructureOut {
  id: number;
  name: string;
  is_default: boolean;
  days: WorkingDayOut[];
  periods: PeriodSlotOut[];
}
export interface TimeStructureCreate {
  name: string;
  is_default?: boolean;
  days: WorkingDayNestedCreate[];
  periods: PeriodSlotNestedCreate[];
}
export interface TimeStructureUpdate {
  name?: string;
  is_default?: boolean;
}

// ---- Allocations ----

export interface AllocationOut {
  id: number;
  subject_id: number;
  section_id: number;
  lab_batch_id: number | null;
  teacher_id: number | null;
  is_fixed_teacher: boolean;
  room_id: number | null;
  is_fixed_room: boolean;
}
export type AllocationCreate = Omit<AllocationOut, "id">;
export type AllocationUpdate = Partial<AllocationCreate>;

// ---- Electives ----

export interface ElectiveBasketOut {
  id: number;
  name: string;
  sessions_per_week: number;
  block_size: number;
}
export type ElectiveBasketCreate = Omit<ElectiveBasketOut, "id">;
export type ElectiveBasketUpdate = Partial<ElectiveBasketCreate>;

export interface ElectiveOptionOut {
  id: number;
  basket_id: number;
  subject_id: number;
  teacher_id: number | null;
  room_type_required: RoomType;
  expected_strength: number;
}
export interface ElectiveOptionNestedCreate {
  subject_id: number;
  teacher_id?: number | null;
  room_type_required?: RoomType;
  expected_strength?: number;
}
export type ElectiveOptionUpdate = Partial<ElectiveOptionNestedCreate>;

export interface ElectiveParticipationOut {
  id: number;
  basket_id: number;
  section_id: number;
}
export interface ElectiveParticipationNestedCreate {
  section_id: number;
}

// ---- Combined classes ----

export interface CombinedClassOut {
  id: number;
  name: string;
  subject_id: number;
  teacher_id: number | null;
  sessions_per_week: number;
  block_size: number;
  room_type_required: RoomType;
}
export type CombinedClassCreate = Omit<CombinedClassOut, "id">;
export type CombinedClassUpdate = Partial<CombinedClassCreate>;

export interface CombinedClassSectionOut {
  id: number;
  combined_class_id: number;
  section_id: number;
}
export interface CombinedClassSectionNestedCreate {
  section_id: number;
}

// ---- Weight profiles ----

export interface WeightProfileOut {
  id: number;
  name: string;
  is_preset: boolean;
  weights: Record<string, number>;
}
export type WeightProfileCreate = Omit<WeightProfileOut, "id">;
export type WeightProfileUpdate = Partial<WeightProfileCreate>;

// Keep in sync with backend/app/models/weight.py DEFAULT_WEIGHTS keys.
export const WEIGHT_CATEGORIES: { key: string; label: string; group: string }[] = [
  { key: "section_gaps", label: "Section gaps", group: "Section comfort" },
  { key: "section_daily_balance", label: "Section daily balance", group: "Section comfort" },
  { key: "same_subject_twice_a_day", label: "Same subject twice a day", group: "Section comfort" },
  { key: "heavy_subject_last_period", label: "Heavy subject in last period", group: "Section comfort" },
  { key: "lab_afternoon_preference", label: "Lab afternoon preference", group: "Section comfort" },
  { key: "teacher_gaps", label: "Teacher gaps", group: "Teacher comfort" },
  { key: "teacher_workload_balance", label: "Teacher workload balance", group: "Teacher comfort" },
  { key: "teacher_preferred_day", label: "Teacher preferred day", group: "Teacher comfort" },
  { key: "teacher_free_day", label: "Teacher free day", group: "Teacher comfort" },
  { key: "teacher_no_first_period", label: "Teacher: no first period", group: "Teacher comfort" },
  { key: "teacher_no_last_period", label: "Teacher: no last period", group: "Teacher comfort" },
  { key: "teacher_avoid_back_to_back", label: "Teacher: avoid back-to-back", group: "Teacher comfort" },
  { key: "stability", label: "Stability (minimize re-shuffling)", group: "Other" },
];

export interface ApiErrorDetail {
  type: string;
  loc: (string | number)[];
  msg: string;
  input?: unknown;
}
