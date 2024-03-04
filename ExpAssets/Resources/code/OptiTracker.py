import sys
import os
import datatable as dt
from typing import Tuple, Dict, List, Any, Union

# Get script directory to allow for relative imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


# Import native API class
from NatNetClient import NatNetClient

# Constants denoting asset types
PREFIX = "Prefix"
MARKER_SET = "MarkerSet"
LABELED_MARKER = "LabeledMarker"
LEGACY_MARKER_SET = "LegacyMarkerSet"
RIGID_BODY = "RigidBody"
SKELETON = "Skeleton"
ASSET_RIGID_BODY = "AssetRigidBody"
ASSET_MARKER = "AssetMarker"
FORCE_PLATE = "ForcePlate"
DEVICE = "Device"
CAMERA = "Camera"
SUFFIX = "Suffix"


# Wrapper for NatNetClient API class
class OptiTracker:
    def __init__(self) -> None:
        # NatNetClient instance
        self.client = self.init_client()

        # self.frame_listeners = {
        #     PREFIX: True, MARKER_SET: True, LABELED_MARKER: True,
        #     LEGACY_MARKER_SET: True, RIGID_BODY: True, SKELETON: True,
        #     ASSET_RIGID_BODY: True, ASSET_MARKER: True, FORCE_PLATE: False,
        #     DEVICE: False, CAMERA: True, SUFFIX: True
        # }

        # self.description_listeners = {
        #     MARKER_SET: True, RIGID_BODY: True, SKELETON: True, FORCE_PLATE: False, 
        #     DEVICE: False, CAMERA: True, ASSET_RIGID_BODY: True, ASSET_MARKER: True
        # }


        # self.descriptions = {
        #     asset_type: dt.Frame() for asset_type, store_value in self.description_listeners.items() if store_value
        # }

    # Create NatNetClient instance
    def init_client(self) -> object:
        
        # Spawn client instance
        client = NatNetClient()

        # Set frame listener
        client.frame_data_listener = self.recieve_frame

        return client
    
    # Start NatNetClient, returns True if successful, False otherwise
    def start(self) -> bool:
        self.init_frame()
        return self.client.startup()

    # Stop NatNetClient
    def stop(self) -> None:
        self.client.shutdown()

    def init_frame(self) -> Dict[str, dt.Frame]:
        self.frames = {
            'Prefix':dt.Frame(), 
            'MarkerSets':dt.Frame(), 
            #'LabeledMarkerSet':dt.Frame(),
            'LegacyMarkerSet':dt.Frame(),
            'RigidBodies':dt.Frame(), 
            'Skeletons':dt.Frame(),
            #'AssetRigidBodies':dt.Frame(),
            'AssetMarkers':dt.Frame(),
            #'ForcePlates':dt.Frame(), 
            #'Devices':dt.Frame(), 
            #'Suffix': dt.Frame()
        }

    # Get new frame data
    def recieve_frame(self, frame_data: Dict[str, List[Dict]]) -> None:
        # Store frame data
        for asset in frame_data.keys():
            for frame in frame_data[asset]:
                self.frames[asset].rbind(dt.Frame(frame))


    def update_frame(self, insert: Dict[Any, Any], into: Union[str, List[str]] = None) -> None:
        if into is not None:
            assets_to_update = [into] if isinstance(into, str) else into

        else:
            assets_to_update = self.frames.keys()

        try:
            for asset in assets_to_update:
                self.frames[asset][:, dt.update(**insert)]

        except KeyError:
            raise ValueError(f"OptiTracker.update_frame: Invalid asset type {asset}")


    def write_data(self, path: str) -> None:
        for asset, frame in self.frames.items():
            frame.to_csv(f"{path}/{asset}.csv")
    
    # Return frame and reset to None
    def export(self) -> Dict[str, dt.Frame]:
        return self.frames
    

        

    # Get new model descriptions
    def collect_descriptions(self, descriptions: Dict[str, Tuple[Dict, ...]]) -> None:
        for asset_type, asset_description in descriptions.items():
            self.descriptions[asset_type].rbind(dt.Frame(asset_description))










