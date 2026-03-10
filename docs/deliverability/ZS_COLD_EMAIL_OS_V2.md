# ZS Cold Email OS v2

Normalized from the uploaded PDF into Markdown so the repo stays text-only.

## Core philosophy

The lazy approach of launching campaigns without a tight offer, clean copy, and ICP fit is dead.

The 2026 meta is maximizing engagement. Every decision - which leads go first, how the email is written, and how the copy is structured - must optimize for replies, not just volume. High engagement protects deliverability. Poor engagement destroys it.

Principles:
- Do not send lazy.
- Do not send broad on day 1.
- Earn the right to volume.

## 1. Infrastructure

Infrastructure is the foundation. If it fails, nothing else matters.

Standard provision per client:
- 1,500 emails/day active pool
- 1,500 emails/day insurance pool
- 3,000 emails/day total provisioned

### Vendor notes

- InboxKit: Azure / Outlook inboxes
- ENDY: Google / GSuite inboxes
- Porkbun / Dynadot: domain registration
- Plusvibe: primary sending platform and campaign management

### Infrastructure math for 1,500/day

- Azure / Outlook launch: 2 emails per inbox per day
- Azure / Outlook scale: 5 emails per inbox per day
- Google / GSuite launch: 8 emails per inbox per day
- Google / GSuite scale: 15 emails per inbox per day

### Enterprise spam filter avoidance

Azure / Outlook inboxes are more likely to hit enterprise filters like Proofpoint, Mimecast, Barracuda, and Abnormal Security.

Rules:
- Keep Azure send rates very low, especially at launch.
- Never hammer enterprise targets from Azure / Outlook inboxes.
- Route enterprise-heavy lists through Google inboxes first.
- If more than 30% of a list is behind enterprise filters, lean heavily on aged Google domains and do not use Azure as the primary channel.

### Domain strategy

- Buy 3x the domains you think you need.
- Keep one third active, one third insurance / warming, one third staged for future rotation.
- Buy generic non-branded `.com` domains on sale and let them age.
- Keep emergency generic domains stocked for fast swaps.
- Domains are an annual cost; inboxes are a monthly cost. Buying and aging domains early is a cheap deliverability asset.

### 15-day rotation cycle

Rotate every 15 days instead of monthly.

- Days 1-15: Group A active, Group B warming / insurance
- Days 16-30: Group A resting / re-warming, Group B active
- Days 31-45: Group A active, Group B resting / re-warming

Naming convention in Plusvibe:
`[Client] | [Industry] | [Launch Date] | [Group A / Group B]`

### One email per company per day

Hard rule: never send more than one email to any single company within 24 hours.

Enforcement:
- Deduplicate at the company-domain level before upload
- Use Plusvibe company-domain deduplication where available
- Stagger multi-contact campaigns by at least 24 hours

## 2. Warmup protocol and DNS verification

### Warmup timeline

- Week 1-2: warmup only, no campaign sends
- Week 3-4: continue warmup, begin DNS verification, prepare copy and list
- Week 4+: ready for most launches
- Week 6-8: recommended for Outlook / enterprise-heavy lists

### Warmup rules

- Minimum warmup: 2 weeks
- Target warmup: 4 weeks
- Outlook / enterprise lists: 6-8 weeks
- Never skip warmup because of client urgency

### DNS checklist before every launch

Verify:
- SPF exists and passes
- DKIM exists and passes
- DMARC exists and passes
- Test email shows `spf=pass`, `dkim=pass`, and `dmarc=pass`
- Domain is not blacklisted
- MX records point to the correct mail server
- Custom tracking domain, if used, is verified correctly

Use MXToolbox and Gmail "Show Original" for checks.

If SPF, DKIM, or DMARC fails, stop and fix DNS before sending any live email.

## 3. Launch protocol: engagement first

### Phase 1: Intent-only launch (days 1-5)

Send first to the highest-signal audience.

Priority signals:
- Companies actively hiring for roles the offer solves
- Recently funded companies
- Recent leadership changes in relevant roles
- Recent relevant tech-stack changes
- Prospects who engaged with LinkedIn content

Volume caps:
- Azure: 2 emails/inbox/day
- Google: 8 emails/inbox/day
- Total campaign volume: 500-800/day for the first 5 days
- Max pacing: 1 email/hour/inbox

### Phase 2: Gmail-only sending (days 1-14)

For new infrastructure:
- Default to Google / Gmail-only sending for the first 2 weeks
- Disable Outlook and enterprise-filtered targets initially
- Sort enterprise-filtered leads to later sub-campaigns

### Outlook trial rule

Introduce Outlook only after day 14 and only on aged domains.

If Outlook targets show zero replies and zero out-of-office responses within 24 hours, shut Outlook sending off immediately.

### Phase 3: Copy and offer lock

Nothing goes out until the message clears the engagement bar.

Pre-send checklist:
- A 10-year-old should understand the offer
- Copy should sound human, not corporate
- WIIFM should be clear
- Spam words removed
- CTA should be a small ask, not a big commitment
- Subject line should usually be under 6 words
- Preview text should be intentional
- Spintax variants must be reviewed manually
- No images, PDFs, or links in email 1
- One email per company per day must be enforced

### Phase 4: Broad list rollout (week 2-3)

Scale only after positive reply signals are confirmed.

Rules:
- Open to the broader ICP only after intent-only launch proves positive
- Azure scale limit: 5 emails/inbox/day
- Google scale limit: 15 emails/inbox/day
- Reintroduce Outlook only on aged domains
- Increase volume by no more than 20% week over week
- Use AI-generated copy for broad rollout, not static templates

## 4. Copy, testing, and spam compliance

### Heavy spintax is mandatory

Every campaign must launch with heavy spintax from day one.

Required variation areas:
- Opening angle
- Sentence structure
- CTA phrasing
- Signature style

Rules:
- Keep the offer the same inside one campaign
- Use separate campaigns for different offers
- Review every variant manually before launch

### Testing rules

- Test at least 1,000 sends before judging results
- Wait 48 hours before drawing conclusions
- Change meaningful chunks, not tiny wording
- Test one variable at a time
- Spintax inside a campaign is style testing; separate campaigns are offer testing

### Test priority order

1. Offer / value proposition
2. ICP segment / list quality
3. Preview text + subject line
4. Email 1 opening angle
5. CTA phrasing
6. Personalization variable

### AI copy at scale

Once a campaign moves past intent-only launch into broad rollout:
- Generate company-specific first lines or observations with Clay + AI
- Use company description, website, and pain points in prompts
- Mirror the company's own vocabulary back to them
- Show real research effort

### Spam-word removal

Mandatory: check every email against the Mailmeteor spam-word list.

High-risk examples to eliminate:
- free
- guarantee
- no obligation
- limited time
- act now
- click here
- earn money
- increase sales
- make money
- risk-free
- winner
- prize
- urgent

Check every spintax variant, not just the primary one.

### Email 1 matters most

Email 1 is the top-performing email in the sequence.

Rules:
- Optimize for Email 1 send volume, not deep sequences
- If Email 1 is weak, fix it before relying on follow-ups
- Additional follow-ups increase spam-report risk, especially after Email 3

## 5. Deliverability monitoring

### Four core signals

Track continuously:
- Campaign reply rate
- Inbox reputation / warmup score
- Bounce rate
- Domain-level reply rate

### Threshold rules

- Inbox reputation below 98%: pull the inbox immediately
- Bounce rate above 2% with valid addresses: treat as a domain problem
- Domain-level reply rate far below client average: investigate or cancel the domain
- Zero out-of-office replies on meaningful volume: treat as a full infra problem

### No open tracking

Open tracking stays off permanently.

Reason:
- Open pixels identify you as a marketer to spam filters
- Reply rate, warmup score, bounce rate, and domain-level reply rate are enough

### Diagnosing infra vs offer problems

Order of operations:
1. Check inbox reputation
2. Check bounce codes
3. Check domain-level reply rate
4. Check for missing autoresponses
5. If infra is clean, rewrite the campaign instead of ordering new domains

Compare against client-specific baselines, not universal reply-rate benchmarks.

## 6. Hot swap protocol

Downtime kills pipeline. The goal is zero dead days.

### When a domain fails

1. Remove failing inboxes from active campaigns immediately.
2. Tag the domain as failed internally.
3. Pull from the insurance pool.
4. Cancel the failed domain to stop billing.
5. Set up forwarding from the failed inbox to the replacement inbox.
6. Order a fresh domain and start warmup immediately.

### Insurance pool sizing

Keep:
- 1,500/day active pool
- 1,500/day insurance pool
- 5-10 aged generic emergency domains per client

### Outlook / enterprise filter protocol

- Default to Google inboxes on day 1
- Use Azure / Outlook only on aged domains
- If Outlook shows no replies and no out-of-offices, shut it off
- Keep emails shorter and simpler for Outlook-heavy lists
- If >30% of the list is behind Proofpoint or Mimecast, use aged Google inboxes only

## 7. List building for maximum engagement

The list is part of the offer. Wrong people waste infrastructure.

### Build methods

- Forward: clear ICP, straightforward Apollo / Clay filtering
- Backward: start from won deals, then analyze firmographics and build TAM
- Circular: niche edge cases only, using lookalikes plus AI validation

### LinkedIn About Us as the primary filter engine

Industry tags are unreliable for niche ICPs. Use LinkedIn About Us text instead.

Method:
- Pull the LinkedIn URL into Clay
- Extract About Us text
- Build a keyword bank from ideal accounts
- Filter on broad industry plus precise About Us keyword match

### Golden ICP layering

- 4 criteria match: hyper-personalized AI creative ideas campaign
- 3 criteria match: personalized value-prop campaign
- 2 criteria match: broad offer campaign
- 1 criterion match: only use if TAM is small and more volume is needed

## 8. KPI hygiene

### Deliverability KPIs

- Inbox reputation: green above 99%, red below 98%
- Bounce rate: green below 1%, red above 2%
- Missing autoresponses: red if zero on meaningful volume
- Bounce type: 550 / blocked / reported as spam means the domain is burned

### Engagement KPIs

- Overall campaign reply rate: green above 2% or above client average
- Domain-level reply rate vs client average: red if more than 40% below
- Positive reply rate: green above 50% of replies
- Negative / unsubscribe rate: red above 0.5%

### Copy and offer KPIs

- Email 1 should outperform later emails
- Spam-word check should be clear before launch
- Spintax variants must sound human
- AI personalization must be accurate and company-specific

### Infrastructure KPIs

- Insurance pool availability should stay above 100% of ADV when possible
- Active domains should generally be 4+ weeks old
- 15-day rotation should stay on schedule
- Azure should stay at or below 5 emails/inbox/day
- Google should stay at or below 15 emails/inbox/day

## Scale decision framework

### When to scale volume

All of these must be true:
- All inboxes above 99% reputation
- Bounce rate below 1%
- Campaign reply rate at or above client baseline for 48+ hours
- Insurance pool has at least 50% of ADV warmed and ready
- Outlook / Azure performs within 20% of Google reply rate, or Outlook is disabled

Scale slowly: max +20% per week.

### When to pause and fix

Pause immediately if any of the following happens:
- Any inbox drops below 98% reputation
- Bounce rate exceeds 2% with validated addresses
- Zero out-of-office replies on meaningful volume
- Bounce codes show 550 / message blocked / reported as spam
- Domain-level reply rate is 40%+ below client average

Do not add volume to a broken campaign. Fix the problem first.
