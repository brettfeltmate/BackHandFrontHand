# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import os
import sys



import klibs
from klibs import P
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLUserInterface import any_key, ui_request
from klibs.KLCommunication import message
from klibs.KLUtilities import hide_mouse_cursor, now
from random import shuffle, randrange

import datatable as dt

#from ExpAssets import *
from OptiTracker import OptiTracker 

# i hate typos
LEFT   	   = "Left"
RIGHT  	   = "Right"
CENTRE 	   = "Centre"
FRONT  	   = "Front"
BACK   	   = "Back"
TARGET 	   = "Target"
DISTRACTOR = "Distractor"

# colours
WHITE = [255, 255, 255, 255]
GRUE  = [90, 90, 96, 255]

# sizing constants
PLACEHOLDER_SIZE_CM   = 4
PLACEHOLDER_BRIM_CM   = 1
PLACEHOLDER_OFFSET_CM = 10

# trial reveal timing
TRIAL_REVEAL = (1000, 2000)


class BackHandFrontHand(klibs.Experiment):

	def setup(self):
		px_cm = round(P.ppi / 2.54)

		holder_offset = px_cm * PLACEHOLDER_OFFSET_CM 	# centre-to-centre
		holder_px 	  = px_cm * PLACEHOLDER_SIZE_CM	
		holder_brim   = px_cm * PLACEHOLDER_BRIM_CM   	
		holder_diam	  = holder_px + holder_brim			

		self.locs = {
			LEFT:  (P.screen_c[0] - holder_offset, P.screen_c[1]),
			CENTRE: P.screen_c,
			RIGHT: (P.screen_c[0] + holder_offset, P.screen_c[1])
		}


		self.placeholders = {
			TARGET:     kld.Annulus(holder_diam, holder_brim, fill=WHITE),
			DISTRACTOR: kld.Annulus(holder_brim, holder_brim, fill=GRUE)
		}

		self.task_sequence = [
			# which side, of which hand, is to be used
			[BACK, LEFT], [BACK, RIGHT], 
			[FRONT, LEFT], [FRONT, RIGHT]
		]

		shuffle(self.task_sequence)

		self.opti = OptiTracker()
		
		self.optidata = {
			"Prefix": 		   dt.Frame(),
			"MarkerSets": 	   dt.Frame(),
			"LegacyMarkerSet": dt.Frame(),
			"RigidBodies": 	   dt.Frame(),
			"Skeletons": 	   dt.Frame(),
			"AssetMarkers":    dt.Frame()
		}




	def block(self):
		self.hand_side, self.hand_used = self.task_sequence.pop()

		instructions = f"(Full Instrux TBD)\n Knockover targets with the {self.hand_side} of your {self.hand_used} hand."
		instructions += "\n\nPress any key to begin."

		if P.practicing:
			instructions += "\n\n(practice block)"

		fill()
		message(instructions, location=P.screen_c)
		flip()

		any_key()

	def setup_response_collector(self):
		pass

	def trial_prep(self):
		# extract trial setup
		self.target, self.distractor = self.arrangement.split('_')

		self.target_loc, _     = self.target.split('-')
		self.distractor_loc, _ = self.distractor.split('-')


		# induce slight uncertainty in the reveal time
		self.evm.add_event("reveal", randrange(*TRIAL_REVEAL))

		# TODO: occulude vision via plato

		# setup phase
		self.present_arrangment(trial_prep=True)
		any_key()

		# "uncued" phase
		self.present_arrangment()

		# begin tracking
		self.opti.start()


	def trial(self):
		hide_mouse_cursor()

		while self.evm.before("reveal"):
			ui_request()

		self.present_arrangment(flag_target=True)
		# TODO: open plato

		hide_mouse_cursor()
		trial_start = now()
		any_key()
		self.opti.stop()



		return {
			"block_num":      P.block_number,
			"trial_num": 	  P.trial_number,
			"practicing": 	  P.practicing,
			"hand_used":  	  self.hand_used,
			"hand_side":      self.hand_used,
			"target_loc": 	  self.target_loc,
			"distractor_loc": self.distractor_loc,
			"movement_time":  "NA",
			"response_time":  now() - trial_start,
			"correct":        "NA"
		}

	def trial_clean_up(self):
		trial_frames = self.opti.export()

		for asset in trial_frames.keys():
			frame = trial_frames[asset]
			frame[:, 
			   dt.update(
					block_num	   = P.block_number, 
					trial_num	   = P.trial_number, 
					hand_side 	   = self.hand_side, 
					hand_used 	   = self.hand_used, 
					target_loc	   = self.target_loc, 
					distractor_loc = self.distractor_loc
			)]

			self.optidata[asset] = dt.rbind(self.optidata[asset], frame)

	def clean_up(self):
		for asset_type in self.optidata.keys():
			self.optidata[asset_type].to_csv(f"{P.p_id}_{asset_type}.csv")


	def present_arrangment(self, trial_prep = False, flag_target = False):
		fill()

		blit(self.placeholders[DISTRACTOR], registration = 5, location = self.locs[self.distractor_loc])

		if flag_target:
			blit(self.placeholders[TARGET], registration = 5, location = self.locs[self.target_loc])

		else:
			blit(self.placeholders[DISTRACTOR], registration = 5, location = self.locs[self.target_loc])
			if trial_prep:
				message(
					"Place objects in placeholders.\nAny key to start.\nFor now, any key to end.",
					location     = [P.screen_c[0]//3, P.screen_c[1]//3], 
					registration = 1
				)

		flip()
