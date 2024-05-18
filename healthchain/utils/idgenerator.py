import random
import string

from typing import List
import uuid


class IdGenerator:
    def __init__(
        self,
        resource_types: List[str] = None,
        patient_id_length: int = 7,
        encounter_id_length: int = 3,
    ) -> None:
        self.resource_types = resource_types
        self.patient_id_length = patient_id_length
        self.encounter_id_length = encounter_id_length

    def generate_random_user_id(self, min_length: int = 1, max_length: int = 5) -> str:
        """Randomly choose between alllowed resources e.g. 'Practitioner' and 'PractitionerRole'
        and generate a random ID consisting of 1 to 5 digits
        """
        prefix = random.choice(self.resource_types)
        random_id = "".join(
            random.choices(string.digits, k=random.randint(min_length, max_length))
        )
        return f"{prefix}/{random_id}"

    def generate_random_patient_id(self, k: int = 7) -> str:
        """
        Generate a random id of k length
        """
        random_id = "".join(random.choices(string.digits, k=k))
        return random_id

    def generate_random_encounter_id(self, k: int = 3) -> str:
        """
        Generate a random id of k length
        """
        random_id = "".join(random.choices(string.digits, k=k))
        return random_id

    def generate_random_uuid(self) -> str:
        return str(uuid.uuid4())
