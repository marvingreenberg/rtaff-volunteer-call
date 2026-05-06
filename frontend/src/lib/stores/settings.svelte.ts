export type Density = "large" | "standard" | "compact";
export type Theme = "light" | "dark";
export type ListView = "pill" | "table";

const DENSITY_KEY = "vcall_density";
const THEME_KEY = "vcall_theme";
const LIST_VIEW_KEY = "vcall_list_view";
const VALID_DENSITIES: readonly string[] = ["large", "standard", "compact"];
const VALID_THEMES: readonly string[] = ["light", "dark"];
const VALID_LIST_VIEWS: readonly string[] = ["pill", "table"];

let _density = $state<Density>("standard");
let _theme = $state<Theme>("light");
let _listView = $state<ListView>("pill");

export const settingsState = {
  get density() {
    return _density;
  },
  set density(v: Density) {
    _density = v;
  },
  get theme() {
    return _theme;
  },
  set theme(v: Theme) {
    _theme = v;
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
    document.documentElement.setAttribute("data-theme", _theme);
  }
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(DENSITY_KEY, _density);
    localStorage.setItem(THEME_KEY, _theme);
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
    const t = localStorage.getItem(THEME_KEY);
    if (t && VALID_THEMES.includes(t)) _theme = t as Theme;
    const lv = localStorage.getItem(LIST_VIEW_KEY);
    if (lv && VALID_LIST_VIEWS.includes(lv)) _listView = lv as ListView;
  }
  applySettings();
}
