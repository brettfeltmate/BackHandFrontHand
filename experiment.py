# -*- coding: utf-8 -*-

__author__ = "Brett Feltmate"

import os
import sys



import klibs
from klibs import P
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import fill, blit, flip, clear
from klibs.KLUserInterface import any_key, ui_request, key_pressed
from klibs.KLCommunication import message
from klibs.KLUtilities import hide_mouse_cursor, now
from klibs.KLAudio import Tone

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

# timing constants
GO_SIGNAL_ONSET = (1000, 2000)
RESPONSE_TIMEOUT = 2000

# audio constants
TONE_DURATION = 50
TONE_SHAPE    = "sine"
TONE_FREQ     = 784      # ridin' on yo G5 airplane
TONE_VOLUME   = 0.5


class BackHandFrontHand(klibs.Experiment):

	def setup(self):
		PX_CM = round(P.ppi / 2.54)

		OFFSET    = PX_CM * PLACEHOLDER_OFFSET_CM 	# centre-to-centre
		HOLDER_PX = PX_CM * PLACEHOLDER_SIZE_CM	
		BRIM_PX   = PX_CM * PLACEHOLDER_BRIM_CM   	
		DIAM_PX	  = HOLDER_PX + BRIM_PX			

		self.locs = {
			LEFT:  (P.screen_c[0] - OFFSET, P.screen_c[1]),
			CENTRE: P.screen_c,
			RIGHT: (P.screen_c[0] + OFFSET, P.screen_c[1])
		}


		self.placeholders = {
			TARGET:     kld.Annulus(DIAM_PX, BRIM_PX, fill=WHITE),
			DISTRACTOR: kld.Annulus(BRIM_PX, BRIM_PX, fill=GRUE)
		}

		self.go_signal = Tone(TONE_DURATION, TONE_SHAPE, TONE_FREQ, TONE_VOLUME)

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
		self.evm.add_event("go_signal", randrange(*GO_SIGNAL_ONSET))
		self.evm.add_event("response_timeout", RESPONSE_TIMEOUT, after = "go_signal")

		# TODO: close plato

		# setup phase
		self.present_arrangment(trial_prep=True)
		any_key()

		# "uncued" phase
		self.present_arrangment()

		# begin tracking
		self.opti.start()


	def trial(self):
		hide_mouse_cursor()
		
		self.present_arrangment(flag_target=True)

		# TODO: open plato

		while self.evm.before("go_signal"):
			# TODO: check for premptive movement
			ui_request()

		self.go_signal.play()

		trial_start = now()
		timeout_at = trial_start + (RESPONSE_TIMEOUT // 1000)

		responded = False
		while now() < timeout_at and not responded:
			responded = key_pressed()

		
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
			   dt.update(**{
				   	"participant_id" : P.p_id,
					"practicing"	 : P.practicing,
					"block_num"	   	 : P.block_number, 
					"trial_num"	     : P.trial_number, 
					"hand_side" 	 : self.hand_side, 
					"hand_used" 	 : self.hand_used, 
					"target_loc"	 : self.target_loc, 
					"distractor_loc" : self.distractor_loc
			   }
			)]

			self.optidata[asset] = dt.rbind(self.optidata[asset], frame)

	def clean_up(self):
		for asset in self.optidata.keys():
			self.optidata[asset].to_csv(path = f"BackHandFrontHand_{asset}_framedata.csv", append=True)


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
