# -*- coding: utf-8 -*-

__author__ = 'Brett Feltmate'

import klibs
from klibs import P
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, blit, flip
from klibs.KLUserInterface import any_key, key_pressed, ui_request
from klibs.KLCommunication import message
from klibs.KLUtilities import hide_mouse_cursor, pump
from klibs.KLTime import Stopwatch, CountDown
from klibs.KLAudio import Tone

from random import shuffle

import os
import csv

# import datatable as dt
from pyfirmata import serial


# from ExpAssets import *
# from OptiTracker import OptiTracker
from natnetclient_rough import NatNetClient
from get_key_state import get_key_state

# i hate typos
LEFT = 'Left'
RIGHT = 'Right'
CENTRE = 'Centre'
FRONT = 'Front'
BACK = 'Back'
TARGET = 'Target'
DISTRACTOR = 'Distractor'

# colours
WHITE = [255, 255, 255, 255]
GRUE = [90, 90, 96, 255]

# sizing constants
PLACEHOLDER_SIZE_CM = 4
PLACEHOLDER_BRIM_CM = 1
PLACEHOLDER_OFFSET_CM = 15

# timing constants
GO_SIGNAL_ONSET = 300
RESPONSE_TIMEOUT = 2000

# audio constants
TONE_DURATION = 50
TONE_SHAPE = 'sine'
TONE_FREQ = 784  # ridin' on yo G5 airplane
TONE_VOLUME = 0.5


class BackHandFrontHand(klibs.Experiment):
    def setup(self):

        PX_CM = round(P.ppi / 2.54)

        OFFSET = PX_CM * PLACEHOLDER_OFFSET_CM  # centre-to-centre
        HOLDER_PX = PX_CM * PLACEHOLDER_SIZE_CM
        BRIM_PX = PX_CM * PLACEHOLDER_BRIM_CM
        DIAM_PX = HOLDER_PX + BRIM_PX

        self.locs = {
            LEFT: (P.screen_c[0] - OFFSET, P.screen_c[1]),
            CENTRE: P.screen_c,
            RIGHT: (P.screen_c[0] + OFFSET, P.screen_c[1]),
        }

        self.placeholders = {
            TARGET: kld.Annulus(DIAM_PX, BRIM_PX, fill=WHITE),
            DISTRACTOR: kld.Annulus(DIAM_PX, BRIM_PX, fill=GRUE),
        }

        self.go_signal = Tone(
            TONE_DURATION, TONE_SHAPE, TONE_FREQ, TONE_VOLUME
        )

        self.task_sequence = [
            # which side, of which hand, is to be used
            [BACK, LEFT],
            [BACK, RIGHT],
            [FRONT, LEFT],
            [FRONT, RIGHT],
        ]

        shuffle(self.task_sequence)

        if P.run_practice_blocks:
            self.insert_practice_block(
                [1, 3, 5, 7], trial_counts=P.trials_per_practice_block
            )
            self.task_sequence = [
                block for block in self.task_sequence for _ in range(2)
            ]
        self.nnc = NatNetClient()
        self.nnc.markers_listener = self.marker_set_listener
        self.nnc.rigid_bodies_listener = self.rigid_bodies_listener

        self.board = serial.Serial(port='COM6', baudrate=9600)

        if not os.path.exists('OptiData'):
            os.mkdir('OptiData')

        self.pid_dir = f'OptiData/P{P.p_id}'
        os.mkdir(self.pid_dir)

    def block(self):
        self.board.write(b'55')

        self.hand_side, self.hand_used = self.task_sequence.pop()

        self.block_dir = self.pid_dir
        if P.practicing:
            self.block_dir += '/practice'
        else:
            self.block_dir += '/testing'

        if not os.path.exists(self.block_dir):
            os.mkdir(self.block_dir)

        self.block_dir += (
            f'/Block{P.block_number}_{self.hand_side}_{self.hand_used}'
        )

        if not os.path.exists(self.block_dir):
            os.mkdir(self.block_dir)

        instructions = 'Block Instructions:\n\n'
        instructions += f'Tipover targets (lit-up dowel) with the {self.hand_side} of your {self.hand_used} hand.'

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
        # shut goggles
        self.board.write(b'56')
        # extract trial setup
        self.target, self.distractor = self.arrangement.split('_')

        self.target_loc, _ = self.target.split('-')
        self.distractor_loc, _ = self.distractor.split('-')

        # induce slight uncertainty in the reveal time
        # self.evm.add_event(label="go_signal", onset=GO_SIGNAL_ONSET)
        self.evm.add_event(label='response_timeout', onset=RESPONSE_TIMEOUT)

        # TODO: close plato

        # setup phase
        self.present_arrangment(phase='setup')

        while True:
            q = pump(True)
            if key_pressed(key='space', queue=q):
                break

    def trial(self):
        self.nnc.startup()

        self.present_arrangment()

        go_signal_delay = CountDown(0.3)

        while go_signal_delay.counting():
            ui_request()

        # open goggles
        self.board.write(b'55')
        hide_mouse_cursor()

        reaction_timer = Stopwatch(start=True)
        self.go_signal.play()

        rt = 'NA'
        while self.evm.before('response_timeout'):
            if get_key_state('space') == 0 and rt == 'NA':
                rt = reaction_timer.elapsed() / 1000

        # Stop polling opt data
        self.nnc.shutdown()

        return {
            'block_num': P.block_number,
            'trial_num': P.trial_number,
            'practicing': P.practicing,
            'left_right_hand': self.hand_used,
            'palm_back_hand': self.hand_side,
            'target_loc': self.target_loc,
            'distractor_loc': self.distractor_loc,
            'response_time': rt,
        }

    def trial_clean_up(self):
        pass

    def clean_up(self):
        pass

    def present_arrangment(self, phase='trial'):
        fill()

        blit(
            self.placeholders[DISTRACTOR],
            registration=5,
            location=self.locs[self.distractor_loc],
        )

        blit(
            self.placeholders[TARGET if phase == 'trial' else DISTRACTOR],
            registration=5,
            location=self.locs[self.target_loc],
        )

        flip()

    def get_trial_properties(self):
        return {
            'trial_num': P.trial_number,
            'block_num': P.block_number,
            'practicing': P.practicing,
            'left_right_hand': self.hand_used,
            'palm_back_hand': self.hand_side,
            'target_loc': self.target_loc,
            'distractor_loc': self.distractor_loc,
            'participant_id': P.participant_id,
        }

    def rigid_bodies_listener(self, rigid_body):
        trial_details = self.get_trial_properties()

        fname = (
            f'{self.block_dir}/P{P.p_id}_T{P.trial_number}_rigidbody_data.csv'
        )

        file_exists = os.path.exists(fname)

        rigid_body.update(trial_details)

        with open(fname, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=rigid_body.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(rigid_body)

    def marker_set_listener(self, marker_set):
        trial_details = self.get_trial_properties()

        fname = f"{self.block_dir}/P{P.p_id}_T{P.trial_number}_{marker_set['label']}_markerset_data.csv"

        file_exists = os.path.exists(fname)

        with open(fname, 'a', newline='') as csvfile:
            for marker in marker_set['markers']:
                marker.update(trial_details)

                writer = csv.DictWriter(csvfile, fieldnames=marker.keys())

                if not file_exists:
                    writer.writeheader()

                writer.writerow(marker)
