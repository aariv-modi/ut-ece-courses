// Static JSON of all courses for the header search box (fetched on first focus).
import { courses, href, pill } from '../lib/courses';

export function GET() {
  const body = courses.map((c: any) => ({ code: c.code, title: c.title, url: href(c), status: pill(c).cls }));
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } });
}
