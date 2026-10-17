# The learning loop (T11, backend)

The paper improves with use. Reader behaviour becomes small, explainable profile changes, applied
nightly by the `learn` pipeline stage (before `compose`) and incrementally after strong signals.

![Precision@10 over a week of simulated reading](learning-curve.png)

`python -m app.scripts.simulate_reader` regenerates the chart: a synthetic reader with hidden
tastes reads seven editions built by the real scorer and selector; precision@10 is the share of
the first ten stories they truly care about. No database, network or LLM is involved.

## Signals (`app/personalize/config.py`, `SignalWeights`)

| Event | Weight |
| --- | --- |
| open (or mark read) | +1.0 |
| dwell >= 30 s | +0.8 x min(1, dwell / expected reading time) |
| more like this | +1.5 |
| save | +1.2 |
| quiz answered correctly | +0.3 |
| impression, never touched | -0.05 |
| skip | -0.6 |
| less like this | -1.5 |
| onboarding like / skip | open / skip weight x 0.5 |

Events collapse per edition item first (opens count once, dwell takes the longest stretch, the
toggles keep the reader's last word and `value: 0` retracts). Each story's weight is then decayed
with a 14-day half-life. Expected reading time comes from the article's word count (230 wpm,
clamped to 30-300 s; 90 s when unknown).

## Update rules (`app/personalize/learn.py`, pure functions)

1. **Topics**: EMA towards `positive / (positive + negative)` evidence per topic, step
   `0.3 x mass / (mass + 1)`, clamped to [0, 1]. Topics with no signal at all lose 0.5% a night.
2. **Interest vector**: Rocchio, `v' = normalise(0.8 v + 0.25 mean(liked) - 0.1 mean(disliked))`,
   where liked/disliked are stories whose net weight is >= +0.3 / <= -0.3.
3. **Entities**: named in >= 3 liked stories -> added to the profile (also listed in
   `learned_entities`). Scoring already matches profile entities, so they take effect at once.
4. **Blocking**: three "less like this" on a topic's stories blocks the topic.
5. **Source affinity**: `(opened - skipped) / (opened + skipped + 2)` per source, in [-1, 1]; the
   scorer turns it into a 0.5x-1.5x multiplier.
6. **Explore**: an explore pick the reader engaged with lifts its topic to 0.4; if fewer than 20%
   of at least three explore picks are engaged, the explore rate falls x0.8 per night to a 5% floor.

Every change is a `profile_changes` row: kind, key, before, after, delta, a reason and the
strongest events behind it. `reader_profiles.learn_state` keeps the watermark and running tallies
so a run never counts an event twice.

## Incremental runs

`learn_service.learn_after_events(sessionmaker, user_id, event_types)` runs the same rules
(without the nightly idle decay) on the stories that carry a `more_like`, `less_like` or `save`,
and remembers them as settled so the nightly run skips them. The events router calls it as a
background task once Task 10's `/events` lands.
