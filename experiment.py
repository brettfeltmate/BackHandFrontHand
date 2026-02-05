# -*- coding: utf-8 -*-

__author__ = 'Brett Feltmate'

import klibs
from klibs import P

from klibs.KLConstants import STROKE_CENTER
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, flip
from klibs.KLUserInterface import smart_sleep, any_key, hide_mouse_cursor
from klibs.KLCommunication import message
from klibs.KLAudio import Tone
from klibs.KLExceptions import TrialException

from klibs.KLBoundary import BoundarySet, CircleBoundary

from natnetclient_rough import NatNetClient  # type: ignore[import]
from OptiTracker import OptiTracker  # type: ignore[import]
from pyfirmata import serial  # type: ignore[import]

from get_key_state import get_key_state  # type: ignore[import]

from csv import DictWriter
from random import shuffle, choice
from datetime import datetime
import os

# import datatable as dt

LEFT = 'Left'
RIGHT = 'Right'
CENTRE = 'Centre'
TOP = 'Top'
FRONT = 'Front'
BACK = 'Back'
TARGET = 'Target'
DISTRACTOR = 'Distractor'
READY = 'Ready'
POS_X = 'pos_x'
POS_Y = 'pos_y'
POS_Z = 'pos_z'
SPACE = 'space'
PREMATURE_REACH = 'Premature reach'
REACH_TIMEOUT = 'Reach timeout'
NA = 'NA'

WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)
GRUE = (90, 90, 96, 255)
ORANGE = (165, 115, 112, 255)


class BackHandFrontHand(klibs.Experiment):
    def setup(self):
        self.px_cm = round(P.ppi / 2.54)

        offset = self.px_cm * P.placeholder_offset_cm  # type: ignore
        holder_px = self.px_cm * P.placeholder_size_cm   # type: ignore
        brim_px = self.px_cm * P.placeholder_brim_cm   # type: ignore
        diam_px = holder_px + brim_px

        # for working with streamed motion capture data
        self.ot = OptiTracker(marker_count=10, sample_rate=120, window_size=5)

        # manages stream
        self.nnc = NatNetClient()

        # what to do with incoming data
        self.nnc.markers_listener = self._marker_set_listener

        # plato goggles controller
        self.goggles = PlatoGoggles(comport=P.arduino_comport, baudrate=P.baudrate)  # type: ignore

        self.locs = {
            LEFT: (P.screen_c[0] - offset, P.screen_c[1]),
            CENTRE: P.screen_c,
            RIGHT: (P.screen_c[0] + offset, P.screen_c[1]),
        }

        self.placeholders = {
            TARGET: kld.Annulus(diam_px, brim_px, fill=WHITE),
            DISTRACTOR: kld.Annulus(diam_px, brim_px, fill=GRUE),
        }

        if P.development_mode:
            self.cursor = kld.Annulus(
                self.px_cm * 2,
                self.px_cm // 5,
                stroke=[self.px_cm // 10, ORANGE, STROKE_CENTER],
                fill=ORANGE,
            )

        self.go_signal = Tone(
            P.tone_duration, P.tone_shape, P.tone_freq, P.tone_volume  # type: ignore
        )

        sides = [BACK, FRONT]
        shuffle(sides)

        self.task_sequence = [[hand, side] for hand in hands for side in sides]

        if P.run_practice_blocks:
            self.insert_practice_block(
                [1, 3, 5, 7], trial_counts=P.trials_per_practice_block  # type: ignore
            )
            self.task_sequence = [
                block for block in self.task_sequence for _ in range(2)
            ]

        self._ensure_dir_exists(P.opti_data_dir)  # type: ignore[known-attribute]
        participant_dir = self._get_participant_base_dir()
        self._ensure_dir_exists(participant_dir)
        self._ensure_dir_exists(os.path.join(participant_dir, 'testing'))

        if P.run_practice_blocks:
            self._ensure_dir_exists(os.path.join(participant_dir, 'practice'))

    def block(self):
        self.goggles.open()
        try:
            self.hand_used, self.side_used = self.task_sequence[
                P.block_number - 1
            ]
        except IndexError:
            raise IndexError(
                f'Block number {P.block_number} exceeds defined task sequence length of {len(self.task_sequence)}.'
            )

        self.participant_dir = self._get_participant_base_dir()
        self.block_dir = self._get_block_dir_path()

        instructions = 'Block Instructions:\n\n'
        instructions += f'Tipover targets (lit-up dowel) with the {self.side_used} of your {self.hand_used} hand.'

        if P.practicing:
            instructions += '\n\n[PRACTICE BLOCK] Press space to begin. Note: Goggles will close'
        else:
            instructions += '\n\n[TESTING BLOCK]  Press space to begin. Note: Goggles will close'

        fill()
        message(instructions, location=P.screen_c)
        flip()

        any_key()

    def setup_response_collector(self):
        pass

    def trial_prep(self):
        self.goggles.close()

        self.trial_deets = self._get_trial_info()

        self.target_loc = self.trial_deets.get('target_loc')
        self.distractor_loc = self.trial_deets.get('distractor_loc')

        self.bounds = BoundarySet(
            boundaries=[
                CircleBoundary(
                    TARGET,
                    self.trial_deets.get('target_loc'),
                    P.boundary_radius_cm * self.px_cm,  # type: ignore[attr]
                ),
                CircleBoundary(
                    DISTRACTOR,
                    self.trial_deets.get('distractor_loc'),
                    P.boundary_radius_cm * self.px_cm,  # type: ignore[attr]
                ),
            ]
        )

        self.evm.add_event(
            label='go_signal', onset=self.trial_deets.get('go_signal_onset')
        )
        self.evm.add_event(
            label='response_timeout',
            onset=P.response_timeout,
            after='go_signal',
        )

        self.draw(prep=True)

        while True:
            q = pump(True)
            if key_pressed(key='space', queue=q):
                break

        self.ot.data_dir = self._get_trial_filename(
            self.block_dir,
            P.p_id,
            P.block_number,
            P.trial_number,
        )

        self.nnc.startup()  # start marker tracking

        # ensure some data exists before beginning trial
        smart_sleep(P.opti_trial_lead_time)  # type: ignore[known-attribute]

        self._validate_trial_data_file(self.ot.data_dir)

        self.draw()

        self.plato.open()

    def trial(self):
        hide_mouse_cursor()

        rt = None
        obj_tipped = None

        while self.evm.before('go_signal'):

            if get_key_state('space') == 0:
                if get_key_state('space') == 0:
                    self._abort_trial(PREMATURE_REACH)

        go_signal_onset = self.evm.trial_time_ms()
        self.go_signal.play()

        while self.evm.before('response_timeout') and obj_tipped is None:
            if get_key_state('space') == 0:
                rt = self.evm.trial_time_ms() - go_signal_onset

            hand_pos = self._get_hand_pos()

            obj_tipped = self.bounds.which_boundary(hand_pos)

        if obj_tipped is None:
            self._abort_trial(REACH_TIMEOUT)

        self.nnc.shutdown()

        return {
            'block_num': P.block_number,
            'trial_num': P.trial_number,
            'hand_used': self.task_deets.get('hand_used'),
            'side_used': self.task_deets.get('side_used'),
            'target_loc': self.task_deets.get('target_loc'),
            'distractor_loc': self.task_deets.get('distractor_loc'),
            'response_time': rt,
            'object_tipped': obj_tipped,
        }

    def trial_clean_up(self):
        clear()

    def clean_up(self):
        clear()

        fill()
        message(
            'Experiment completed; Press any key to quit to desktop',
            location = P.screen_c,
            registration = 5,
            blit_txt = True
        )
        flip()

        any_key()

    def draw(self, prep: bool = False) -> None:  # type: ignore[unused-argument]
        fill()

        if prep:
            message(
                'Place objects in rings.\nWhen ready, instruct participant to press and hold spacebar.',
                location = (P.screen_c[0], P.screen_y // 4)
                registration = 3,
                blit_txt = True
            )

        for obj in [DISTRACTOR, TARGET]:
            blit(
                self.placeholders[obj],
                registraction = 5,
                location = self.locs[obj]
            )

        flip()

    def _get_hand_pos(self):
        hand_marker = self.ot.position()

        hand_pos = {
            axis: markers[axis][0].item() * self.px_cm
            for axis in (POS_X, POS_Y, POS_Z)
        }
        return self._translate_pos(hand_pos)

    def _translate_pos(self, pos):
        return (P.screen_x - pos[POS_X], P.screen_y - pos[POS_Z])

    def _abort_trial(self, err=''):
        msgs = {
            PREMATURE_REACH: 'Please wait for the go signal.',
            REACH_TIMEOUT: 'Too slow!',
        }

        self.goggles.open()

        self.nnc.shutdown()

        os.remove(self.ot.data_dir)

        fill()
        message(
            msgs.get(err, 'Unknown error'), location=P.screen_c, blit_txt=True
        )
        flip()

        smart_sleep(1000)

        raise TrialException(err)

    def _marker_set_listener(self, marker_set: dict) -> None:
        """Write marker set data to CSV file.

        Args:
            marker_set (dict): Dictionary containing marker data to be written.
                Expected format: {'markers': [{'key1': val1, ...}, ...]}
        """

        if marker_set.get('label') in P.hand_markerset_labels:  # type: ignore[known-attribute]
            # Append data to trial-specific CSV file
            fname = self.ot.data_dir
            header = list(marker_set['markers'][0].keys())

            # if file doesn't exist, create it and write header
            if not os.path.exists(fname):
                with open(fname, 'w', newline='') as file:
                    writer = DictWriter(file, fieldnames=header)
                    writer.writeheader()

            # append marker data to file
            with open(fname, 'a', newline='') as file:
                writer = DictWriter(file, fieldnames=header)
                for marker in marker_set.get('markers', None):  # type: ignore[iterable]
                    if marker is not None:
                        writer.writerow(marker)

    def _ensure_dir_exists(self, path):
        """Create directory if it doesn't exist. Raises exception on failure."""
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create directory '{path}': {e}")

    def _get_participant_base_dir(self):
        """Get base directory path for current participant."""
        if P.development_mode:
            # Use 999 with datetime suffix for unique dev directories
            datetime_suffix = datetime.now().strftime('%m%d_%H%M')
            p_id = f'DEV_{datetime_suffix}'
        else:
            p_id = str(P.p_id)
        return os.path.join(
            P.opti_data_dir, p_id  # type: ignore[known-attribute]
        )

    def _get_block_dir_path(self):
        """Construct block directory path."""
        phase = 'practice' if P.practicing else 'testing'
        return os.path.join(
            self.participant_dir, phase, self.hand_used, self.side_used
        )

    def _get_trial_filename(
        self,
        block_dir,
        participant_id,
        block_num,
        trial_num,
    ):
        """Construct trial data filename."""
        filename = (
            f'P{participant_id}_B{block_num:02d}_T{trial_num:03d}_OptiData.txt'
        )
        return os.path.join(block_dir, filename)

    def _get_trial_info(self):
        """Collate trial information"""
        target, distractor = self.arrangement.split('_')  # type: ignore[access-attribute]
        target_loc, _ = target.split('-')
        distractor_loc, _ = distractor.split('-')
        go_signal_onset = choice(P.go_signal_onset)  # type: ignore[known-attribute]

        return {
            'participant': P.p_id,
            'block_num': P.block_number,
            'trial_num': P.trial_number,
            'practicing': P.practicing,
            'hand_used': self.hand_used,
            'side_used': self.side_used,
            'target_loc': target_loc,
            'distractor_loc': distractor_loc,
            'go_signal_onset': go_signal_onset,
        }

    def _add_trial_header_info(self, filepath, trial_info):
        """Markup file with trial details"""

        header_lines = []
        header_lines.append(f'#Participant ID: {P.p_id}')
        for key, value in trial_info.items():
            header_lines.append(f'#{key.replace("_", " ").title()}: {value}')
        header_lines.append(
            f"#Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        header_lines.append('#----------------------------------------')

        try:
            with open(filepath, 'r+') as f:
                content = f.read()
                f.seek(0, 0)
                f.writelines('\n'.join(header_lines) + '\n' + content)
        except IOError as e:
            raise IOError(
                f'Cannot write header to trial data file: {filepath} - {e}'
            )

    def _validate_trial_data_file(self, filepath):
        """Validate that trial data file exists and contains data. Raises exception if not."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f'Trial data file does not exist: {filepath}'
            )

        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                # Should have at least header + some data lines
                if len(lines) < 6:
                    raise ValueError(
                        f'OptiData file at \n\t{filepath}\nis sparser than expected, with only {len(lines)} lines.'
                    )
        except IOError as e:
            raise IOError(f'Cannot read trial data file: {filepath} - {e}')


class PlatoGoggles:
    def __init__(self, comport: str, baudrate: int):
        self.serial_conn = serial.Serial(port=comport, baudrate=baudrate)

    def open(self):
        self.serial_conn.write(P.plato_open_cmd)  # type: ignore

    def close(self):
        self.serial_conn.write(P.plato_close_cmd)  # type: ignore
