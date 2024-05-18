from typing import List, Dict, Callable
from pydantic import BaseModel
from healthchain.data_generator.base_generators import generator_registry


class UseCaseMapping(BaseModel):
    generator: str
    params: Dict[str, str]
    # would also want to validate that the params are fields of the generator


use_case_mappings = {
    "problems": [
        {"generator": "condition", "params": {"field": "condition_type"}},
        {"generator": "condition", "params": {"field": "condition_type"}},
    ],
}


class GeneratorOrchestrator:
    def __init__(
        self, registry: Dict[str, Callable], mappings: Dict[str, List[Dict[str, str]]]
    ):
        self.registry = registry
        self.mappings = mappings

    def fetch_generator(self, generator_name: str) -> Callable:
        return self.registry.get(generator_name)

    def orchestrate(self, user_input: Dict[str, str]) -> List[BaseModel]:
        results = []

        for use_case, details in user_input.items():
            if use_case not in self.mappings:
                continue

            for item in self.mappings[use_case]:
                generator_name = item["generator"]
                params = item.get(
                    "params", {}
                ).copy()  # Use a copy to avoid mutating the original params
                # add the use case key to the params
                params["complexity"] = details

                generator = self.fetch_generator(generator_name)
                result = generator.generate(**params)
                results.append(result)

        return results


# Example usage
orchestrator = GeneratorOrchestrator(generator_registry, use_case_mappings)

user_input = {"problems": "complex_problem"}
generated_resources = orchestrator.orchestrate(user_input)

for resource in generated_resources:
    print(resource.json())
