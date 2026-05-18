/**
 * Volunteer-name display budget. The assignment UI shows each volunteer in
 * a fixed-width slot so that two columns of names line up cleanly even at
 * different density settings.
 *
 * Names ≤ VOLUNTEER_NAME_TRUNCATE_AT chars render unchanged; longer names
 * are clipped and a single-glyph ellipsis ("…") is appended. Total
 * displayed characters never exceed VOLUNTEER_NAME_DISPLAY_MAX.
 *
 * The CSS width cap lives in app.css as --volunteer-name-max-width and
 * uses ch units so it scales with the active density's font size. Keep
 * the two values in lockstep.
 */
export const VOLUNTEER_NAME_DISPLAY_MAX = 22;
export const VOLUNTEER_NAME_TRUNCATE_AT = 21;

const ELLIPSIS = "…";

export function truncateVolunteerName(name: string): string {
  if (name.length <= VOLUNTEER_NAME_TRUNCATE_AT) return name;
  return name.slice(0, VOLUNTEER_NAME_TRUNCATE_AT) + ELLIPSIS;
}
