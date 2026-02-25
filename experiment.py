# -*- coding: utf-8 -*-

__author__ = 'Brett Feltmate'

import klibs
from klibs import P

from klibs.KLConstants import STROKE_CENTER
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, flip, clear, blit
from klibs.KLUserInterface import smart_sleep, any_key, pump, key_pressed
from klibs.KLUtilities import hide_mouse_cursor
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
import os

# import datatable as dt

LEFT = 'left'
RIGHT = 'right'
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
        self.plato = PlatoGoggles(comport=P.arduino_comport, baudrate=P.baudrate)  # type: ignore

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

        hands = [LEFT, RIGHT] if P.condition == LEFT else [RIGHT, LEFT]  # type: ignore

        self.task_sequence = [[hand, side] for hand in hands for side in sides]

        if P.run_practice_blocks:
            self.insert_practice_block(
                [1, 3, 5, 7], trial_counts=P.trials_per_practice_block  # type: ignore
            )
            self.task_sequence = [
                block for block in self.task_sequence for _ in range(2)
            ]

        self.participant_dir = os.path.join(
            P.opti_data_dir,  # type: ignore[known-attribute]
            f'{P.p_id if not P.development_mode else "DEV"}',
        )

        if os.path.exists(self.participant_dir):
            if not P.development_mode:
                raise FileExistsError(
                    f'Participant directory already exists: {self.participant_dir}. Please check participant ID or remove existing directory.'
                )
            else:
                os.rmdir(self.participant_dir)

        os.makedirs(self.participant_dir)

    def block(self):
        self.plato.open()
        try:
            self.hand_used, self.side_used = self.task_sequence[
                P.block_number - 1
            ]
        except IndexError:
            raise IndexError(
                f'Block number {P.block_number} exceeds defined task sequence length of {len(self.task_sequence)}.'
            )

        self.block_opti_dir = os.path.join(
            self.participant_dir,
            'practice' if P.practicing else 'testing',
            f'Block_{P.block_number}_{self.hand_used}_{self.side_used}',
        )

        if os.path.exists(self.block_opti_dir):
            if not P.development_mode:
                raise FileExistsError(
                    f'Block directory already exists: {self.block_opti_dir}. Please check block number or remove existing directory.'
                )
            else:
                os.rmdir(self.block_opti_dir)

        os.makedirs(self.block_opti_dir)

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
        self.plato.close()

        self.trial_deets = self._get_trial_info()

        self.target_loc = self.locs[  # type: ignore[argument]
            self.trial_deets.get('target_loc')
        ]
        self.distractor_loc = self.locs[  # type: ignore[argument]
            self.trial_deets.get('distractor_loc')
        ]

        self.trial_opti_dir = os.path.join(
            self.block_opti_dir,
            f'Trial_{P.trial_number}_Target_{self.trial_deets.get("target_loc")}_Distractor_{self.trial_deets.get("distractor_loc")}',
        )

        self.ot.data_dir = self.trial_opti_dir
        # FIXME: KeyError: 'Right'
        # self.distractor_loc = self.locs[...

        self.bounds = BoundarySet(
            boundaries=[
                CircleBoundary(
                    TARGET,
                    self.target_loc,
                    P.boundary_radius_cm * self.px_cm,  # type: ignore[attr]
                ),
                CircleBoundary(
                    DISTRACTOR,
                    self.distractor_loc,
                    P.boundary_radius_cm * self.px_cm,  # type: ignore[attr]
                ),
            ]
        )

        self.evm.add_event(
            label='go_signal', onset=self.trial_deets.get('go_signal_onset')
        )
        self.evm.add_event(
            label='response_timeout',
            onset=P.response_timeout,  # type: ignore[known-attribute]
            after='go_signal',
        )

        self.draw(prep=True)

        while True:
            q = pump(True)
            if key_pressed(key='space', queue=q):
                break

        self.nnc.startup()  # start marker tracking

        # ensure some data exists before beginning trial
        smart_sleep(P.opti_trial_lead_time)  # type: ignore[known-attribute]

        self.draw()

        self.plato.open()

    def trial(self):
        hide_mouse_cursor()

        if not os.path.exists(self.ot.data_dir):
            raise FileNotFoundError(
                f'OptiTracker data directory not found: {self.ot.data_dir}. Check OptiTracker setup and trial preparation.'
            )

        rt = None
        obj_tipped = None

        while self.evm.before('go_signal'):

            if get_key_state('space') == 0:
                if get_key_state('space') == 0:
                    self._abort_trial(PREMATURE_REACH)

        go_signal_onset = self.evm.trial_time_ms
        self.go_signal.play()

        while self.evm.before('response_timeout') and obj_tipped is None:
            if get_key_state('space') == 0:
                rt = self.evm.trial_time_ms - go_signal_onset

            hand_pos = self._get_hand_pos()

            obj_tipped = self.bounds.which_boundary(hand_pos)

        if obj_tipped is None:
            self._abort_trial(REACH_TIMEOUT)

        self.nnc.shutdown()

        return {
            'block_num': P.block_number,
            'trial_num': P.trial_number,
            'hand_used': self.trial_deets.get('hand_used'),
            'side_used': self.trial_deets.get('side_used'),
            'go_signal_onset': self.trial_deets.get('go_signal_onset'),
            'target_loc': self.trial_deets.get('target_loc'),
            'distractor_loc': self.trial_deets.get('distractor_loc'),
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
            location=P.screen_c,
            registration=5,
            blit_txt=True,
        )
        flip()

        any_key()

    def draw(self, prep: bool = False) -> None:  # type: ignore[unused-argument]
        fill()

        if prep:
            message(
                'Place objects in rings.\nWhen ready, instruct participant to press and hold spacebar.',
                location=(P.screen_c[0], P.screen_y // 4),  # type: ignore[unsupported-operator]
                registration=3,
                blit_txt=True,
            )

        blit(
            self.placeholders[TARGET],
            registration=5,
            location=self.target_loc,
        )
        blit(
            self.placeholders[DISTRACTOR],
            registration=5,
            location=self.distractor_loc,
        )

        flip()

    def _get_hand_pos(self):
        markers = self.ot.position()

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

        self.plato.open()

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

        print(
            f'Markerset label: {marker_set.get("label")}'
        )  # Debug: print the label of the incoming marker set
        print(
            f'Hand used: {self.hand_used}'
        )  # Debug: print the label of the incoming marker set
        if marker_set.get('label') == self.hand_used:  # type: ignore[known-attribute]
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
            'go_signal_onset': go_signal_onset,
            'target_loc': target_loc,
            'distractor_loc': distractor_loc,
        }


class PlatoGoggles:
    def __init__(self, comport: str, baudrate: int):
        self.serial_conn = serial.Serial(port=comport, baudrate=baudrate)

    def open(self):
        self.serial_conn.write(P.plato_open_cmd)  # type: ignore

    def close(self):
        self.serial_conn.write(P.plato_close_cmd)  # type: ignore
