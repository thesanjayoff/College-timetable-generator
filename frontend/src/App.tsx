import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { RouteGuard } from "./components/RouteGuard";
import { AppLayout } from "./components/layout/AppLayout";

import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ProfilePage from "./pages/ProfilePage";
import DepartmentsPage from "./pages/departments/DepartmentsPage";
import ProgramsPage from "./pages/programs/ProgramsPage";
import SectionsPage from "./pages/sections/SectionsPage";
import RoomsPage from "./pages/rooms/RoomsPage";
import SubjectsPage from "./pages/subjects/SubjectsPage";
import TeachersPage from "./pages/teachers/TeachersPage";
import TimeStructuresPage from "./pages/timeStructures/TimeStructuresPage";
import AllocationsPage from "./pages/allocations/AllocationsPage";
import ElectivesPage from "./pages/electives/ElectivesPage";
import CombinedClassesPage from "./pages/combinedClasses/CombinedClassesPage";
import WeightProfilesPage from "./pages/weightProfiles/WeightProfilesPage";
import UsersPage from "./pages/users/UsersPage";

import VersionsListPage from "./pages/versions/VersionsListPage";
import SolvePage from "./pages/solve/SolvePage";
import DiagnosticsPage from "./pages/diagnostics/DiagnosticsPage";
import SubstitutionPlannerPage from "./pages/substitution/SubstitutionPlannerPage";
import ImportExportPage from "./pages/importExport/ImportExportPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <RouteGuard>
                <AppLayout />
              </RouteGuard>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />

            <Route path="/departments" element={<DepartmentsPage />} />
            <Route path="/programs" element={<ProgramsPage />} />
            <Route path="/sections" element={<SectionsPage />} />
            <Route path="/rooms" element={<RoomsPage />} />
            <Route path="/subjects" element={<SubjectsPage />} />
            <Route path="/teachers" element={<TeachersPage />} />
            <Route path="/time-structures" element={<TimeStructuresPage />} />
            <Route path="/allocations" element={<AllocationsPage />} />
            <Route path="/electives" element={<ElectivesPage />} />
            <Route path="/combined-classes" element={<CombinedClassesPage />} />
            <Route path="/weight-profiles" element={<WeightProfilesPage />} />

            <Route path="/versions" element={<VersionsListPage />} />
            <Route path="/solve" element={<SolvePage />} />
            <Route path="/diagnostics" element={<DiagnosticsPage />} />
            <Route path="/substitution" element={<SubstitutionPlannerPage />} />
            <Route path="/import-export" element={<ImportExportPage />} />

            <Route
              path="/users"
              element={
                <RouteGuard roles={["admin"]}>
                  <UsersPage />
                </RouteGuard>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
