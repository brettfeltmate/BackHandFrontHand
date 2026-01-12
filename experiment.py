# -*- coding: utf-8 -*-

__author__ = 'Brett Feltmate'

import klibs
from klibs import P


class BackHandFrontHand(klibs.Experiment):
    def setup(self):
        pass

    def block(self):
        pass

    def setup_response_collector(self):
        pass

    def trial_prep(self):
        pass

    def trial(self):

        return {
            'block_num': P.block_number,
            'trial_num': P.trial_number,
        }

    def trial_clean_up(self):
        pass

    def clean_up(self):
        pass

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
            p_id = f'999_{datetime_suffix}'
        else:
            p_id = str(P.p_id)
        return os.path.join(
            P.opti_data_dir, p_id  # type: ignore[known-attribute]
        )

    def _get_block_dir_path(self, participant_dir, is_practice, block_task):
        """Construct block directory path."""
        phase = 'practice' if is_practice else 'testing'
        return os.path.join(participant_dir, phase, block_task)

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

    def _add_trial_header_info(self, filepath, trial_info):
        """Redundantly markup file with trial details"""

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
