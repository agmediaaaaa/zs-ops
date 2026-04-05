# SOP: Cold-Email Copy — Spam & Deliverability Guard

Always-on spam and deliverability guardrails for every generated output.

Use these rules to decide what to avoid, how to rewrite risky wording, and when to treat a word or phrase as unsafe.

---

## When these rules apply

- Apply them to subject lines, openers, second lines, follow-ups, and any CTA-style copy.
- If a deliverability checker or QA review flags a word or phrase, treat it as banned going forward unless the user explicitly approves an exception.
- When in doubt, choose the lower-hype rewrite instead of trying to defend borderline wording.

---

## What to avoid — internal QA banned single words

`get`, `bank`, `credit`, `access`, `open`, `compare`, `problem`, `now`, `billing`, `deal`, `finance`, `financial`, `claims`, `insurance`, `mortgage`, `soon`, `new`, `performance`, `freedom`, `home`, `sales`, `medical`, `urgent`, `life`, `marketing`, `investment`, `diagnostics`, `friend`, `cash`, `invoice`, `extra`, `purchase`

---

## What to avoid — internal QA banned short phrases

`off chance`, `one time`, `all good`, `following up here`, `last note from me here`, `great fit`, `bumping this once`, `just following up once`, `circle back`, `one more quick follow-up`, `keep this open`, `compare notes`, `compare notes live`, `appreciate the reply`

---

## What to avoid — broader high-risk promotional or pressure wording

`$$$`, `50% off`, `100% guaranteed`, `100% free`, `100% off`, `100% satisfied`, `access now`, `act fast`, `act immediately`, `act now`, `action required`, `affordable deal`, `amazing`, `amazing deal`, `amazing offer`, `apply here`, `apply now`, `avoid bankruptcy`, `bargain`, `best bargain`, `best deal`, `best offer`, `best price`, `best rates`, `big profit`, `bonus`, `buy now`, `buy today`, `call now`, `can't live without`, `cash bonus`, `cash out`, `claim now`, `claim your discount`, `click`, `click below`, `click here`, `click this link`, `contact us immediately`, `deal ending soon`, `discount`, `don't delete`, `double your money`, `double your wealth`, `drastically reduced`, `earn`, `earn cash`, `earn extra income`, `earn money`, `easy income`, `exclusive deal`, `expires today`, `extra cash`, `extra income`, `fantastic`, `fantastic offer`, `fast cash`, `final call`, `for free`, `free access`, `free consultation`, `free gift`, `free membership`, `free money`, `free quote`, `free trial`, `full refund`, `get it now`, `get out of debt`, `get started now`, `giveaway`, `great news`, `guaranteed deposit`, `guaranteed results`, `hurry up`, `important information`, `immediately`, `increase revenue`, `increase sales`, `incredible deal`, `instant earnings`, `instant income`, `instant savings`, `investment advice`, `join millions`, `limited time`, `lowest price`, `make money`, `million dollars`, `money-back guarantee`, `must read`, `no catch`, `no cost`, `no obligation`, `no strings attached`, `once in a lifetime`, `only $`, `only available here`, `order now`, `order today`, `please read`, `price protection`, `profits`, `promise`, `pure profit`, `quote`, `risk-free`, `satisfaction guaranteed`, `save $`, `save big money`, `save up to`, `sign up free`, `special invitation`, `special offer`, `special promotion`, `supplies are limited`, `take action now`, `the best`, `this won't last`, `thousands`, `time limited`, `today`, `top urgent`, `trial`, `unbeatable offer`, `unbelievable`, `unlimited`, `urgent`, `what are you waiting for?`, `while supplies last`, `why pay more?`, `will not believe`, `winner announced`, `wonderful`, `you are a winner`, `you will not believe your eyes`

---

## What to avoid — phishing-style or security-warning language

`access your account`, `account update`, `activate now`, `change password`, `click to verify`, `confirm your details`, `confidential information`, `data breach`, `download now`, `final notice`, `important update`, `immediate action required`, `install now`, `last warning`, `log in now`, `new login detected`, `password reset`, `payment details needed`, `phishing alert`, `security breach`, `security update`, `update account`, `verify identity`, `warning message`

---

## What to avoid — irrelevant blacklisted categories (never appear in user copy)

`100% natural`, `adult content`, `bet now`, `blackjack`, `casino bonus`, `cure for`, `diet pill`, `doctor recommended`, `fat burner`, `fast weight loss`, `free chips`, `free spins`, `gamble online`, `guaranteed weight loss`, `jackpot`, `lottery winner`, `medical breakthrough`, `miracle cure`, `natural remedy`, `no prescription needed`, `online betting`, `online casino`, `online pharmacy`, `pain relief`, `poker tournament`, `prescription drugs`, `reverse aging`, `risk-free bet`, `safe and effective`, `scientifically proven`, `secret formula`, `slots jackpot`, `spin to win`, `vip offer`, `weight loss`, `winning numbers`, `xxx`

---

## How to avoid them

- Rewrite hype into plain, observational language.
- Replace pressure with permission.
- Replace promotional wording with specific business language.
- If a line sounds like an ad, coupon, scam, phishing message, or fake urgency, rewrite it.
- If a bump sounds filler-heavy or vague, replace it with a direct next-step question or a clear closeout line.
- If a value line uses fuzzy wording like `tight`, `fit`, `access`, or `problem`, rewrite it so the operational meaning is explicit.
- If a reply acknowledgement sounds low-status or unnecessary, remove it and go straight to the next useful question.
- If a sentence sounds polished in an AI way, simplify it until it reads like a person speaking plainly.

---

## Nuance rules — when a token is still unsafe

- Punctuation does not make a banned token safe.
- Hyphenating a banned token does not make it safe.
- Splitting or joining the word does not make it safe if the root token is still obvious.
- Treat close variants as banned too when the risky root token is still clearly present.
- Examples: `cash-cycle` is still `cash`; `invoice-line` is still `invoice`; `extra-room` is still `extra`; `purchase-cycle` is still `purchase`.

---

## Nuance rules — company names

- If a banned word appears inside a company name used in copy, do not drop the company reference entirely if the line still needs the name.
- Rewrite the displayed company name so the banned token is gone from standalone form.
- Prefer the simplest deterministic rewrite that keeps the name recognizable.
- First choice: remove the banned token if the remaining name still reads clearly.
- Only abbreviate or compress when removing the token would make the name unclear.
- Examples: `Access Brand Communications` → `AB Communications`; `Calcon Mutual Mortgage` → `Calcon Mutual`; `Buckeye Insurance` → `Buckeye`; `Coming Soon New York` → `Coming NY`.

---

## Formatting and style bans

- No em dashes.
- No ALL CAPS.
- No multiple exclamation marks.
- No greeting prefix before the first name such as Hi, Hello, or Hey.
- No third-person company references such as `[Company] offers` or `[Company] helps`.
- No fake urgency, misleading subject lines, excessive links, or promotional formatting.

---

## Safe replacement patterns

- Instead of `free consultation`, use `open to a short conversation`.
- Instead of `special offer`, use `what we're seeing in the market`.
- Instead of `act now`, use `if relevant, happy to send details`.
- Instead of `guaranteed results`, use `this may be relevant depending on your situation`.
- Instead of `click here`, use `let me know and I can send it over`.
- Instead of `limited time`, use `not sure if this is timely for you`.
- Instead of `increase revenue`, use a precise business outcome such as `help support liquidity` when that is actually true.

---

## Final check before approving copy

1. Scan the subject line for spam-trigger wording.
2. Scan the body for banned or high-risk wording.
3. Rewrite any hype-heavy or pressure-heavy line into plain language.
4. Remove fake urgency.
5. Keep the email sounding like a credible real person, not a promotion.
