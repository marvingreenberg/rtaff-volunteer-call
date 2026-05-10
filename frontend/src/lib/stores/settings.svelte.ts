export type Density = "large" | "standard" | "compact";
export type ListView = "pill" | "table";

const DENSITY_KEY = "volunteer_call_density";
const LIST_VIEW_KEY = "volunteer_call_list_view";
const VALID_DENSITIES: readonly string[] = ["large", "standard", "compact"];
const VALID_LIST_VIEWS: readonly string[] = ["pill", "table"];

let _density = $state<Density>("standard");
let _listView = $state<ListView>("pill");

export const settingsState = {
  get density() {
    return _density;
  },
  set density(v: Density) {
    _density = v;
  },
  get listView() {
    return _listView;
  },
  set listView(v: ListView) {
    _listView = v;
  },
};

export function applySettings(): void {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-density", _density);
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(DENSITY_KEY, _density);
    localStorage.setItem(LIST_VIEW_KEY, _listView);
  }
}

export function setListView(v: ListView): void {
  settingsState.listView = v;
  applySettings();
}

export function loadSettings(): void {
  if (typeof localStorage !== "undefined") {
    const d = localStorage.getItem(DENSITY_KEY);
    if (d && VALID_DENSITIES.includes(d)) _density = d as Density;
    const lv = localStorage.getItem(LIST_VIEW_KEY);
    if (lv && VALID_LIST_VIEWS.includes(lv)) _listView = lv as ListView;
  }
  applySettings();
  // Clean up any prior dark-theme attribute / persisted value from before
  // dark mode was dropped — leaving them around would keep dark mode active
  // for users who previously enabled it.
  if (typeof document !== "undefined") {
    document.documentElement.removeAttribute("data-theme");
  }
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem("volunteer_call_theme");
  }
}
