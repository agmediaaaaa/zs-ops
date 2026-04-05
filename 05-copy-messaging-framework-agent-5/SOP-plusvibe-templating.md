# SOP: PlusVibe — Liquid, Spintax & Day Variables

Use this when sequences or copy will run in **PlusVibe** (Liquid + spintax + day/date helpers). Official references:

- [Liquid syntax guide](https://help.plusvibe.ai/en/articles/10748974-liquid-syntax-guide-for-plusvibe)
- [Spintax guide](https://help.plusvibe.ai/en/articles/8606174-spintax-guide)
- [Day variables guide](https://help.plusvibe.ai/en/articles/9735657-day-variables-guide)

Always use **Preview Email** and **Test Email** before sending live campaigns. Formatting mistakes break output or professionalism.

---

## Variables: plain text vs Liquid blocks

| Context | How to write |
|--------|----------------|
| Normal email body text | Double curly braces: `{{first_name}}`, `{{company_name}}` |
| Inside Liquid (`{% %}`) | Variable name only, no braces: `first_name`, `company_name` |

Example: lead field `{{job_responsibility}}` → inside Liquid use `job_responsibility`.

---

## Liquid — conditionals

Standard `if` / `elsif` / `else` / `endif`:

```liquid
{% if first_name != blank %}
Nice to meet you, {{first_name}}!
{% elsif company_name != blank %}
Hello there, someone from {{company_name}}!
{% else %}
Welcome!
{% endif %}
```

Date math for “day of week” style logic (Monday–Sunday):

```liquid
{% assign today_number = 'now' | date: '%u' | plus: 0 %}
{% if today_number < 4 %}
Hope you're having a good start to the week.
{% else %}
Hope you're having a good week.
{% endif %}
```

Hour-of-day logic uses `'now' | date: '%H' | plus: 0` similarly. Use logical operators (`and`, `or`, `contains`) per the platform guide.

**Note:** The literal `'now'` in Liquid filters is required by the engine. That does not override human-facing copy rules elsewhere; it only appears inside `{% %}` blocks.

---

## Spintax — random options

**Syntax:** open with `{{random|` then pipe-separated options, close with `}}`.

- `random` is **not** case-sensitive (`{{RANDOM|...}}` works).
- **Whitespace inside options is preserved** (watch accidental leading/trailing spaces).
- **Only one `{{variable}}` per spintax section.** More than one variable in a single section errors.

**Good:** `{{random|Hello {{first_name}}|Hi there}}`

**Bad:** `{{random|Hello {{first_name}} {{last_name}}|Hi there}}` (two variables in one section)

**Empty option:** use `||` so a segment may render blank, e.g. `{{random||Hello}}`.

---

## Spintax — fallback when a field is empty

**Syntax:** `{{fallback|{{field}}|default text}}`

Example: `{{fallback|{{first_name}}|Sir}}`

`fallback` is not case-sensitive. Whitespace in fallback text is preserved.

---

## Day and time variables (`pipl_*` helpers)

**Time of day** (uses campaign timezone):

- `{{pipl_time_of_day}}` → expands to morning / afternoon / evening  
  - Morning: before 12:00  
  - Afternoon: 12:00–15:00  
  - Evening: after 15:00  

Example: `Good {{pipl_time_of_day}}`

**Day of week:**

- `{{pipl_day_of_week}}` → e.g. Monday, Tuesday (for “Happy {{pipl_day_of_week}}” style copy).

**Relative dates** (`pipl_date`):

- `{{pipl_date "2 days from now" "MMMM Do YYYY"}}` → formatted date string  
- Shorthand examples from docs: `2days`, `2days ago`, `2weeks`, `2months`, `2year` with optional format string.

**Skip weekends** when adding days: use `now_wd` (weekday), e.g.  
`{{pipl_date "now_wd 2Days" "Do MMM"}}`

**Locales** (de, es, it, fr): add language code, e.g.  
`{{pipl_date "now_wd 2Days" "dddd, Do MMMM YYYY" "fr"}}`  
`{{pipl_day_of_week "de"}}`

Formatting tokens follow **Moment.js** conventions; match format strings to what you need in the final line.

---

## Cross-check with spam guard

Spintax options still produce **visible** words. Run finished variants through `SOP-spam-guard.md` (banned tokens, hype, phishing-shaped lines). Do not use spintax to sneak banned wording past filters.
