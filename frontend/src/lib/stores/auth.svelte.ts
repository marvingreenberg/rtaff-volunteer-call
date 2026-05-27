import { auth as authApi, type PersonResponse } from "$lib/api/client";

let _user = $state<PersonResponse | null>(null);
let _loading = $state(true);
let _error = $state<string | null>(null);
// Set when the user landed via a per-call invite link; consumed by the
// /volunteering page to deep-link to that call. Cleared after one read.
let _invitedCallId = $state<string | null>(null);

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
  get invitedCallId() {
    return _invitedCallId;
  },
};

/** Read and clear the invite-call deep-link target. */
export function consumeInvitedCallId(): string | null {
  const id = _invitedCallId;
  _invitedCallId = null;
  return id;
}

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
    const resp = await authApi.verify({ token });
    authState.user = resp.person;
    _invitedCallId = resp.invited_call_id;
    authState.loading = false;
    return resp.person;
  } catch (e) {
    authState.loading = false;
    const msg = e instanceof Error ? e.message : "Invalid or expired token";
    authState.error = msg;
    authState.user = null;
    throw new Error(msg);
  }
}

export async function logout() {
  authState.user = null;
  _invitedCallId = null;
  try {
    await authApi.logout();
  } catch {
    // Clearing the cookie is best-effort; the in-memory state is gone
    // regardless.
  }
}

export async function initFromToken(
  urlToken?: string | null,
): Promise<PersonResponse | null> {
  authState.loading = true;
  authState.error = null;

  try {
    const person = await authApi.me(urlToken ?? undefined);
    authState.user = person;
    authState.loading = false;
    return person;
  } catch {
    if (urlToken) {
      authState.error =
        "Invalid or expired link. Please contact the office for a new one.";
    }
    authState.user = null;
    authState.loading = false;
    return null;
  }
}
