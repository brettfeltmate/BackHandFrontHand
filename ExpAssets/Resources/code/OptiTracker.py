import datatable as dt
from typing import Tuple, Dict, List
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


class OptiTracker:
    def __init__(self) -> None:
        # NatNetClient instance
        self.client = self.init_client()

        # TODO:
        # - Add optional selectivity
        # - Insert asset IDs from descriptions into respective mocap tables

        self.frames = {
            "Prefix": dt.Frame(),
            "MarkerSet": dt.Frame(),
            "LabeledMarker": dt.Frame(),
            "LegacyMarkerSet": dt.Frame(),
            "RigidBody": dt.Frame(),
            "Skeleton": dt.Frame(),
            "AssetRigidBody": dt.Frame(),
            "AssetMarker": dt.Frame(),
            "ForcePlate": dt.Frame(),
            "Device": dt.Frame(),
            "Suffix": dt.Frame(),
        }

        self.descriptions = {
            "MarkerSet": dt.Frame(),
            "RigidBody": dt.Frame(),
            "Skeleton": dt.Frame(),
            "AssetRigidBody": dt.Frame(),
            "AssetMarker": dt.Frame(),
            "ForcePlate": dt.Frame(),
            "Device": dt.Frame(),
            "Camera": dt.Frame(),
        }

    # Create NatNetClient instance
    def init_client(self) -> object:
        client = NatNetClient()

        # Assign listener callbacks
        client.frame_data_listener = self.collect_frame
        client.description_listener = self.collect_descriptions

        return client

    # Plug into Motive stream
    def start_client(self) -> bool:
        return self.client.startup()

    # Stop NatNetClient
    def stop_client(self) -> None:
        self.client.shutdown()

    # streamdata collection callbacks

    def collect_frame(self, frame_data: Dict[str, List[Dict]]) -> None:
        # HACK: clumsy nesting
        for asset_type in frame_data.keys():
            for asset_data in frame_data[asset_type]:
                self.frames[asset_type].rbind(dt.Frame(asset_data))

    def collect_descriptions(self, descriptions: Dict[str, Tuple[Dict, ...]]) -> None:
        for asset_type, asset_description in descriptions.items():
            self.descriptions[asset_type].rbind(dt.Frame(asset_description))
