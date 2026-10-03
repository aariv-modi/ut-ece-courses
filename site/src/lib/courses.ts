// Shared course helpers used by the layouts and pages.
import data from '../data/dataset.json';

export const generated: string = data.generated;
export const base = import.meta.env.BASE_URL;

// UT numbering: first digit = credit hours; last two digits = level (01-19 lower division, 20-79 upper division).
const key = (n: string) => ({ lvl: parseInt(n.slice(1, 3)), suf: n.slice(3), hrs: n[0] });
export const courses: any[] = Object.values(data.courses).sort((a: any, b: any) => {
  const x = key(a.number), y = key(b.number);
  return x.lvl - y.lvl || x.suf.localeCompare(y.suf) || x.hrs.localeCompare(y.hrs);
});

export const baseNum = (c: any): string => c.base_number || c.number;
export const href = (c: any) => `${base}course/${c.number.toLowerCase()}/`;

export const isHonors = (c: any) => baseNum(c).endsWith('H');
export const division = (c: any): 'lower' | 'upper' => (parseInt(baseNum(c).slice(1, 3)) < 20 ? 'lower' : 'upper');
export const DIV_LABEL: Record<string, string> = { lower: 'Lower-division courses', upper: 'Upper-division courses' };

// "Fall 2025" -> "Fall '25"
export const short = (t: string) => t.replace(/^(Fall|Spring) 20(\d\d)$/, "$1 '$2");
export const offeredList = (c: any): string[] => [...c.terms_offered, ...(c.offered_next ? ['Spring 2027'] : [])];

// Eight-semester window = Fall 2023 .. Spring 2027. Courses not taught in the last four are split by whether they
// appeared in the four before that (recent) or are older / have no record (retired).
const ord = (t: string) => { const m = t.match(/^(Fall|Spring) (\d{4})$/)!; return +m[2] * 2 + (m[1] === 'Fall' ? 1 : 0); };
const CUTOFF = ord('Fall 2023');
export const tier = (c: any): 'active' | 'recent' | 'retired' =>
  c.status === 'active' ? 'active'
  : c.last_offered_earlier && ord(c.last_offered_earlier) >= CUTOFF ? 'recent' : 'retired';

// green = scheduled Spring 2027; yellow = taught in the window; red = not taught in the window ("Last offered")
export const pill = (c: any) => {
  const terms = offeredList(c);
  if (terms.length) return { cls: c.offered_next ? 'ok' : 'yellow', label: 'Offered', text: terms.map(short).join(', ') };
  const text = c.last_offered_earlier ? short(c.last_offered_earlier)
    : 'no Fall or Spring offering found since Spring 2010';
  return { cls: 'red', label: 'Last offered', text };
};

export const stats = {
  courses: courses.length,
  next: courses.filter((c) => c.offered_next).length,
  active: courses.filter((c) => c.status === 'active').length,
  recent: courses.filter((c) => tier(c) === 'recent').length,
  retired: courses.filter((c) => tier(c) === 'retired').length,
  syllabi: courses.reduce((n, c) => n + c.instructors.filter((e: any) => e.topics && e.topics.length).length, 0),
  topics: courses.reduce((n, c) => n + c.instructors.reduce((m: number, e: any) => m + (e.topics ? e.topics.length : 0), 0), 0),
};
