from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import json

# Function to load JSON data from a file
def load_data(file_path: str) -> Dict:
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("File not found.")
        raise
    except json.JSONDecodeError:
        print("Failed to decode JSON.")
        raise

# Function to write a single Pydantic model based on the schema information
def write_model(file, name: str, model_info: Dict) -> Dict[str, List[str]]:
    enum_items: dict = {}
    enum_list: list = []
    if 'oneOf' in model_info:
        file.write(f'class {name}Model(Enum):\n')
        for item in model_info['oneOf']:
            if '$ref' in item:
                name = item['$ref'].split('/')[-1]
                file.write(f'    {name}: stringModel = "{item["$ref"]}"\n')
        return enum_items

    if 'properties' in model_info:
        file.write(f'class {name}Model(BaseModel):\n')
        for prop_name, prop_info in model_info['properties'].items():
            if prop_name.startswith('_'):
                continue
            prop_description = prop_info.get('description', '').replace('"', '').split('\n')[0].split('\r')[0]
            write_field(file, prop_name, prop_info, prop_description, name)
            if 'enum' in prop_info:
                enum_items = prop_info['enum']
                enum_items = [str(item) for item in enum_items]
                enum_list.append({f'{name}_{prop_name}': enum_items})
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
        file.write(f'class {name}Model(BaseModel):\n')
        file.write(f'    {name}: {pydantic_type} = Field(pattern=r\'{pattern}\')\n\n')
        file.write(f'    class Config:\n')
        file.write(f'        schema_extra = {{\n')
        file.write(f'            "description": "{description}"\n')
        file.write(f'        }}\n\n')

    file.write('\n')

    return enum_list

# Helper function to handle the writing of model fields
def write_field(file, prop_name: str, prop_info: Dict, prop_description: str, name: str):
    if '$ref' in prop_info:
        ref_model = prop_info['$ref'].split('/')[-1]
        if ref_model == 'base64Binary':
            ref_model = 'string'
        file.write(f'    {prop_name}_field: {ref_model}Model = Field(default=None, alias="{prop_name}", description="{prop_description}")\n')
    elif 'type' in prop_info and 'items' in prop_info and '$ref' in prop_info['items']:
        item_model = prop_info['items']['$ref'].split('/')[-1]
        file.write(f'    {prop_name}_field: List[{item_model}Model] = Field(default_factory=list, alias="{prop_name}", description="{prop_description}")\n')
    elif 'enum' in prop_info:
        file.write(f'    {name}_{prop_name}_field: {prop_name}Model = Field(..., alias="{prop_name}", description="{prop_description}")\n')
    elif 'const' in prop_info:
        file.write(f'    {prop_name}: str =  "{prop_info["const"]}"\n')

# Generate all Pydantic models from the schema
def generate_pydantic_models(schema: Dict[str, Any], output_file: str):
    with open(output_file, 'w') as file:
        enum_list_total = []
        file.write('from __future__ import annotations\n')
        file.write('from pydantic import BaseModel, Field\n')
        file.write('from typing import List, Optional\n')
        file.write('from enum import Enum\n\n')
        for model_name, model_info in schema.items():
            if model_name != 'Base':
                enum_list = write_model(file, model_name, model_info)
                enum_list_total.extend(enum_list)

        #TODO: Need to keep a global list of enums to avoid duplicates
        for enum_item in enum_list_total:
            name = list(enum_item.keys())[0]
            file.write(f'class {name}(Enum):\n')
            enum_items = enum_item[name]
            # for item in enum_items:
                ## TODO: Handle special characters in item names
                # file.write(f'    {item.replace("-", "_")} = "{item}"\n')
            file.write('    pass\n\n')
            file.write('\n')
        
        file.write('HumanNameModel.model_rebuild()\n')


# Main execution flow
if __name__ == '__main__':
    data: dict = load_data('../data/fhir.schema.json')
    definitions = data.get('definitions', {})
    generate_pydantic_models(definitions, 'src/pydantic_models.py')
    print('Pydantic models generated successfully!')


class MyEmptyClass():
    pass
