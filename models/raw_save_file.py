from typing import Dict, Any

from bin_utils import rpad_bytes
from constant import SAVE_DATA_V14_LENGTH, SAVE_DATA_V15_LENGTH
from schemas.sav_14 import sav14_schema, sav14_save_data_schema
from schemas.sav_15 import sav15_schema, sav15_save_data_schema
from schemas.sav_16 import sav16_schema, sav16_save_data_schema
from schemas.version_id import version_identifier_schema
from construct import Container # Moved import to top


class RawSaveFile:
    def __init__(
            self,
            version: int,
            save_data: Any, # Changed type hint to Any to allow Dict or Container
    ):
        self.version = version
        self.save_data = save_data # This save_data is passed to construct.build later
        
        # Access lua_state based on type of save_data
        if isinstance(save_data, Container):
            self.lua_state_bytes = save_data.lua_state
        elif isinstance(save_data, dict):
            self.lua_state_bytes = save_data['lua_state']
        else:
            raise TypeError(f"save_data must be a Container or dict, got {type(save_data)}")

    @classmethod
    def from_file(cls, path: str) -> 'RawSaveFile':
        with open(path, 'rb') as f:
            input_bytes = f.read()
            version = version_identifier_schema.parse(input_bytes).version

            if version == 14:
                parsed_schema = sav14_schema.parse(input_bytes)
            elif version == 15:
                parsed_schema = sav15_schema.parse(input_bytes)
            elif version == 16:
                parsed_schema = sav16_schema.parse(input_bytes)
            else:
                raise Exception(f"Unsupported version {version}")

            # The 'clean_save_data' logic is removed.
            # RawSaveFile is instantiated with the direct parsed_schema.save_data.value (Container)
            return RawSaveFile(
                version,
                parsed_schema.save_data.value 
            )

    def to_file(self, path: str) -> None:
        if self.version == 14:
            sav14_schema.build_file(
                {
                    'save_data': {
                        'data': rpad_bytes(
                            sav14_save_data_schema.build(
                                self.save_data
                            ),
                            SAVE_DATA_V14_LENGTH
                        )
                    }
                },
                filename=path,
            )
        elif self.version == 15:
            sav15_schema.build_file(
                {
                    'save_data': {
                        'data': rpad_bytes(
                            sav15_save_data_schema.build(
                                self.save_data
                            ),
                            SAVE_DATA_V15_LENGTH
                        )
                    }
                },
                filename=path,
            )
        elif self.version == 16:
            sav16_schema.build_file( # Corrected from sav15_schema to sav16_schema
                {
                    'save_data': {
                        'data': sav16_save_data_schema.build(
                            self.save_data
                        )
                    }
                },
                filename=path,
            )
        else:
            raise Exception(f"Unsupported version {self.version}")
