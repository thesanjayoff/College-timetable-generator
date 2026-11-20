import type { UserRole } from "../../api/types";

export interface NavItem {
  to: string;
  label: string;
  abbr: string;
  /** Roles allowed to see this item. Omitted = everyone (any authenticated role). */
  roles?: UserRole[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [{ to: "/", label: "Dashboard", abbr: "DB" }],
  },
  {
    label: "Master Data",
    items: [
      { to: "/departments", label: "Departments", abbr: "DP" },
      { to: "/programs", label: "Programs", abbr: "PR" },
      { to: "/sections", label: "Sections", abbr: "SC" },
      { to: "/rooms", label: "Rooms", abbr: "RM" },
      { to: "/subjects", label: "Subjects", abbr: "SJ" },
      { to: "/teachers", label: "Teachers", abbr: "TC" },
      { to: "/time-structures", label: "Time Structures", abbr: "TS" },
      { to: "/allocations", label: "Allocations", abbr: "AL" },
      { to: "/electives", label: "Electives", abbr: "EL" },
      { to: "/combined-classes", label: "Combined Classes", abbr: "CC" },
      { to: "/weight-profiles", label: "Weight Profiles", abbr: "WP" },
    ],
  },
  {
    label: "Timetable Workspace",
    items: [
      { to: "/versions", label: "Versions", abbr: "VR" },
      { to: "/solve", label: "Solve", abbr: "SV" },
      { to: "/diagnostics", label: "Diagnostics", abbr: "DG" },
      { to: "/substitution", label: "Substitution Planner", abbr: "SB" },
      { to: "/import-export", label: "Import / Export", abbr: "IE" },
    ],
  },
  {
    label: "Administration",
    items: [{ to: "/users", label: "Users", abbr: "US", roles: ["admin"] }],
  },
];
