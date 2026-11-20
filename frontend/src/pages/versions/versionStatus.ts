import type { VersionStatus } from "../../api/types";

type BadgeTone = "slate" | "green" | "amber" | "rose" | "indigo";

export function statusTone(status: VersionStatus | string): BadgeTone {
  switch (status) {
    case "published":
      return "green";
    case "archived":
      return "slate";
    case "draft":
    default:
      return "amber";
  }
}

export function solveStatusTone(status: string | null): BadgeTone {
  switch (status) {
    case "optimal":
    case "feasible":
      return "green";
    case "running":
      return "indigo";
    case "infeasible":
    case "failed":
      return "rose";
    case "stopped":
      return "amber";
    default:
      return "slate";
  }
}
