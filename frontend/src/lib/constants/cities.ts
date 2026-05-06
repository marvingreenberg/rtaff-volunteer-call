export const CITIES = [
  "Alexandria",
  "Annandale",
  "Arlington",
  "Burke",
  "Centreville",
  "Chantilly",
  "Clifton",
  "Fairfax",
  "Falls Church",
  "Great Falls",
  "Herndon",
  "McLean",
  "Oakton",
  "Reston",
  "Springfield",
  "Tysons",
  "Vienna",
];

export function matchCities(query: string): string[] {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return CITIES.filter((c) => c.toLowerCase().includes(q));
}
