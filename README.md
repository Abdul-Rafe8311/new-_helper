# NewsHelper

[![CI](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Abdul-Rafe8311/new-_helper/actions/workflows/ci.yml)

A personalised morning newspaper that gathers the day's stories, writes one edition for each reader, and learns from what they read.

## Try the demo

**<https://new-helper-nine.vercel.app>**

The demo account is seeded. Use the demo button on the sign-in page to get in without signing up.

<!-- TODO: add a screenshot of /today (docs/screenshots/today.png). Only the /interests screenshots exist so far. -->
> TODO: screenshot of `/today` is not in the repo yet.

Sample edition as a PDF: [docs/samples/newshelper-sample-edition.pdf](docs/samples/newshelper-sample-edition.pdf)

## How it meets the brief

| Requirement | Feature in the repo |
| --- | --- |
| 1. Onboarding that captures interests | `/onboarding` is a step flow: name, beats (topics), free-text words parsed by Claude into keywords, reading time and depth, and a taste test on real articles. Answers autosave. |
| 2. Daily PDF in newspaper style, personalised in content and presentation | The daily pipeline composes one edition per reader and typesets it with WeasyPrint. Content is chosen from the reader's profile. Presentation follows it too: section order follows topic weights, and the reading depth (brief, balanced, deep) changes summary length and the number of briefs. |
| 3. Web reader, PDF download and archive | `/today` and `/paper/[date]` show the edition, `/archive` lists past editions, `/saved` keeps saved stories, and each edition has a PDF download. |
| 4. Learning from behaviour | Opens, reading time, saves, skips, "more like this" and "less like this" are logged as events. The `learn` stage turns them into profile changes. `/interests` shows what was learned and lets the reader edit it. |
| 5. Creative extras | Recall quiz with a streak counter and a "Still remember?" card on `/today`. Audio ("Listen"): Not yet built. "Ask your paper": Not yet built. Sunday edition: Not yet built. |

## How it learns

Each reader action becomes a small, logged change to their interest profile, with older signals fading over time. The next edition is ranked against the updated profile, and `/interests` shows every change.

![Precision@10 over a week of simulated reading](docs/learning-curve.png)

Precision@10 rose from 0.52 on day 1 to 0.88 on day 7, on simulated readers (5 synthetic readers, with a control group). Details are in [docs/learning.md](docs/learning.md).
