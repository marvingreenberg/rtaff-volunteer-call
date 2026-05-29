import { describe, it, expect, beforeEach } from "vitest";
import {
  settingsState,
  applySettings,
  loadSettings,
  setDensity,
} from "./settings.svelte";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-density");
  document.documentElement.removeAttribute("data-theme");
  settingsState.density = "standard";
  settingsState.listView = "pill";
});

describe("settingsState", () => {
  it("has standard/pill defaults", () => {
    expect(settingsState.density).toBe("standard");
    expect(settingsState.listView).toBe("pill");
  });
});

describe("applySettings", () => {
  it("sets data-density attribute on html element", () => {
    settingsState.density = "large";
    applySettings();
    expect(document.documentElement.getAttribute("data-density")).toBe("large");
  });

  it("persists density to localStorage", () => {
    settingsState.density = "compact";
    applySettings();
    expect(localStorage.getItem("volunteer_call_density")).toBe("compact");
  });

  it("persists listView to localStorage", () => {
    settingsState.listView = "table";
    applySettings();
    expect(localStorage.getItem("volunteer_call_list_view")).toBe("table");
  });

  it("does not write a data-theme attribute (dark mode removed)", () => {
    // Catches a regression where the dark-mode toggle is reintroduced and
    // forgets to be opt-in — leaving everyone in dark mode by default.
    settingsState.density = "standard";
    applySettings();
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });
});

describe("setDensity", () => {
  it("setDensity mutates state and applies", () => {
    setDensity("large");
    expect(settingsState.density).toBe("large");
    expect(document.documentElement.getAttribute("data-density")).toBe("large");
  });
});

describe("loadSettings", () => {
  it("reads density from localStorage", () => {
    localStorage.setItem("volunteer_call_density", "large");
    loadSettings();
    expect(settingsState.density).toBe("large");
  });

  it("ignores invalid density localStorage values", () => {
    localStorage.setItem("volunteer_call_density", "huge");
    loadSettings();
    expect(settingsState.density).toBe("standard");
  });

  it("reads listView from localStorage", () => {
    localStorage.setItem("volunteer_call_list_view", "table");
    loadSettings();
    expect(settingsState.listView).toBe("table");
  });

  it("ignores invalid listView localStorage values", () => {
    localStorage.setItem("volunteer_call_list_view", "grid");
    loadSettings();
    expect(settingsState.listView).toBe("pill");
  });

  it("clears any pre-existing dark-theme persistence on load", () => {
    // Prior versions stored theme=dark in localStorage. After the dark-mode
    // removal, users coming back must not stay stuck in dark mode that no
    // longer has any matching CSS — they would see broken/un-themed colors.
    localStorage.setItem("volunteer_call_theme", "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    loadSettings();
    expect(localStorage.getItem("volunteer_call_theme")).toBeNull();
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("applies density to DOM after loading", () => {
    localStorage.setItem("volunteer_call_density", "compact");
    loadSettings();
    expect(document.documentElement.getAttribute("data-density")).toBe(
      "compact",
    );
  });
});
