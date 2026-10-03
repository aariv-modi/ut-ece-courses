# Topic list + coverage spec (pass 1)

You build, for ONE course (or a few small courses), (a) a strong list of DISTINCT topics the course teaches and (b) a
judgement of which instructor's most recent public syllabus covers which topic. The result is shown to students choosing
courses, so precision matters more than volume: a wrong check mark is worse than a missing one.

Input: `data/topic_in/<course>.json` (course key, title, official description/prerequisites, and for each instructor:
`name`, `syllabus_term`, `kind` (pdf|web), `text_file`, `pdf_file`, `url`, optional `toc_hints`). Read EVERY instructor's
`text_file` completely (use the Read tool; read in chunks if long). If a PDF's text is empty/garbled (< 1500 chars), read
the `pdf_file` itself instead. Web-format texts have policy/boilerplate sections omitted; content sections are verbatim.

Output: `data/topic_out/<course>.json` (UTF-8 JSON, written with the Write tool):
```json
{
  "course": "429",
  "topics": [
    {"label": "Cache memories and locality",
     "coverage": {
        "Morgan Fong": {"status": "stated", "evidence": "verbatim quote from THIS instructor's text, <= 40 words",
                        "where": "Topics section / Week 9", "as_written": "how this syllabus words the topic"},
        "Prashant Joshi": {"status": "textbook", "evidence": "Ch. 6 ...", "where": "...", "as_written": "...",
                           "toc_url": "https://... (the table of contents you actually fetched)"}
     }}
  ],
  "instructors": {
    "Morgan Fong": {"document_ok": true, "document_note": "", "detail_level": "weekly_schedule",
                    "textbooks": [{"title": "...", "authors": "...", "edition": "3rd", "isbn": null, "status": "required"}],
                    "external_schedule_url": null, "prerequisites_stated": "verbatim sentence or null",
                    "description_stated": "verbatim or null"}
  },
  "notes": "anything the reader should know (thin syllabi, odd documents, judgement calls)"
}
```
Allowed `status`: `stated` (the syllabus itself names/teaches the topic), `possible` (the syllabus hedges: "may include",
"time permitting", "optional", "tentative: ..."), `textbook` (covered only through assigned textbook chapters you resolved
against the book's real table of contents). `detail_level`: weekly_schedule | topic_list | chapters_only | minimal.

## How to decide topics (judgement, not keywords)
1. The topic list is the UNION over all instructors' syllabi: distinct, lecture-level concepts a student would recognise
   (2-8 words, e.g. "Dynamic programming", "Pipeline hazards and forwarding", "TCP congestion control"). Typical size
   10-70; fewer if the syllabi are thin. Do not pad.
2. One consistent granularity. If instructors differ in detail, use the finer label when at least one syllabus lists it
   separately, and credit another instructor ONLY if their text actually includes it (named in a list, schedule line,
   outcome, or module description). An umbrella phrase ("data structures", "ML basics") covers only the umbrella topic,
   never finer topics it does not name.
3. Merge synonyms/near-duplicates into one topic ("Caches" / "Cache memories"). Never merge related-but-different topics
   (Inheritance vs Polymorphism vs Encapsulation; Stack vs Queue; BFS vs DFS vs Dijkstra; a family vs one member).
4. Exclude: exams, reviews, grading, policies, deadlines, logistics, "course introduction", teamwork/presentation skills
   unless presented as taught content. Tools/languages are topics only if the course teaches them (e.g. Docker, Git, SQL).
   Do not infer topics from the catalog description or from your own idea of what such a course "usually" covers.
5. Judge coverage by reading and understanding the whole syllabus (schedule tables, topic lists, learning outcomes that
   name technical content, module descriptions, assignment descriptions that name technical content, assigned chapters).
   Count synonyms, abbreviations and enumerated sub-topics when they are really there. A passing mention in an unrelated
   context does not count. "Not listed" is the default; never write claims of "not taught".
6. Before leaving a topic blank for an instructor, search that instructor's text for the concept under other names; only
   then leave it blank. Conversely every check mark must be defensible from the quote you give.
7. EVIDENCE: every coverage entry has `evidence`, a verbatim excerpt (<= 40 words; " ... " may join two nearby pieces)
   from that instructor's own text file. Quotes are machine-checked against the text; invented or paraphrased quotes are
   rejected. Table text may be split across lines in the file: quote it as it reads.
8. Textbook chapters: when a syllabus only cites chapters ("Ch. 8"), resolve them with WebSearch/WebFetch against the
   book's real table of contents for the right edition (never from memory). Use `toc_hints` if provided. If the edition or
   book is ambiguous or no TOC is found, do not credit those chapters. `evidence` for status `textbook` = the syllabus
   reference text + the TOC chapter title, and `toc_url` is required.
9. Prerequisite/description/textbook/external-URL fields are copied from the syllabus, not invented. `external_schedule_url`
   is only a PUBLIC page named in the syllabus (instructor site, GitHub/GitLab...), never Canvas/instructure.
10. `document_ok`: false if the document is for a different course/instructor/term than expected (explain); if the
    instructor's name is simply not printed but course and term match, `document_ok` true with an explanatory note.
11. Variable-topic courses (e.g. a single C S 378 topic): the topic list is for that one subject.

## Mechanics (a previous run was corrupted by shared scripts: follow strictly)
- Work only on your assigned course keys. Write ONLY `data/topic_out/<course>.json`. Never modify any other file.
- Never use /tmp or any shared script path; helper scripts (if any) live in `data/topic_tmp/<your batch>/`.
- Do not use automated/fuzzy topic generation. You decide every topic and every check mark yourself.
- Validate before replying: run `python pipeline/15_topic_validate.py <course>` and fix everything it reports.
- Reply with ONE short line: courses done, validation result, and anything odd.

## ECE-specific notes
- Many ECE courses share a syllabus template across sections and instructors; still judge EACH instructor's own text. If two instructors' texts are identical, credit both identically.
- Syllabi that give only textbook chapter/section numbers ("Ch 4.1-4.2") name no topics themselves: resolve them against the real table of contents of the named book/edition (WebSearch/WebFetch) as `textbook` status with `toc_url`; if the book/edition is not named in that instructor's text, or you cannot fetch its real TOC, credit nothing from bare numbers. NEVER credit from memory of a book.
- Catalog-description phrases ("Explore ... transmission lines; and waveguides") count as `stated` only when that instructor's own syllabus text contains them; note "Catalog description repeated in syllabus" in `where`.
- Learning outcomes that name technical content (e.g. "Use the z-transform to analyze discrete-time signals") count as `stated` for that content.
- ABET student-outcome boilerplate, exam/quiz/homework lists, policies and software-install steps are never topics. Tools/languages/instruments (MATLAB, Python, oscilloscope, SPICE, Verilog) are topics only if the course teaches them as content.
- Variable-topic ECE 379K offerings: the topic list is for that one subject only.
