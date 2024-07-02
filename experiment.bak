# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

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

import datatable as dt
from pyfirmata import serial


# from ExpAssets import *
from OptiTracker import OptiTracker
from get_key_state import get_key_state

# i hate typos
LEFT = "Left"
RIGHT = "Right"
CENTRE = "Centre"
FRONT = "Front"
BACK = "Back"
TARGET = "Target"
DISTRACTOR = "Distractor"

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
TONE_SHAPE = "sine"
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

        self.go_signal = Tone(TONE_DURATION, TONE_SHAPE, TONE_FREQ, TONE_VOLUME)

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

        self.opti = OptiTracker()

        self.optidata = {
            "Prefix": dt.Frame(),
            "MarkerSets": dt.Frame(),
            "LegacyMarkerSets": dt.Frame(),
            "RigidBodies": dt.Frame(),
            "Skeletons": dt.Frame(),
            "AssetMarkers": dt.Frame(),
        }
        self.board = serial.Serial(port="COM6", baudrate=9600)

    def block(self):
        self.board.write(b"55")

        self.hand_side, self.hand_used = self.task_sequence.pop()

        instructions = "Block Instructions:\n\n"
        instructions += f"Tipover targets (lit-up dowel) with the {self.hand_side} of your {self.hand_used} hand."
        if P.practicing:
            instructions += (
                "\n\n[PRACTICE BLOCK] Press space to begin. Note: Goggles will close"
            )
        else:
            instructions += (
                "\n\n[TESTING BLOCK]  Press space to begin. Note: Goggles will close"
            )

        fill()
        message(instructions, location=P.screen_c)
        flip()

        any_key()

    def setup_response_collector(self):
        pass

    def trial_prep(self):
        # shut goggles
        self.board.write(b"56")
        # extract trial setup
        self.target, self.distractor = self.arrangement.split("_")

        self.target_loc, _ = self.target.split("-")
        self.distractor_loc, _ = self.distractor.split("-")

        # induce slight uncertainty in the reveal time
        # self.evm.add_event(label="go_signal", onset=GO_SIGNAL_ONSET)
        self.evm.add_event(label="response_timeout", onset=RESPONSE_TIMEOUT)

        # TODO: close plato

        # setup phase
        self.present_arrangment(phase="setup")

        while True:
            q = pump(True)
            if key_pressed(key="space", queue=q):
                break

        # Start polling from opti and begin trial
        self.opti.start_client()

    def trial(self):
        self.present_arrangment()
        # open goggles
        self.board.write(b"55")
        hide_mouse_cursor()

        # abort & recycle trial following prepotent responses
        # while self.evm.before("go_signal"):
        #     if get_key_state(key="space") == 0:
        #         fill()
        #         message(text="Please wait for the go-tone.", location=P.screen_c)
        #         flip()

        #         delay = CountDown(1)
        #         while delay.counting():
        #             ui_request()

        #         TrialException(msg="EarlyStart")
        #         FIX: errs claiming no 'go_signal' label present

        go_signal_delay = CountDown(0.3)

        while go_signal_delay.counting():
            ui_request()

        reaction_timer = Stopwatch(start=True)
        self.go_signal.play()

        rt = "NA"
        while self.evm.before("response_timeout"):
            if get_key_state("space") == 0 and rt == "NA":
                rt = reaction_timer.elapsed() / 1000

        # Stop polling opt data
        self.opti.stop_client()

        return {
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "practicing": P.practicing,
            "left_right_hand": self.hand_used,
            "palm_back_hand": self.hand_side,
            "target_loc": self.target_loc,
            "distractor_loc": self.distractor_loc,
            "response_time": rt,
        }

    def trial_clean_up(self):
        trial_frames = self.opti.export_frames()

        for asset in trial_frames.keys():
            frame = trial_frames[asset]
            frame[
                :,
                dt.update(
                    **{
                        "participant_id": P.p_id,
                        "practicing": P.practicing,
                        "block_num": P.block_number,
                        "trial_num": P.trial_number,
                        "left_right_hand": self.hand_side,
                        "palm_back_hand": self.hand_used,
                        "target_loc": self.target_loc,
                        "distractor_loc": self.distractor_loc,
                    }
                ),
            ]

            self.optidata[asset] = dt.rbind(self.optidata[asset], frame)

    def clean_up(self):
        for asset in self.optidata.keys():
            self.optidata[asset].to_csv(
                path=f"BackHandFrontHand_{asset}_framedata.csv", append=True
            )

    def present_arrangment(self, phase="trial"):
        fill()

        blit(
            self.placeholders[DISTRACTOR],
            registration=5,
            location=self.locs[self.distractor_loc],
        )


        blit(
            self.placeholders[TARGET if phase == "trial" else DISTRACTOR],
            registration=5,
            location=self.locs[self.target_loc],
        )

        flip()
