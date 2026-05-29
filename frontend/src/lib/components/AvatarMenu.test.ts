import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";

vi.mock("$lib/api/client", () => ({
  notifications: {
    unreadCount: vi.fn().mockResolvedValue({ count: 0 }),
  },
}));

import AvatarMenu from "./AvatarMenu.svelte";
import { settingsState } from "$lib/stores/settings.svelte";
import type { PersonResponse } from "$lib/api/types";

const user: PersonResponse = {
  id: "p1",
  first_name: "Vera",
  last_name: "Volunteer",
  email: "vera@example.com",
  phone: null,
  phone_verified: false,
  skills: [],
  active: true,
  notification_preference: "email",
  notification_detail_level: "summary",
  subscription_status: "active",
  pause_start: null,
  pause_end: null,
  notes: null,
  roles: [],
  programs: [],
  calendars: [],
  calendar_kind: "google",
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
} as unknown as PersonResponse;

describe("AvatarMenu density picker", () => {
  beforeEach(() => {
    settingsState.density = "standard";
    document.documentElement.removeAttribute("data-density");
  });

  it("clicking Large updates the density store and DOM attribute", async () => {
    const { getByRole, getByLabelText } = render(AvatarMenu, {
      props: { user, onlogout: () => {} },
    });
    // Open the menu first
    await fireEvent.click(getByLabelText("User menu"));
    const largeBtn = getByRole("radio", { name: /large/i });
    await fireEvent.click(largeBtn);
    expect(settingsState.density).toBe("large");
    expect(document.documentElement.getAttribute("data-density")).toBe("large");
  });
});
