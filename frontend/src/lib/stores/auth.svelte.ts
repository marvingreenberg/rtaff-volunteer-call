import { auth as authApi, type PersonResponse } from "$lib/api/client";

const TOKEN_KEY = "vcall_token";

let _user = $state<PersonResponse | null>(null);
let _loading = $state(true);
let _error = $state<string | null>(null);

export const authState = {
  get user() {
    return _user;
  },
  set user(v: PersonResponse | null) {
    _user = v;
  },
  get loading() {
    return _loading;
  },
  set loading(v: boolean) {
    _loading = v;
  },
  get error() {
    return _error;
  },
  set error(v: string | null) {
    _error = v;
  },
};

export interface LoginResult {
  message: string;
  demoToken: string | null;
}

export async function login(email: string): Promise<LoginResult> {
  authState.loading = true;
  authState.error = null;
  try {
    const resp = await authApi.login({ email });
    authState.loading = false;
    return { message: resp.message, demoToken: resp.demo_token ?? null };
  } catch (e) {
    authState.loading = false;
    const msg = e instanceof Error ? e.message : "Failed to request login";
    authState.error = msg;
    throw new Error(msg);
  }
}

export async function verify(token: string): Promise<PersonResponse> {
  authState.loading = true;
  authState.error = null;
  try {
    const person = await authApi.verify({ token });
    authState.user = person;
    if (typeof localStorage !== "undefined")
      localStorage.setItem(TOKEN_KEY, token);
    authState.loading = false;
    return person;
  } catch (e) {
    authState.loading = false;
    const msg = e instanceof Error ? e.message : "Invalid or expired token";
    authState.error = msg;
    authState.user = null;
    if (typeof localStorage !== "undefined") localStorage.removeItem(TOKEN_KEY);
    throw new Error(msg);
  }
}

export function logout() {
  authState.user = null;
  if (typeof localStorage !== "undefined") localStorage.removeItem(TOKEN_KEY);
}

export async function initFromToken(
  urlToken?: string | null,
): Promise<PersonResponse | null> {
  const token =
    urlToken ||
    (typeof localStorage !== "undefined"
      ? localStorage.getItem(TOKEN_KEY)
      : null);
  if (!token) {
    authState.loading = false;
    return null;
  }

  authState.loading = true;
  authState.error = null;

  try {
    const person = await authApi.me(token);
    authState.user = person;
    if (typeof localStorage !== "undefined")
      localStorage.setItem(TOKEN_KEY, token);
    authState.loading = false;
    return person;
  } catch {
    authState.error =
      "Invalid or expired link. Please contact the office for a new one.";
    authState.user = null;
    if (typeof localStorage !== "undefined") localStorage.removeItem(TOKEN_KEY);
    authState.loading = false;
    return null;
  }
}
