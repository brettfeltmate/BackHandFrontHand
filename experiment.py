# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import klibs
from klibs import P
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLUserInterface import any_key, ui_request
from klibs.KLCommunication import message
from klibs.KLUtilities import hide_mouse_cursor, now
from random import shuffle

from datatable import Frame, rbind, update, to_csv

from ExpAssets.Resources.code.OptiTracker import OptiTracker

LEFT = "Left"
RIGHT = "Right"
CENTRE = "Centre"
TARGET = "Target"
DISTRACTOR = "Distractor"
LEFT_TARGET = "LeftTarget"
RIGHT_TARGET = "RightTarget"
CENTRE_TARGET = "CentreTarget"
LEFT_DISTRACTOR = "LeftDistractor"
RIGHT_DISTRACTOR = "RightDistractor"
CENTRE_DISTRACTOR = "CentreDistractor"
LEFTHAND = "LeftHand"
RIGHTHAND = "RightHand"
FOREHAND = "Forehand"
BACKHAND = "Backhand"

class BackHandFrontHand(klibs.Experiment):

	def setup(self):
		self.opti = OptiTracker()
		self.optidata = {
			"Prefix": Frame(),
			"MarkerSets": Frame(),
			"LegacyMarkerSet": Frame(),
			"RigidBodies": Frame(),
			"Skeletons": Frame(),
			"AssetMarkers": Frame()
		}

		px_cm = round(P.ppi / 2.54)
		placeholder_cm = 4

		placeholder_px = px_cm * placeholder_cm
		self.offset = 10 * px_cm  # Placeholders offset 12cm center-to-center, centered on screen center
		brimwidth = px_cm    # Objects encircled by a brim 1cm wide
		diam = placeholder_px + brimwidth

		self.locs = {
			LEFT: (P.screen_c[0] - self.offset, P.screen_c[1]),
			CENTRE: P.screen_c,
			RIGHT: (P.screen_c[0] + self.offset, P.screen_c[1])
		}

		self.fills = {
			TARGET: [255, 255, 255, 255],     # White
			DISTRACTOR: [90, 90, 96, 255]     # Darkgray
		}

		self.placeholders = {
			TARGET: kld.Annulus(diam, brimwidth, fill=self.fills[TARGET]),
			DISTRACTOR: kld.Annulus(diam, brimwidth, fill=self.fills[DISTRACTOR])
		}

		self.task_sequence = [
			[BACKHAND, LEFTHAND], 
			[BACKHAND, RIGHTHAND], 
			[FOREHAND, LEFTHAND], 
			[FOREHAND, RIGHTHAND]
		]

		shuffle(self.task_sequence)

	def block(self):
		self.block_task, self.block_hand = self.task_sequence.pop()

		msg = f"(Full Instrux TBD)\n Slap targets with the {self.block_task} of your {self.block_hand}.\nAny Key to start block."
		fill()
		message(msg, location=P.screen_c)
		flip()

		any_key()

	def setup_response_collector(self):
		pass

	def trial_prep(self):
		self.target_loc, self.distractor_loc = self.arrangement.split('_')
		self.present_arrangment(trial_prep=True)
		any_key()
		clear()
		self.present_arrangment()
		self.opti.start()


	def trial(self):
		hide_mouse_cursor()
		trial_start = now()
		any_key()
		self.opti.stop()
		trial_frames = self.opti.export()
		for asset_type in trial_frames.keys():
			asset_frame = trial_frames[asset_type]
			asset_frame[:, update(
				block_num=P.block_number, 
				trial_num=P.trial_number, 
				block_task=self.block_task, 
				block_hand=self.block_hand, 
				target_loc=self.target_loc, 
				distractor_loc=self.distractor_loc
			)]

			self.optidata[asset_type] = rbind(self.optidata[asset_type], asset_frame)


		return {
			"block_num": P.block_number,
			"trial_num": P.trial_number,
			"practicing": P.practicing,
			"block_task": self.block_task,
			"block_hand": self.block_hand,
			"target_loc": self.target_loc,
			"distractor_loc": self.distractor_loc,
			"movement_time": "NA",
			"response_time": now() - trial_start,
			"correct": "NA"
		}

	def trial_clean_up(self):
		pass

	def clean_up(self):
		for asset_type in self.optidata.keys():
			self.optidata[asset_type].to_csv(f"{P.subj_id}_{asset_type}.csv")


	def present_arrangment(self, trial_prep = False):
		fill()
		self.target_side, _ = self.target_loc.split('-')
		self.distractor_side, _ = self.distractor_loc.split('-')
		blit(self.placeholders[TARGET], registration=5, location=self.locs[self.target_side])
		blit(self.placeholders[DISTRACTOR], registration=5, location=self.locs[self.distractor_side])
		if trial_prep:
			msg = f"Place the target in the {self.target_side} circle.\nPress any key to start trial.\nFor now, press any key to end trial as well."
			message(msg, location=[P.screen_c[0] - self.offset, P.screen_c[1]//4], registration=1)
		flip()