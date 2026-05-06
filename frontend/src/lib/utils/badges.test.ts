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
  it("maps call statuses", () => {
    expect(callStatusBadgeClass("draft")).toBe("badge-draft");
    expect(callStatusBadgeClass("open")).toBe("badge-open");
    expect(callStatusBadgeClass("closed")).toBe("badge-closed");
  });

  it("returns default for unknown", () => {
    expect(callStatusBadgeClass("unknown")).toBe("badge-default");
  });
});

describe("skillBadgeClass", () => {
  it("returns badge-skilled for skilled", () => {
    expect(skillBadgeClass("skilled")).toBe("badge-skilled");
  });

  it("returns badge-unskilled for unskilled", () => {
    expect(skillBadgeClass("unskilled")).toBe("badge-unskilled");
  });

  it("returns badge-unknown for unrecognized values", () => {
    expect(skillBadgeClass("other")).toBe("badge-unknown");
    expect(skillBadgeClass("")).toBe("badge-unknown");
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
