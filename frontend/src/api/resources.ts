/** Thin typed wrappers around each backend resource's REST endpoints. */
import { api } from "./client";
import type {
  AllocationCreate,
  AllocationOut,
  AllocationUpdate,
  CombinedClassCreate,
  CombinedClassOut,
  CombinedClassSectionNestedCreate,
  CombinedClassSectionOut,
  CombinedClassUpdate,
  DepartmentCreate,
  DepartmentOut,
  DepartmentUpdate,
  ElectiveBasketCreate,
  ElectiveBasketOut,
  ElectiveBasketUpdate,
  ElectiveOptionNestedCreate,
  ElectiveOptionOut,
  ElectiveOptionUpdate,
  ElectiveParticipationNestedCreate,
  ElectiveParticipationOut,
  LabBatchNestedCreate,
  LabBatchOut,
  LabBatchUpdate,
  PeriodSlotNestedCreate,
  PeriodSlotOut,
  PeriodSlotUpdate,
  ProgramCreate,
  ProgramOut,
  ProgramUpdate,
  RoomCreate,
  RoomOut,
  RoomUnavailabilityNestedCreate,
  RoomUnavailabilityOut,
  RoomUpdate,
  SectionCreate,
  SectionOut,
  SectionUpdate,
  SubjectCreate,
  SubjectOut,
  SubjectUpdate,
  TeacherCreate,
  TeacherOut,
  TeacherPreferenceNestedCreate,
  TeacherPreferenceOut,
  TeacherPreferenceUpdate,
  TeacherSubjectNestedCreate,
  TeacherSubjectOut,
  TeacherUnavailabilityNestedCreate,
  TeacherUnavailabilityOut,
  TeacherUpdate,
  TimeStructureCreate,
  TimeStructureOut,
  TimeStructureUpdate,
  UserCreate,
  UserOut,
  UserSelfUpdate,
  UserUpdate,
  WeightProfileCreate,
  WeightProfileOut,
  WeightProfileUpdate,
  WorkingDayNestedCreate,
  WorkingDayOut,
  WorkingDayUpdate,
} from "./types";

// ---- Departments ----
export const departmentsApi = {
  list: () => api.get<DepartmentOut[]>("/api/departments").then((r) => r.data),
  get: (id: number) => api.get<DepartmentOut>(`/api/departments/${id}`).then((r) => r.data),
  create: (data: DepartmentCreate) => api.post<DepartmentOut>("/api/departments", data).then((r) => r.data),
  update: (id: number, data: DepartmentUpdate) =>
    api.put<DepartmentOut>(`/api/departments/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/departments/${id}`).then(() => undefined),
};

// ---- Programs ----
export const programsApi = {
  list: (departmentId?: number) =>
    api
      .get<ProgramOut[]>("/api/programs", { params: departmentId ? { department_id: departmentId } : {} })
      .then((r) => r.data),
  create: (data: ProgramCreate) => api.post<ProgramOut>("/api/programs", data).then((r) => r.data),
  update: (id: number, data: ProgramUpdate) => api.put<ProgramOut>(`/api/programs/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/programs/${id}`).then(() => undefined),
};

// ---- Sections (+ lab batches) ----
export const sectionsApi = {
  list: (programId?: number) =>
    api
      .get<SectionOut[]>("/api/sections", { params: programId ? { program_id: programId } : {} })
      .then((r) => r.data),
  create: (data: SectionCreate) => api.post<SectionOut>("/api/sections", data).then((r) => r.data),
  update: (id: number, data: SectionUpdate) => api.put<SectionOut>(`/api/sections/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/sections/${id}`).then(() => undefined),

  listLabBatches: (sectionId: number) =>
    api.get<LabBatchOut[]>(`/api/sections/${sectionId}/lab-batches`).then((r) => r.data),
  createLabBatch: (sectionId: number, data: LabBatchNestedCreate) =>
    api.post<LabBatchOut>(`/api/sections/${sectionId}/lab-batches`, data).then((r) => r.data),
  updateLabBatch: (sectionId: number, batchId: number, data: LabBatchUpdate) =>
    api.put<LabBatchOut>(`/api/sections/${sectionId}/lab-batches/${batchId}`, data).then((r) => r.data),
  removeLabBatch: (sectionId: number, batchId: number) =>
    api.delete(`/api/sections/${sectionId}/lab-batches/${batchId}`).then(() => undefined),
};

export const labBatchesApi = {
  list: (sectionId?: number) =>
    api
      .get<LabBatchOut[]>("/api/lab-batches", { params: sectionId ? { section_id: sectionId } : {} })
      .then((r) => r.data),
};

// ---- Rooms (+ unavailability) ----
export const roomsApi = {
  list: () => api.get<RoomOut[]>("/api/rooms").then((r) => r.data),
  create: (data: RoomCreate) => api.post<RoomOut>("/api/rooms", data).then((r) => r.data),
  update: (id: number, data: RoomUpdate) => api.put<RoomOut>(`/api/rooms/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/rooms/${id}`).then(() => undefined),

  listUnavailability: (roomId: number) =>
    api.get<RoomUnavailabilityOut[]>(`/api/rooms/${roomId}/unavailability`).then((r) => r.data),
  addUnavailability: (roomId: number, data: RoomUnavailabilityNestedCreate) =>
    api.post<RoomUnavailabilityOut>(`/api/rooms/${roomId}/unavailability`, data).then((r) => r.data),
  removeUnavailability: (roomId: number, rowId: number) =>
    api.delete(`/api/rooms/${roomId}/unavailability/${rowId}`).then(() => undefined),
};

// ---- Subjects ----
export const subjectsApi = {
  list: (departmentId?: number) =>
    api
      .get<SubjectOut[]>("/api/subjects", { params: departmentId ? { department_id: departmentId } : {} })
      .then((r) => r.data),
  create: (data: SubjectCreate) => api.post<SubjectOut>("/api/subjects", data).then((r) => r.data),
  update: (id: number, data: SubjectUpdate) => api.put<SubjectOut>(`/api/subjects/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/subjects/${id}`).then(() => undefined),
};

// ---- Teachers (+ subjects, unavailability, preferences) ----
export const teachersApi = {
  list: (departmentId?: number) =>
    api
      .get<TeacherOut[]>("/api/teachers", { params: departmentId ? { department_id: departmentId } : {} })
      .then((r) => r.data),
  create: (data: TeacherCreate) => api.post<TeacherOut>("/api/teachers", data).then((r) => r.data),
  update: (id: number, data: TeacherUpdate) => api.put<TeacherOut>(`/api/teachers/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/teachers/${id}`).then(() => undefined),

  listSubjects: (teacherId: number) =>
    api.get<TeacherSubjectOut[]>(`/api/teachers/${teacherId}/subjects`).then((r) => r.data),
  addSubject: (teacherId: number, data: TeacherSubjectNestedCreate) =>
    api.post<TeacherSubjectOut>(`/api/teachers/${teacherId}/subjects`, data).then((r) => r.data),
  removeSubject: (teacherId: number, linkId: number) =>
    api.delete(`/api/teachers/${teacherId}/subjects/${linkId}`).then(() => undefined),

  listUnavailability: (teacherId: number) =>
    api.get<TeacherUnavailabilityOut[]>(`/api/teachers/${teacherId}/unavailability`).then((r) => r.data),
  addUnavailability: (teacherId: number, data: TeacherUnavailabilityNestedCreate) =>
    api.post<TeacherUnavailabilityOut>(`/api/teachers/${teacherId}/unavailability`, data).then((r) => r.data),
  removeUnavailability: (teacherId: number, rowId: number) =>
    api.delete(`/api/teachers/${teacherId}/unavailability/${rowId}`).then(() => undefined),

  listPreferences: (teacherId: number) =>
    api.get<TeacherPreferenceOut[]>(`/api/teachers/${teacherId}/preferences`).then((r) => r.data),
  addPreference: (teacherId: number, data: TeacherPreferenceNestedCreate) =>
    api.post<TeacherPreferenceOut>(`/api/teachers/${teacherId}/preferences`, data).then((r) => r.data),
  updatePreference: (teacherId: number, rowId: number, data: TeacherPreferenceUpdate) =>
    api.put<TeacherPreferenceOut>(`/api/teachers/${teacherId}/preferences/${rowId}`, data).then((r) => r.data),
  removePreference: (teacherId: number, rowId: number) =>
    api.delete(`/api/teachers/${teacherId}/preferences/${rowId}`).then(() => undefined),
};

// ---- Time structures (+ working days, period slots) ----
export const timeStructuresApi = {
  list: () => api.get<TimeStructureOut[]>("/api/time-structures").then((r) => r.data),
  get: (id: number) => api.get<TimeStructureOut>(`/api/time-structures/${id}`).then((r) => r.data),
  create: (data: TimeStructureCreate) =>
    api.post<TimeStructureOut>("/api/time-structures", data).then((r) => r.data),
  update: (id: number, data: TimeStructureUpdate) =>
    api.put<TimeStructureOut>(`/api/time-structures/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/time-structures/${id}`).then(() => undefined),

  addDay: (tsId: number, data: WorkingDayNestedCreate) =>
    api.post<WorkingDayOut>(`/api/time-structures/${tsId}/days`, data).then((r) => r.data),
  updateDay: (tsId: number, dayId: number, data: WorkingDayUpdate) =>
    api.put<WorkingDayOut>(`/api/time-structures/${tsId}/days/${dayId}`, data).then((r) => r.data),
  removeDay: (tsId: number, dayId: number) =>
    api.delete(`/api/time-structures/${tsId}/days/${dayId}`).then(() => undefined),

  addPeriod: (tsId: number, data: PeriodSlotNestedCreate) =>
    api.post<PeriodSlotOut>(`/api/time-structures/${tsId}/periods`, data).then((r) => r.data),
  updatePeriod: (tsId: number, periodId: number, data: PeriodSlotUpdate) =>
    api.put<PeriodSlotOut>(`/api/time-structures/${tsId}/periods/${periodId}`, data).then((r) => r.data),
  removePeriod: (tsId: number, periodId: number) =>
    api.delete(`/api/time-structures/${tsId}/periods/${periodId}`).then(() => undefined),
};

// ---- Allocations ----
export const allocationsApi = {
  list: (params?: { section_id?: number; subject_id?: number; teacher_id?: number }) =>
    api.get<AllocationOut[]>("/api/allocations", { params }).then((r) => r.data),
  create: (data: AllocationCreate) => api.post<AllocationOut>("/api/allocations", data).then((r) => r.data),
  update: (id: number, data: AllocationUpdate) =>
    api.put<AllocationOut>(`/api/allocations/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/allocations/${id}`).then(() => undefined),
};

// ---- Electives ----
export const electivesApi = {
  listBaskets: () => api.get<ElectiveBasketOut[]>("/api/electives/baskets").then((r) => r.data),
  createBasket: (data: ElectiveBasketCreate) =>
    api.post<ElectiveBasketOut>("/api/electives/baskets", data).then((r) => r.data),
  updateBasket: (id: number, data: ElectiveBasketUpdate) =>
    api.put<ElectiveBasketOut>(`/api/electives/baskets/${id}`, data).then((r) => r.data),
  removeBasket: (id: number) => api.delete(`/api/electives/baskets/${id}`).then(() => undefined),

  listOptions: (basketId: number) =>
    api.get<ElectiveOptionOut[]>(`/api/electives/baskets/${basketId}/options`).then((r) => r.data),
  createOption: (basketId: number, data: ElectiveOptionNestedCreate) =>
    api.post<ElectiveOptionOut>(`/api/electives/baskets/${basketId}/options`, data).then((r) => r.data),
  updateOption: (basketId: number, optionId: number, data: ElectiveOptionUpdate) =>
    api
      .put<ElectiveOptionOut>(`/api/electives/baskets/${basketId}/options/${optionId}`, data)
      .then((r) => r.data),
  removeOption: (basketId: number, optionId: number) =>
    api.delete(`/api/electives/baskets/${basketId}/options/${optionId}`).then(() => undefined),

  listParticipations: (basketId: number) =>
    api
      .get<ElectiveParticipationOut[]>(`/api/electives/baskets/${basketId}/participations`)
      .then((r) => r.data),
  createParticipation: (basketId: number, data: ElectiveParticipationNestedCreate) =>
    api
      .post<ElectiveParticipationOut>(`/api/electives/baskets/${basketId}/participations`, data)
      .then((r) => r.data),
  removeParticipation: (basketId: number, participationId: number) =>
    api.delete(`/api/electives/baskets/${basketId}/participations/${participationId}`).then(() => undefined),
};

// ---- Combined classes ----
export const combinedClassesApi = {
  list: () => api.get<CombinedClassOut[]>("/api/combined-classes").then((r) => r.data),
  create: (data: CombinedClassCreate) =>
    api.post<CombinedClassOut>("/api/combined-classes", data).then((r) => r.data),
  update: (id: number, data: CombinedClassUpdate) =>
    api.put<CombinedClassOut>(`/api/combined-classes/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/combined-classes/${id}`).then(() => undefined),

  listSections: (combinedClassId: number) =>
    api
      .get<CombinedClassSectionOut[]>(`/api/combined-classes/${combinedClassId}/sections`)
      .then((r) => r.data),
  addSection: (combinedClassId: number, data: CombinedClassSectionNestedCreate) =>
    api
      .post<CombinedClassSectionOut>(`/api/combined-classes/${combinedClassId}/sections`, data)
      .then((r) => r.data),
  removeSection: (combinedClassId: number, linkId: number) =>
    api.delete(`/api/combined-classes/${combinedClassId}/sections/${linkId}`).then(() => undefined),
};

// ---- Weight profiles ----
export const weightProfilesApi = {
  list: () => api.get<WeightProfileOut[]>("/api/weight-profiles").then((r) => r.data),
  create: (data: WeightProfileCreate) =>
    api.post<WeightProfileOut>("/api/weight-profiles", data).then((r) => r.data),
  update: (id: number, data: WeightProfileUpdate) =>
    api.put<WeightProfileOut>(`/api/weight-profiles/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/weight-profiles/${id}`).then(() => undefined),
};

// ---- Users ----
export const usersApi = {
  list: () => api.get<UserOut[]>("/api/users").then((r) => r.data),
  create: (data: UserCreate) => api.post<UserOut>("/api/users", data).then((r) => r.data),
  update: (id: number, data: UserUpdate) => api.put<UserOut>(`/api/users/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/users/${id}`).then(() => undefined),
  me: () => api.get<UserOut>("/api/users/me").then((r) => r.data),
  updateMe: (data: UserSelfUpdate) => api.put<UserOut>("/api/users/me", data).then((r) => r.data),
};
