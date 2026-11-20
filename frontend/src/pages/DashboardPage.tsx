import { useCallback } from "react";
import { Link } from "react-router-dom";
import { useFetch } from "../hooks/useFetch";
import {
  departmentsApi,
  programsApi,
  roomsApi,
  sectionsApi,
  subjectsApi,
  teachersApi,
} from "../api/resources";
import { Card, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAuth } from "../context/AuthContext";

interface CountCard {
  label: string;
  to: string;
  count: number;
}

export default function DashboardPage() {
  const { user } = useAuth();

  const fetcher = useCallback(async () => {
    const [departments, programs, sections, teachers, rooms, subjects] = await Promise.all([
      departmentsApi.list(),
      programsApi.list(),
      sectionsApi.list(),
      teachersApi.list(),
      roomsApi.list(),
      subjectsApi.list(),
    ]);
    return { departments, programs, sections, teachers, rooms, subjects };
  }, []);

  const { data, loading, error } = useFetch(fetcher, []);

  const cards: CountCard[] = data
    ? [
        { label: "Departments", to: "/departments", count: data.departments.length },
        { label: "Programs", to: "/programs", count: data.programs.length },
        { label: "Sections", to: "/sections", count: data.sections.length },
        { label: "Teachers", to: "/teachers", count: data.teachers.length },
        { label: "Rooms", to: "/rooms", count: data.rooms.length },
        { label: "Subjects", to: "/subjects", count: data.subjects.length },
      ]
    : [];

  return (
    <div>
      <PageHeader
        title={`Welcome${user ? `, ${user.name}` : ""}`}
        description="A quick look at the college's master data. Use the sidebar to manage each area."
      />

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {cards.map((c) => (
            <Link key={c.label} to={c.to}>
              <Card className="px-4 py-5 transition hover:border-indigo-300 hover:shadow-md">
                <p className="text-2xl font-semibold text-slate-900 dark:text-slate-50">{c.count}</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{c.label}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {!loading && !error && data && data.departments.length === 0 && (
        <div className="mt-8">
          <Card className="px-5 py-5">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Get started</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              No data yet. Start by creating a <Link to="/departments" className="font-medium text-indigo-600 dark:text-indigo-400">department</Link>,
              then add programs, sections, rooms, subjects and teachers before building allocations and a
              time structure.
            </p>
          </Card>
        </div>
      )}

    </div>
  );
}
