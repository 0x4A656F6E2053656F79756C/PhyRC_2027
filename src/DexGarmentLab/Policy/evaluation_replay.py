"""Evaluate archived physical state on CPU, without starting a physics solver."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .evaluation_geometry import GarmentGeometry
from .evaluation_live import IsaacMeasurements, EvaluationSession
from .state import rotation
from .evaluation_contact import CollisionContact


def measurement_context(measurement):
    """Freeze the live evaluator's read-only landmarks/topology, including labels."""
    geometry = measurement.geometry
    return {
        'version': 1, 'metadata': measurement.metadata,
        'contact': measurement.contact_context,
        'geometry': {key: getattr(geometry, key).tolist() for key in ('faces', 'collar', 'collar_inner')},
        'geometry_lists': {key: [v.tolist() for v in getattr(geometry, key)] for key in ('loops', 'cuffs', 'inner')},
        'coverage_samples': geometry.coverage_samples,
        'arrays': {key: np.asarray(getattr(measurement, key)).tolist()
                   for key in ('neck_chain', 'head_surface', 'table_centres', 'table_size')},
        'arms': {side: chain.tolist() for side, chain in measurement.arms.items()},
        'thresholds': {key: getattr(measurement, key)
                       for key in ('clearance_m', 'max_anchor_error_m', 'pickup_rise_m')},
    }


class ReplayMeasurements(IsaacMeasurements):
    def __init__(self, context, metadata):
        if context.get('version') != 1:
            raise ValueError('Unsupported replay evaluation context')
        self.metadata = context['metadata']
        # Explicitly reject silently rescoring with different rules/geometry.
        # Known v2/v3 evidence can be rescored with the contact clock and
        # independent v4 items. Garment/anchor measurement math is unchanged.
        previous_sources = {
            'scoring_source_sha256': {'9abba388fb40a28a30a4cf036ea8a820164ab3e29007b0d9a4b2931f2a9bcc79',
                                      '47d40e535135c3292468e3cd4da5a810fa58395551bafd5ed9ed3088233cb8dd'},
            'live_source_sha256': {'ec96427d9c7324eb2f5b251f1faec808fa166347827a8ea81e8bd8a527570387',
                                   'f31681f0ef1e0b7f5c3abe1fe1523587179611b9f90b05aea66635652b2ddff6'}}
        self.metadata = dict(self.metadata)
        self.metadata['recorded_coverage_definition'] = self.metadata.get('coverage_definition')
        self.metadata['coverage_definition'] = ('best arm centreline progress; confirmed short-sleeve completion '
                                                'gives overall dressing 30/30; each 5-point milestone requires its own evidence')
        for field, name in [('geometry_source_sha256', 'evaluation_geometry.py'),
                            ('scoring_source_sha256', 'evaluation.py'),
                            ('live_source_sha256', 'evaluation_live.py')]:
            current = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            if self.metadata[field] != current and self.metadata[field] not in previous_sources.get(field, set()):
                raise ValueError(f'Recorded evaluator differs from {name}; use the matching source revision')
            self.metadata['recorded_' + field] = self.metadata[field]
            self.metadata[field] = current
        self.geometry = GarmentGeometry.__new__(GarmentGeometry)
        for key, value in context['geometry'].items():
            setattr(self.geometry, key, np.asarray(value, dtype=int))
        for key, values in context['geometry_lists'].items():
            setattr(self.geometry, key, [np.asarray(value, dtype=int) for value in values])
        self.geometry.coverage_samples = context['coverage_samples']
        for key, value in context['arrays'].items():
            setattr(self, key, np.asarray(value, dtype=float))
        for key, value in context['thresholds'].items():
            setattr(self, key, value)
        self.arms = {side: np.asarray(chain, dtype=float) for side, chain in context['arms'].items()}
        self.grasp_links = metadata['grasp_link_indices']
        self.pickup_references, self.pickup_diagnostics = {}, []
        self.values = None
        self.contact_context = context['contact']
        self.contact_detector = None
        self.metadata.update(contact_criterion=self.contact_context['criterion'], native_physx_contact_event=False,
                             contact_limitations=self.contact_context['limitations'],
                             contact_source_sha256=hashlib.sha256(Path(__file__).with_name('evaluation_contact.py').read_bytes()).hexdigest(),
                             timing_revision='short-sleeve-contact-clock-v3')

    def contact(self, points):
        if self.contact_detector is None:
            self.contact_detector = CollisionContact(self.contact_context, self.values['static_Human'])
        return self.contact_detector.touches(points)

    def physical_sample(self):
        values = self.values
        points = values['g0_positions']
        if not np.isfinite(points).all():
            raise ValueError('Nonfinite recorded garment state')
        health, anchors = [], []
        for i, link in enumerate(self.grasp_links):
            prefix = f'r{i}_'
            cloth = int(values[prefix + 'grab_cloth'])
            attached = (cloth >= 0 and bool(values[prefix + 'attachment_present'])
                        and bool(values[prefix + 'anchor_data_present']))
            if not attached:
                health.append({'attached': False, 'anchor_p95_error_m': None})
                anchors.append((-1, np.array([], dtype=int)))
                continue
            if cloth != 0:
                raise ValueError('Replay evaluation requires exactly one garment')
            mask = values[prefix + 'anchor_mask'].astype(bool)
            ids = values[prefix + 'grab_indices'].astype(int)[mask]
            local = values[prefix + 'anchor_local_offsets'][mask]
            tf = values[prefix + 'links'][link]
            expected = tf[:3] + local @ rotation(np.r_[tf[6], tf[3:6]]).T
            error = np.linalg.norm(points[ids] - expected, axis=1)
            if not len(ids):
                raise ValueError('Recorded attachment has no anchors')
            health.append({'attached': True, 'anchor_count': len(ids),
                           'anchor_p95_error_m': float(np.quantile(error, .95))})
            anchors.append((cloth, ids))
        return self.physical_from_state(points, health, anchors)


class ReplayEvaluation:
    """Consume every archive frame, score a selected continuous tick interval.

    Tick bounds are inclusive. At the start tick the last state boundary wins,
    so a range may start immediately after a reset. A reset INSIDE an attempt
    invalidates it, exactly as in live evaluation.
    """
    def __init__(self, metadata, output, start_tick=0, end_tick=None, contact_context=None):
        if metadata.get('evaluation_state_version') != 1:
            raise ValueError('This older recording lacks native attachment evidence and evaluation landmarks. '
                             'Exact replay scoring requires a new --full-record 1 recording; '
                             'ordinary replay of old recordings is still supported.')
        if start_tick < 0 or (end_tick is not None and end_tick <= start_tick):
            raise ValueError('Evaluation requires 0 <= start_tick < end_tick')
        self.metadata, self.output = metadata, output
        self.start_tick, self.end_tick = start_tick, end_tick
        self.dt = metadata['physics_dt_s']
        self.context, self.initial, self.session = None, None, None
        self.last_tick, self.finished = start_tick, False
        self.human = None
        self.fallback_contact_context = contact_context

    def consume(self, header, values):
        if self.finished:
            return
        tick = header['tick']
        if 'evaluation_context' in values:
            self.context = json.loads(str(values['evaluation_context']))
            if 'contact' not in self.context and self.fallback_contact_context is not None:
                self.context['contact'] = self.fallback_contact_context
        if tick < self.start_tick:
            return
        if self.end_tick is not None and tick > self.end_tick:
            return
        if tick == self.start_tick and self.session is None:
            self.initial = values
            return
        if self.initial is None:
            raise ValueError('Requested evaluation start tick is absent')
        if self.session is None:
            measurements = ReplayMeasurements(self.context, self.metadata)
            measurements.values = self.initial
            self.human = self.initial['static_Human'].copy()
            backend = SimpleNamespace(world=SimpleNamespace(get_physics_dt=lambda: self.dt))
            self.session = EvaluationSession(backend, [], [], None, self.output)
            self.session.start({'mode': 'replay_state', 'physics_resimulated': False,
                                'recording_start_tick': self.start_tick},
                               measurements=measurements, subscribe=False)
        if header['kind'].startswith(('before_', 'after_')):
            self.session.finish(reason='recorded_reset_or_load', valid=False, take_final=False)
            raise ValueError(f'Reset/load at tick {tick} invalidates this attempt; select a continuous '
                             'interval with --start-tick and --end-tick (replay: --evaluation-…-tick)')
        if not np.array_equal(self.human, values['static_Human']):
            self.session.finish(reason='mannequin_changed_without_boundary', valid=False, take_final=False)
            raise ValueError('Recorded mannequin changed within an evaluation attempt')
        self.session.measurements.values = values
        if header['kind'] == 'physics':
            if tick != self.last_tick + 1:
                raise ValueError('Missing physics tick during replay evaluation')
            self.session._physics_step(self.dt)
            self.last_tick = tick
            if not self.session.active:
                raise ValueError(f'Replay measurement failed: {self.session.last_report["reason"]}')

    def finish(self):
        if self.finished:
            return self.report
        if self.session is None or self.last_tick <= self.start_tick:
            raise ValueError('Selected interval contains fewer than two states')
        if self.end_tick is not None and self.last_tick != self.end_tick:
            self.session.finish(reason='requested_end_tick_missing', valid=False, take_final=False)
            raise ValueError('Recording ended before requested evaluation end tick')
        self.report = self.session.finish(reason='replay_interval_complete')
        self.finished = True
        if not self.report['valid']:
            raise ValueError(self.report['reason'])
        return self.report
