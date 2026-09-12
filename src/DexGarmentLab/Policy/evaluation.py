"""Phase 1 score accounting from timestamped simulator measurements.

Source: Phase 1 proposal plus the user's short-sleeve/pickup revision.
No Isaac imports are required.
This module scores measurements; it does not infer dressing from proximity or
gripper commands. See docs/PHASE1_EVALUATION.md for the measurement contract and
the implementation choices that the proposal leaves unspecified.
"""
from dataclasses import asdict, dataclass
import math
from statistics import fmean


ARMS = ('left', 'right')
STAGES = ('pickup', 'first_sleeve', 'opposite_shoulder', 'second_sleeve')
EPS = 1e-8


def number(value, name, minimum=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{name} must be a number')
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name} must be finite and >= {minimum}')
    return value


def boolean(value, name):
    if not isinstance(value, bool):
        raise ValueError(f'{name} must be a JSON/Python boolean')
    return value


@dataclass(frozen=True)
class ScoringConfig:
    # 20 Hz matches DressingEnv. Physics-step recording can use 1/240 instead.
    max_sample_gap_s: float = 0.05
    time_limit_s: float | None = None
    simultaneous_first_arm: str = 'left'

    def __post_init__(self):
        if number(self.max_sample_gap_s, 'max_sample_gap_s') <= 0:
            raise ValueError('max_sample_gap_s must be positive')
        if self.time_limit_s is not None and number(self.time_limit_s, 'time_limit_s') <= 0:
            raise ValueError('time_limit_s must be positive')
        if self.simultaneous_first_arm not in ARMS:
            raise ValueError('simultaneous_first_arm must be left or right')


def validate_sample(sample):
    """Reject missing measurements instead of silently substituting zero."""
    if not isinstance(sample, dict):
        raise ValueError('Each sample must be an object')
    try:
        t = number(sample['time_s'], 'time_s')
        holding = sample['gripper_holding']
        if not isinstance(holding, (list, tuple)) or len(holding) != 2:
            raise ValueError('gripper_holding must contain exactly two booleans')
        holding = [boolean(v, 'gripper_holding') for v in holding]
        clear = boolean(sample['garment_lifted_clear'], 'garment_lifted_clear')
        lifted = sample.get('gripper_lifted', [clear, clear])
        if not isinstance(lifted, (list, tuple)) or len(lifted) != 2:
            raise ValueError('gripper_lifted must contain exactly two booleans')
        lifted = [boolean(v, 'gripper_lifted') for v in lifted]
        complete = boolean(sample.get('dressing_complete', False), 'dressing_complete')
        mappings = {}
        for key in ('wrist_in_sleeve', 'garment_beyond_shoulder', 'arm_coverage'):
            if not isinstance(sample[key], dict) or set(sample[key]) != set(ARMS):
                raise ValueError(f'{key} must have exactly left and right keys')
            if key == 'arm_coverage':
                mappings[key] = {arm: number(sample[key][arm], f'{key}.{arm}') for arm in ARMS}
                if any(v > 1 for v in mappings[key].values()):
                    raise ValueError('arm_coverage uses fractions [0,1], not percentages [0,100]')
            else:
                mappings[key] = {arm: boolean(sample[key][arm], f'{key}.{arm}') for arm in ARMS}
        clock = {}
        if 'first_contact_time_s' in sample:
            first = sample['first_contact_time_s']
            if first is not None:
                first = number(first, 'first_contact_time_s')
                if first > t + EPS:
                    raise ValueError('First contact cannot be in the future')
            clock['first_contact_time_s'] = first
            if 'physics_tick' in sample:
                tick, first_tick = sample['physics_tick'], sample.get('first_contact_tick')
                dt = number(sample.get('physics_dt_s'), 'physics_dt_s')
                if type(tick) is not int or tick < 0 or dt <= 0 or abs(tick * dt - t) > EPS:
                    raise ValueError('Physics tick/dt does not match sample time')
                if first is None:
                    if first_tick is not None:
                        raise ValueError('Contact tick without contact time')
                elif (type(first_tick) is not int or not 0 <= first_tick <= tick
                      or abs(first_tick * dt - first) > EPS):
                    raise ValueError('Contact tick does not match contact time')
                clock.update(physics_tick=tick, first_contact_tick=first_tick, physics_dt_s=dt)
        return dict(time_s=t, gripper_holding=holding, garment_lifted_clear=clear,
                    gripper_lifted=lifted, dressing_complete=complete, **mappings, **clock)
    except KeyError as exc:
        raise ValueError(f'Missing measurement: {exc.args[0]}') from exc


class Phase1Scorer:
    """Accumulate milestones and best arm progress; latch complete dressing.

    At least two samples are required, starting at episode time zero. Pickup
    requires the SAME gripper to hold a lifted grasp region for >=3 s.
    Changing grippers does not splice two shorter holds into a qualifying hold.
    """
    def __init__(self, config=None):
        self.config = config or ScoringConfig()
        self.reset()

    def reset(self):
        self.last = None
        self.sample_count = 0
        self.hold_started = [None, None]
        self.first_arm = None
        self.awarded_at = {stage: None for stage in STAGES}
        self.best_coverage = {arm: 0.0 for arm in ARMS}
        self.completion_started = None
        self.dressing_completed_at = None

    def update(self, sample):
        sample = validate_sample(sample)
        t = sample['time_s']
        if self.last is None:
            if abs(t) > EPS:
                raise ValueError('The first measurement must be at episode time 0')
        else:
            gap = t - self.last['time_s']
            if ('first_contact_time_s' in sample) != ('first_contact_time_s' in self.last):
                raise ValueError('Cannot change timing basis during an episode')
            previous_contact = self.last.get('first_contact_time_s')
            if previous_contact is not None and sample['first_contact_time_s'] != previous_contact:
                raise ValueError('First contact time must remain latched')
            if previous_contact is None and sample.get('first_contact_time_s') is not None:
                if sample['first_contact_time_s'] <= self.last['time_s']:
                    raise ValueError('Contact was omitted from an earlier sample')
            if gap <= 0:
                raise ValueError('Sample times must strictly increase')
            if gap > self.config.max_sample_gap_s + EPS:
                raise ValueError('Missing samples: gap exceeds max_sample_gap_s')
        if self.config.time_limit_s is not None and t > self.config.time_limit_s + EPS:
            raise ValueError('Measurement exceeds time limit; stop sampling at the deadline')

        for i, holding in enumerate(sample['gripper_holding']):
            if holding and sample['gripper_lifted'][i]:
                if self.hold_started[i] is None:
                    self.hold_started[i] = t
                if t - self.hold_started[i] >= 3.0 - EPS:
                    self._award('pickup', t)
            else:
                self.hold_started[i] = None

        wrists = sample['wrist_in_sleeve']
        if self.first_arm is None:
            entered = [arm for arm in ARMS if wrists[arm]]
            if entered:
                self.first_arm = (entered[0] if len(entered) == 1
                                  else self.config.simultaneous_first_arm)
                self._award('first_sleeve', t)
        if self.first_arm is not None:
            other = 'right' if self.first_arm == 'left' else 'left'
            if sample['garment_beyond_shoulder'][other]:
                self._award('opposite_shoulder', t)
            if wrists[other]:
                self._award('second_sleeve', t)
        if self.first_arm is not None:
            for arm in ARMS:
                self.best_coverage[arm] = max(self.best_coverage[arm], sample['arm_coverage'][arm])
        # Require a short continuous confirmation, rather than one noisy frame.
        if sample['dressing_complete'] and all(wrists.values()):
            if self.completion_started is None:
                self.completion_started = t
            if t - self.completion_started >= 0.5 - EPS and self.dressing_completed_at is None:
                self.dressing_completed_at = t
        else:
            self.completion_started = None
        self.last = sample
        self.sample_count += 1
        return self.points()

    def _award(self, stage, t):
        if self.awarded_at[stage] is None:
            self.awarded_at[stage] = t

    def points(self):
        breakdown = {stage: 5.0 if t is not None else 0.0
                     for stage, t in self.awarded_at.items()}
        n = m = 0.0
        if self.first_arm is not None:
            other = 'right' if self.first_arm == 'left' else 'left'
            n = self.best_coverage[self.first_arm]
            m = self.best_coverage[other]
        complete = self.dressing_completed_at is not None
        breakdown['first_arm_coverage'] = 10.0 if complete else 10.0 * n
        breakdown['second_arm_coverage'] = 20.0 if complete else 20.0 * m
        overall = breakdown['first_arm_coverage'] + breakdown['second_arm_coverage']
        items = {stage: {'points': breakdown[stage], 'max_points': 5.0,
                         'achieved': self.awarded_at[stage] is not None,
                         'achieved_at_episode_s': self.awarded_at[stage]} for stage in STAGES}
        items['overall_dressing'] = {
            'points': overall, 'max_points': 30.0,
            'first_arm': self.first_arm,
            'second_arm': None if self.first_arm is None else ('right' if self.first_arm == 'left' else 'left'),
            'n': n, 'm': m, 'coverage_basis': 'best measured fraction per arm',
            'first_arm_points': breakdown['first_arm_coverage'], 'max_first_arm_points': 10.0,
            'second_arm_points': breakdown['second_arm_coverage'], 'max_second_arm_points': 20.0,
            'measured_coverage_points': 10.0 * n + 20.0 * m,
            'full_dressing_override': complete,
        }
        return {'raw_points': sum(breakdown.values()), 'max_raw_points': 50.0,
                'score_items': items, 'score_breakdown_version': 'separate-dressing-items-v4',
                'overall_dressing_points': overall,
                'max_overall_dressing_points': 30.0,
                'dressing_complete': complete,
                'coverage_score_overridden': complete,
                'current_arm_coverage': dict(self.last['arm_coverage']) if self.last else dict(self.best_coverage),
                'dressing_completed_at_s': self.dressing_completed_at,
                'pickup_hold_seconds': [0.0 if start is None or self.last is None else
                                         self.last['time_s'] - start for start in self.hold_started],
                'breakdown': breakdown, 'first_arm': self.first_arm,
                'first_arm_coverage': n, 'second_arm_coverage': m,
                'milestone_times_s': dict(self.awarded_at)}

    def result(self):
        if self.sample_count < 2 or self.last['time_s'] <= 0:
            raise ValueError('Final scoring requires a positive duration and at least two samples')
        result = self.points()
        duration = self.last['time_s']
        if 'first_contact_time_s' in self.last:
            first = self.last['first_contact_time_s']
            elapsed = 0.0 if first is None else max(0.0, duration - first)
            if first is not None and 'physics_tick' in self.last:
                elapsed = (self.last['physics_tick'] - self.last['first_contact_tick']) * self.last['physics_dt_s']
            status = 'no_contact' if first is None else 'awaiting_elapsed_time' if elapsed <= EPS else 'scored'
            return dict(result, task_time_s=elapsed, elapsed_episode_time_s=duration,
                        first_contact_time_s=first, timing_basis='first_garment_mannequin_contact',
                        scoring_revision='separate-dressing-items-v4', score_status=status,
                        final_score=result['raw_points'] / elapsed if status == 'scored' else None,
                        score_unit='points/s', sample_count=self.sample_count)
        return dict(result, task_time_s=duration,
                    scoring_revision='separate-dressing-items-v4', timing_basis='episode_start_legacy',
                    final_score=result['raw_points'] / duration,
                    score_unit='points/s', sample_count=self.sample_count)


def format_score_items(result):
    """One shared display for live teleop, replay and batch/policy evaluation."""
    items = result['score_items']
    labels = [('pickup', 'Pickup'), ('first_sleeve', 'First sleeve'),
              ('opposite_shoulder', 'Opposite shoulder'), ('second_sleeve', 'Second sleeve'),
              ('overall_dressing', 'Overall dressing')]
    parts = [f"{label} {items[key]['points']:.2f}/{items[key]['max_points']:.0f}" for key, label in labels]
    overall = items['overall_dressing']
    parts[-1] += (f" (first {overall['first_arm_points']:.2f}/10, "
                  f"second {overall['second_arm_points']:.2f}/20)")
    if overall['full_dressing_override']:
        parts[-1] += ' [complete-dressing override]'
    return ' | '.join(parts)


def evaluate_episode(samples, config=None):
    """Evaluation function: final score = (5+5+5+5+10*n+20*m) / seconds.

    Each 5-point term is included only if its milestone was achieved.
    n and m retain best progress; full dressing overrides their score terms.
    """
    scorer = Phase1Scorer(config)
    for sample in samples:
        scorer.update(sample)
    return scorer.result()


def evaluate_submissions(data, config=None):
    """Mean points/s across shared unique seeds; best whole submission counts.

    Mean aggregation is an explicit implementation choice, NOT a formula stated
    in the proposal. Do not select the best seed or mix episodes across retries.
    """
    config = config or ScoringConfig()
    if not isinstance(data, dict) or data.get('schema_version') not in ('phase1-measurements-v1', 'phase1-measurements-v2', 'phase1-measurements-v3'):
        raise ValueError('Expected schema_version phase1-measurements-v1, v2 or v3')
    submissions = data.get('submissions')
    if not isinstance(submissions, list) or not submissions:
        raise ValueError('At least one submission is required')
    reference_seeds, ids, results = None, set(), []
    for submission in submissions:
        sid = submission.get('submission_id')
        if not isinstance(sid, str) or not sid.strip() or sid in ids:
            raise ValueError('submission_id must be a unique nonempty string')
        ids.add(sid)
        episodes = submission.get('episodes')
        if not isinstance(episodes, list) or len(episodes) < 2:
            raise ValueError('Each submission needs at least two randomized initial-state seeds')
        seeds, scores = set(), []
        for episode in episodes:
            seed = episode.get('seed')
            if type(seed) is not int or seed < 0 or seed in seeds:
                raise ValueError('Each episode needs a unique nonnegative integer seed')
            seeds.add(seed)
            if not isinstance(episode.get('samples'), list):
                raise ValueError('Each episode needs a samples list')
            try:
                if data['schema_version'] != 'phase1-measurements-v3' and any(
                        isinstance(sample, dict) and 'first_contact_time_s' in sample for sample in episode['samples']):
                    raise ValueError('Contact-timed traces require v3; do not mix timing bases in a ranking')
                if data['schema_version'] in ('phase1-measurements-v2', 'phase1-measurements-v3'):
                    for sample in episode['samples']:
                        if not isinstance(sample, dict) or not {'gripper_lifted', 'dressing_complete'} <= sample.keys():
                            raise ValueError('v2 requires gripper_lifted and dressing_complete measurements')
                        if data['schema_version'] == 'phase1-measurements-v3' and 'first_contact_time_s' not in sample:
                            raise ValueError('v3 requires first_contact_time_s (null until first contact)')
                scores.append(dict(seed=seed, **evaluate_episode(episode['samples'], config)))
            except ValueError as exc:
                raise ValueError(f'Submission {sid}, seed {seed}: {exc}') from exc
        if reference_seeds is not None and seeds != reference_seeds:
            raise ValueError('All submissions must use the same seed set')
        reference_seeds = seeds
        if any(e['final_score'] is None for e in scores):
            raise ValueError('No comparable points/s: an episode has no contact or no positive post-contact duration')
        results.append({'submission_id': sid, 'episodes': scores,
                        'final_score': fmean(e['final_score'] for e in scores),
                        'mean_raw_points': fmean(e['raw_points'] for e in scores)})
    best = max(results, key=lambda result: result['final_score'])
    contact_timing = data['schema_version'] == 'phase1-measurements-v3'
    return {'schema_version': 'phase1-scores-v4',
            'rules_source': 'Phase 1 proposal with user revision: lifted grasp region, best progress, sleeves plus neck completion',
            'scoring_revision': 'separate-dressing-items-v4',
            'timing_basis': 'first_garment_mannequin_contact' if contact_timing else 'episode_start_legacy',
            'aggregation': 'arithmetic mean of episode points/s (implementation choice)',
            'config': asdict(config), 'submissions': results,
            'best_submission_id': best['submission_id'],
            'final_score': best['final_score'], 'score_unit': 'points/s'}


class Phase1TaskEvaluator:
    """DressingEnv evaluator hook with an explicit trusted measurement callback.

    measure(info) must return validate_sample()'s fields except time_s. It must
    read actual geometry/attachments, not action intentions. The environment
    clock supplies time_s. This adapter does not install geometric detectors.
    """
    def __init__(self, measure, config=None):
        if not callable(measure):
            raise ValueError('measure must be callable')
        self.measure = measure
        self.scorer = Phase1Scorer(config)
        self.started = False

    def _sample(self, info):
        sample = dict(self.measure(info))
        sample['time_s'] = info['episode_time_s']
        return sample

    def reset(self, initial_info):
        self.started = False
        self.scorer.reset()
        self.scorer.update(self._sample(initial_info))
        self.started = True

    def __call__(self, previous_obs, action, next_obs, info):
        if not self.started:
            raise RuntimeError('Call evaluator.reset() before stepping')
        before = self.scorer.points()['raw_points']
        measurement = self._sample(info)
        self.scorer.update(measurement)
        result = self.scorer.result()
        limit = self.scorer.config.time_limit_s
        terminated = limit is not None and info['episode_time_s'] >= limit - EPS
        # Training reward is a raw-point delta; final ranking uses points/s.
        # Success now includes the measured neck/sleeve completion condition.
        result['success_evaluated'] = 'dressing_complete' in measurement
        result['success'] = result['dressing_complete']
        result['phase1_score_evaluated'] = True
        return result['raw_points'] - before, terminated, result
