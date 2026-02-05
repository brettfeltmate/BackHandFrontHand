### Klibs Parameter overrides ###

#########################################
# Runtime Settings
#########################################
collect_demographics = True
manual_demographics_collection = False
manual_trial_generation = False
run_practice_blocks = True
multi_user = False
view_distance = (
    57  # in centimeters, 57cm = 1 deg of visual angle per cm of screen
)
allow_hidpi = True

#########################################
# Available Hardware
#########################################
eye_tracker_available = False
eye_tracking = False

#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (45, 45, 45, 255)
default_color = (255, 255, 255, 255)
default_font_size = 23
default_font_unit = 'px'
default_font_name = 'Hind-Medium'

#########################################
# EyeLink Settings
#########################################
manual_eyelink_setup = False
manual_eyelink_recording = False

saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

#########################################
# Experiment Structure
#########################################
multi_session_project = False
trials_per_block = 60
blocks_per_experiment = 4
table_defaults = {}
conditions = ['left', 'right']
default_condition = None

#########################################
# Development Mode Settings
#########################################
dm_auto_threshold = True
dm_trial_show_mouse = True
dm_ignore_local_overrides = False
dm_show_gaze_dot = True

#########################################
# Data Export Settings
#########################################
primary_table = 'trials'
unique_identifier = 'userhash'
exclude_data_cols = ['created']
append_info_cols = ['random_seed']
datafile_ext = '.txt'

#########################################
# PROJECT-SPECIFIC VARS
#########################################
trials_per_practice_block = 6

placeholder_size_cm = 4
boundary_radius_cm = 4
placeholder_brim_cm = 1
placeholder_offset_cm = 15

# timing constants
go_signal_onset = [300, 500, 700]
response_timeout = 2000

# audio constants
tone_duration = 50
tone_shape = 'sine'
tone_freq = 784  # ridin' on yo G5 airplane
tone_volume = 0.5

plato_open_cmd = b'55'
plato_close_cmd = b'56'
arduino_comport = 'COM6'
baudrate = 9600
hand_markerset_labels = ['Left', 'Right']
opti_trial_lead_time = 120
