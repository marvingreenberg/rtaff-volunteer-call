import { describe, it, expect } from "vitest";
import {
  projectStatusBadgeClass,
  projectStatusBorderColor,
  callStatusBadgeClass,
  skillBadgeClass,
  roleLabel,
} from "./badges";

describe("projectStatusBadgeClass", () => {
  it("maps known statuses", () => {
    expect(projectStatusBadgeClass("intake")).toBe("badge-intake");
    expect(projectStatusBadgeClass("completed")).toBe("badge-completed");
    expect(projectStatusBadgeClass("in_progress")).toBe("badge-progress");
  });

  it("returns default for unknown status", () => {
    expect(projectStatusBadgeClass("unknown")).toBe("badge-default");
  });
});

describe("projectStatusBorderColor", () => {
  it("maps known statuses to CSS variables", () => {
    expect(projectStatusBorderColor("assessment")).toBe("var(--rt-blue)");
    expect(projectStatusBorderColor("planning")).toBe("var(--rt-orange)");
  });

  it("returns gray for unknown status", () => {
    expect(projectStatusBorderColor("unknown")).toBe("var(--rt-gray-300)");
  });
});

describe("callStatusBadgeClass", () => {
  it("maps call statuses to reused badge palette classes", () => {
    // Each lifecycle step reuses an existing palette color rather than
    // minting a new one — open=gray (draft-shade), waiting=blue
    // (info-shade), assigned=green (full-shade), archived=red
    // (cancelled-shade). Pin the exact mapping so a future palette
    // refactor doesn't silently re-color a step.
    expect(callStatusBadgeClass("open")).toBe("badge-draft");
    expect(callStatusBadgeClass("waiting")).toBe("badge-open");
    expect(callStatusBadgeClass("assigned")).toBe("badge-full");
    expect(callStatusBadgeClass("archived")).toBe("badge-cancelled");
  });

  it("returns default for unknown", () => {
    expect(callStatusBadgeClass("unknown")).toBe("badge-default");
  });
});

describe("skillBadgeClass", () => {
  it("returns badge-skilled for each known skill tag", () => {
    expect(skillBadgeClass("plumbing")).toBe("badge-skilled");
    expect(skillBadgeClass("electrical")).toBe("badge-skilled");
    expect(skillBadgeClass("carpentry")).toBe("badge-skilled");
    expect(skillBadgeClass("hvac")).toBe("badge-skilled");
  });

  it("returns badge-default for unrecognized values", () => {
    expect(skillBadgeClass("other")).toBe("badge-default");
    expect(skillBadgeClass("")).toBe("badge-default");
  });
});

describe("roleLabel", () => {
  it("returns human-readable labels for known roles", () => {
    expect(roleLabel("staff")).toBe("Staff");
    expect(roleLabel("team_leader")).toBe("Team Leader");
    expect(roleLabel("volunteer")).toBe("Volunteer");
  });

  it("returns the raw role string for unknown roles", () => {
    expect(roleLabel("admin")).toBe("admin");
    expect(roleLabel("")).toBe("");
  });
});
