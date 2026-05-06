/**
 * Reusable fetchOptions factories for AutocompleteInput.
 */

import { people } from "$lib/api/client";

export interface AutocompleteItem {
  value: string;
  label: string;
  description?: string;
}

type FetchOptionsFn = (query: string) => Promise<AutocompleteItem[]>;

function withErrorFallback(fn: FetchOptionsFn): FetchOptionsFn {
  return async (query: string) => {
    try {
      return await fn(query);
    } catch {
      return [];
    }
  };
}

export function searchPeople(filters?: {
  role?: string;
  active?: boolean;
  descriptionField?: "skill_category" | "roles";
}): FetchOptionsFn {
  const {
    role,
    active = true,
    descriptionField = "skill_category",
  } = filters || {};
  return withErrorFallback(async (query: string) => {
    const results = await people.list({ role, active, search: query });
    return results.map((p) => ({
      value: p.id,
      label: `${p.first_name} ${p.last_name}`,
      description:
        descriptionField === "roles" ? p.roles.join(", ") : p.skill_category,
    }));
  });
}
