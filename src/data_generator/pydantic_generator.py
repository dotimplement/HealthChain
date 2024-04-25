from pydantic import BaseModel, Field, conlist
import time

import json

# Specify the path to your JSON file

def load_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data


def write_model(f, name, model_info):
    enum_items = {}
    if 'oneOf' in model_info:
        pass
    elif 'properties' in model_info:
        f.write(f'class {name}(BaseModel):\n')
        props = model_info['properties']
        for prop_name, prop_info in props.items():
            if prop_name[0] == '_':
                pass
            else:
                prop_description = prop_info.get('description', '').replace('"', '').split('\n')[0].split('\r')[0]
                if '$ref' in prop_info:
                    # Handle reference to another model
                    ref_model = prop_info['$ref'].split('/')[-1]
                    f.write(f'    {prop_name}_field: {ref_model} = Field(default=None, alias="{prop_name}", description="{prop_description}")\n')
                elif 'type' in prop_info and 'items' in prop_info:
                    # Handle list of other models
                    if '$ref' in prop_info['items']:
                        item_model = prop_info['items']['$ref'].split('/')[-1]
                        f.write(f'    {prop_name}_field: list[{item_model}] = Field(default_factory=None, alias="{prop_name}", description="{prop_description}")\n')
                    elif 'enum' in prop_info['items']:
                        enum_items[prop_name] = prop_info['items']['enum']
    elif 'pattern' in model_info:
        pydantic_type = None
        pattern = model_info.get('pattern')
        description = model_info.get('description').replace('"', '').split('\n')[0].split('\r')[0]
        field_type = model_info.get('type')
        if field_type == 'string':
            pydantic_type = 'str'
        elif field_type == 'integer':
            pydantic_type = 'int'
        elif field_type == 'number':
            pydantic_type = 'float'
        else:
            pydantic_type = 'str'
        f.write(f'class {name.lower()}(BaseModel):\n')
        f.write(f'    {name}: {pydantic_type} = Field(pattern=r\'{pattern}\')\n\n')
        f.write(f'    class Config:\n')
        f.write(f'        schema_extra = {{\n')
        f.write(f'            "description": "{description}"\n')
        f.write(f'        }}\n\n')
    elif 'description' in model_info and 'type' in model_info:
        pass
    else:
        pass

    f.write('\n')

    return enum_items


def generate_pydantic_models_with_complex_fields(schema, output_file):
    enum_dicts = {}
    with open(output_file, 'w') as f:
        f.write('from __future__ import annotations\n')
        f.write('from pydantic import BaseModel, Field, conlist, condecimal, constr, conint, confloat, typing\n\n')

        for model_name, model_info in schema.items():
            if model_name != 'Base':
                enum_items = write_model(f, model_name, model_info)
                enum_dicts.update(enum_items)
    



if __name__ == '__main__':
    data = load_data('../data/fhir.schema.json')
    definitions = data['definitions']
    generate_pydantic_models_with_complex_fields(definitions, 'pydantic_complex_field_models_vsc.py')
    print('Pydantic models generated successfully!')


