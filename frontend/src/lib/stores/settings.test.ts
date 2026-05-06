import { describe, it, expect, beforeEach } from "vitest";
import { settingsState, applySettings, loadSettings } from "./settings.svelte";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-density");
  document.documentElement.removeAttribute("data-theme");
  settingsState.density = "standard";
  settingsState.theme = "light";
  settingsState.listView = "pill";
});

describe("settingsState", () => {
  it("has standard/light/pill defaults", () => {
    expect(settingsState.density).toBe("standard");
    expect(settingsState.theme).toBe("light");
    expect(settingsState.listView).toBe("pill");
  });
});

describe("applySettings", () => {
  it("sets data-density attribute on html element", () => {
    settingsState.density = "large";
    applySettings();
    expect(document.documentElement.getAttribute("data-density")).toBe("large");
  });

  it("sets data-theme attribute on html element", () => {
    settingsState.theme = "dark";
    applySettings();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("persists density to localStorage", () => {
    settingsState.density = "compact";
    applySettings();
    expect(localStorage.getItem("vcall_density")).toBe("compact");
  });

  it("persists theme to localStorage", () => {
    settingsState.theme = "dark";
    applySettings();
    expect(localStorage.getItem("vcall_theme")).toBe("dark");
  });

  it("persists listView to localStorage", () => {
    settingsState.listView = "table";
    applySettings();
    expect(localStorage.getItem("vcall_list_view")).toBe("table");
  });
});

describe("loadSettings", () => {
  it("reads density from localStorage", () => {
    localStorage.setItem("vcall_density", "large");
    loadSettings();
    expect(settingsState.density).toBe("large");
  });

  it("reads theme from localStorage", () => {
    localStorage.setItem("vcall_theme", "dark");
    loadSettings();
    expect(settingsState.theme).toBe("dark");
  });

  it("ignores invalid density localStorage values", () => {
    localStorage.setItem("vcall_density", "huge");
    loadSettings();
    expect(settingsState.density).toBe("standard");
  });

  it("ignores invalid theme localStorage values", () => {
    localStorage.setItem("vcall_theme", "neon");
    loadSettings();
    expect(settingsState.theme).toBe("light");
  });

  it("reads listView from localStorage", () => {
    localStorage.setItem("vcall_list_view", "table");
    loadSettings();
    expect(settingsState.listView).toBe("table");
  });

  it("ignores invalid listView localStorage values", () => {
    localStorage.setItem("vcall_list_view", "grid");
    loadSettings();
    expect(settingsState.listView).toBe("pill");
  });

  it("applies settings to DOM after loading", () => {
    localStorage.setItem("vcall_density", "compact");
    localStorage.setItem("vcall_theme", "dark");
    loadSettings();
    expect(document.documentElement.getAttribute("data-density")).toBe(
      "compact",
    );
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
