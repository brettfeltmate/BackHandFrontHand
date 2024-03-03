# TODO: Document

from construct import Struct
from DataStructures import *
from typing import Tuple, List, Dict, Union




# # # # # # # # # # # # # # # # # # # # # # #
# Parent class for asset-specific upackers  #
# # # # # # # # # # # # # # # # # # # # # # #

class dataUnpacker:
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        self.natnet_version = NatNetStreamVersion      # implementation unlikely until future updates warrant it
        self._structure = self._get_structure()        # asset bespoke parsing structures, see DataStructures.py
        self._framedata = None                         # container for unpacked data

        # parses on init if data
        if unparsed_bytestream is not None:
            self.parse(unparsed_bytestream)

    # fetch structure corresponding to asset type
    def _get_structure(self) -> Struct:
        """
        Returns the Struct corresponding to the type of this instance
        from the FRAMEDATA_STRUCTS mapping.
        """
        try:
            return FRAMEDATA_STRUCTS[type(self)]
        except KeyError:
            raise ValueError(f"dataUnpacker._get_structure() | Unrecognized asset type.\n\tExpected: {FRAMEDATA_STRUCTS.keys()}\n\tSupplied: {type(self)}")
    
    # returns landing position in datastream after parsingg
    def relative_offset(self) -> int:
        if self._framedata is not None:
            return self._framedata.relative_offset
        
        return 0
    
    # shadows Construct.Struct.parse() method
    def parse(self, unparsed_bytestream: bytes) -> None:
        self._framedata = self._structure.parse(unparsed_bytestream)

    # coerces data parcels into list[dict]; bundling procedure varies by asset type
    #       NOTE: children drop leading entries (obj addr)
    def data(self) -> List[Dict]:
        raise NotImplementedError("AssetDataStruct.data() | Must be implemented by child class.")




# # # # # # # # # # # # # #
# Unpackers by asset type #
# # # # # # # # # # # # # # 
    
class prefixData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)     
        
    def data(self) -> List[Dict]:
        # Drops terminal entry (relative stream pos)
        return [dict(list(self._framedata.items())[1:-1])]


class markerSetsData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(marker.items())[1:]) 
                for marker_set in self._framedata.children
                for marker in marker_set.children]
    
# if you thought these'd come with labels, you're wrong.
class labeledMarkerSetData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(labeledMarker.items())[1:]) 
                for labeledMarker in self._framedata.children]

# no idea what these are; not documented in SDK
# NOTE: untested, unpacking breaks upon reaching them; without documentation I'm struggling to confirm correct structuring
class legacyMarkerSetData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(legacyMarker.items())[1:]) 
                for legacyMarker in self._framedata.children]


class rigidBodiesData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:

        return [dict(list(rigidBody.items())[1:])
                for rigidBody in self._framedata.children]


# instead of giving rigid body collectives a shared ID, they gave them their own class
class skeletonsData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(rigidBody.items())[1:]) 
                for skeleton in self._framedata.children
                for rigidBody in skeleton.children]
    
# I think this is in the dictionary under "redundancy"
class assetsData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    # NOTE: out of necessity, not choice
    def data(self, asset_type) -> List[Dict]:
        if (asset_type == "AssetRigidBodies"):
            return [dict(list(assetRigidBody.items())[1:]) 
                    for assetRigidBody in self._framedata.rigid_body_children]
                    # for asset in self._framedata.children
                    # for assetRigidBody in asset.rigid_bodies]
        
        elif (asset_type == "AssetMarkers"):
            return [dict(list(assetMarker.items())[1:]) 
                    for assetMarker in self._framedata.marker_children]
                    # for asset in self._framedata.children
                    # for assetMarker in asset.markers]
        else:
            raise ValueError(f"assetData.export() | asset_type must be 'AssetRigidBodies' or 'AssetMarkers'; type supplied: {asset_type}")


# NOTE: untested, cannot verify that calibration matrices are correctly parsed
class forcePlatesData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(frame.items())[1:]) 
                for forcePlate in self._framedata.children 
                for channel in forcePlate.children
                for frame in channel.children
                ]


class devicesData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(frame.items())[1:]) 
                for device in self._framedata.children 
                for channel in device.children
                for frame in channel.children
                ]


class suffixData(dataUnpacker):
    def __init__(self, unparsed_bytestream: bytes = None, NatNetStreamVersion: List[int] = None) -> None:
        super().__init__(unparsed_bytestream, NatNetStreamVersion)

    def data(self) -> List[Dict]:
        return [dict(list(self._framedata.items())[1:-1])]
    


# unpacker class type used to select the correct structure
# NOTE: potentially will be refactored to allow for keying via stream version
FRAMEDATA_STRUCTS = {
    prefixData:             dataStruct_Prefix,
    markerSetsData:         dataStruct_MarkerSets,
    labeledMarkerSetData:   dataStruct_LabeledMarkerSet,
    legacyMarkerSetData:    dataStruct_LegacyMarkerSet,
    rigidBodiesData:        dataStruct_RigidBodies,
    skeletonsData:          dataStruct_Skeletons,
    assetsData:             dataStruct_Assets,
    forcePlatesData:        dataStruct_ForcePlates,
    devicesData:            dataStruct_Devices,
    suffixData:             dataStruct_Suffix
}

# # # # # # # # # # # # #
# Frame data container  #
# # # # # # # # # # # # #
    
class frameData:
    def __init__(self) -> None:
        
        # Aggregate Frame Data
        self._framedata = {
            'Prefix': [], 
            'MarkerSets': [], 
            #'LabeledMarkerSet': [],
            'LegacyMarkerSet': [],
            'RigidBodies': [], 
            'Skeletons': [],
            #'AssetRigidBodies': [],
            'AssetMarkers': [],
            #'ForcePlates': [], 
            #'Devices': [], 
            'Suffix': []
        }

    def log(self, asset_type: str, asset_frame_data: List[Dict]) -> None:
        self._framedata[asset_type].append(asset_frame_data)

    # TODO: build back in; or drop, ostensibly unnecessary
    def __validate_export_arg(self, arg: Union[Tuple[str,...], str], name: str) -> Tuple[str, ...]:
        if isinstance(arg, str):
            return (arg,)
        elif isinstance(arg, tuple) and all(isinstance(i, str) for i in arg):
            return arg
        else:
            raise TypeError(f"frameData.export() | {name}: expected str or tuple thereof, got {type(arg)}")

    # exporting allows for selective inclusion/exclusion of asset types
        # TODO: make that true
    def export(self, include: Union[Tuple[str, ...], str] = None, exclude: Union[Tuple[str, ...], str] = None) -> Dict[str, Tuple[Dict, ...]]:
        # include = self.__validate_export_arg(include, "include")

        # if exclude is not None:
        #     exclude = self.__validate_export_arg(exclude, "exclude")
        #     return {k: v for k, v in self._framedata.items() 
        #             if k in include and k not in exclude}
            
        # return {k: v for k, v in self._framedata.items() if k in include}

        return self._framedata

