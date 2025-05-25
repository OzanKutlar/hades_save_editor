from typing import Dict, Any

from bin_utils import rpad_bytes
from constant import SAVE_DATA_V14_LENGTH, SAVE_DATA_V15_LENGTH
from schemas.sav_14 import sav14_schema, sav14_save_data_schema
from schemas.sav_15 import sav15_schema, sav15_save_data_schema
from schemas.sav_16 import sav16_schema, sav16_save_data_schema
from schemas.version_id import version_identifier_schema


class RawSaveFile:
    def __init__(
            self,
            version: int,
            save_data: Dict[Any, Any],
    ):
        self.version = version
        self.save_data = save_data
        self.lua_state_bytes = save_data['lua_state']

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

            # Explicitly construct save_data dict to avoid internal construct fields like '_io'
            parsed_data_container = parsed_schema.save_data.value
            clean_save_data = {}
            
            # Common fields for v14, v15, v16 (adjust if there are version-specific top-level save_data fields)
            # Based on sav16_save_data_schema, which is the most comprehensive here.
            # Other schemas might have fewer fields, so getattr with default or checking version is safer if they differ significantly.
            
            expected_fields = [
                "version", "location", "runs", "active_meta_points",
                "active_shrine_points", "god_mode_enabled", "hell_mode_enabled",
                "lua_keys", "current_map_name", "start_next_map", "lua_state"
            ]
            if version == 16: # version 16 has timestamp
                expected_fields.insert(1, "timestamp")
            # v14 and v15 do not have 'timestamp' at this level in their specific save_data_schema

            for field_name in expected_fields:
                if hasattr(parsed_data_container, field_name):
                    clean_save_data[field_name] = getattr(parsed_data_container, field_name)
                else:
                    # This might happen if a field is truly optional or not in an older version's schema
                    # For now, we assume fields are present if listed.
                    # A more robust handling might involve schema introspection or default values.
                    print(f"Warning: Field '{field_name}' not found in parsed save data for version {version}.", file=sys.stderr)


            return RawSaveFile(
                version,
                clean_save_data
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
            sav15_schema.build_file(
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
