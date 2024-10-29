import json
import pandas as pd

from typing import Dict, Optional, TypeVar, Generic, List, Any, Iterator
from dataclasses import dataclass, field
from spacy.tokens import Doc as SpacyDoc

from healthchain.models.data.ccddata import CcdData
from healthchain.models.data.cdsfhirdata import CdsFhirData
from healthchain.models.data.concept import (
    AllergyConcept,
    MedicationConcept,
    ProblemConcept,
)
from healthchain.models.responses.cdsresponse import Action, Card


T = TypeVar("T")


@dataclass
class DataContainer(Generic[T]):
    """
    A generic container for data.

    This class represents a container for data with a specific type T.

    Attributes:
        data (T): The data stored in the container.

    Methods:
        to_dict() -> Dict[str, Any]:
            Converts the container's data to a dictionary.

        to_json() -> str:
            Converts the container's data to a JSON string.

        from_dict(cls, data: Dict[str, Any]) -> "DataContainer":
            Creates a DataContainer instance from a dictionary.

        from_json(cls, json_str: str) -> "DataContainer":
            Creates a DataContainer instance from a JSON string.
    """

    data: T

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContainer":
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "DataContainer":
        return cls.from_dict(json.loads(json_str))


@dataclass
class Document(DataContainer[str]):
    """
    A container for document data, optionally wrapping a spaCy Doc object.

    This class extends DataContainer to specifically handle textual document data.
    It provides functionality to work with raw text, tokenized text, spaCy Doc objects,
    and structured clinical data.

    Attributes:
        data (str): The raw text content of the document.
        preprocessed_text (str): The preprocessed version of the text.
        tokens (List[str]): A list of individual tokens extracted from the text.
        pos_tags (List[str]): A list of part-of-speech tags corresponding to the tokens.
        entities (List[str]): A list of named entities identified in the text.
        ccd_data (Optional[CcdData]): An optional CcdData object containing structured clinical data.
        fhir_resources (Optional[CdsFhirData]): Optional FHIR resources data.
        cds_cards (Optional[List[Card]]): Optional list of CDS cards.
        cds_actions (Optional[List[Action]]): Optional list of CDS actions.
        text (str): The current text content, which may be updated when setting a spaCy Doc.
        _doc (SpacyDoc): An internal reference to the spaCy Doc object, if set.

    Methods:
        __post_init__(): Initializes the text attribute and _doc reference.
        _update_attributes(): Updates tokens, pos_tags, and entities from the spaCy Doc.
        doc (property): Returns the spaCy Doc object if set, or raises an error.
        set_spacy_doc(doc: SpacyDoc): Sets the spaCy Doc and updates related attributes.
        word_count() -> int: Returns the number of tokens in the document.
        char_count() -> int: Returns the number of characters in the text.
        get_entities() -> List[Dict[str, Any]]: Returns a list of entities with their details.
        update_ccd(new_problems: List[ProblemConcept], new_medications: List[MedicationConcept], new_allergies: List[AllergyConcept], overwrite: bool): Updates the existing CcdData object.
        __iter__() -> Iterator[str]: Allows iteration over the document's tokens.
        __len__() -> int: Returns the word count of the document.

    Raises:
        ValueError: When attempting to access the spaCy Doc before it's set.

    Note:
        The spaCy Doc object needs to be set using a preprocessor before accessing
        certain attributes and methods that depend on it.
    """

    preprocessed_text: str = field(default="")
    tokens: List[str] = field(default_factory=list)
    pos_tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    ccd_data: Optional[CcdData] = field(default=None)
    fhir_resources: Optional[CdsFhirData] = field(default=None)
    cds_cards: Optional[List[Card]] = field(default=None)
    cds_actions: Optional[List[Action]] = field(default=None)
    entities: List[str] = field(default_factory=list)

    # Third-party specific attributes
    spacy_doc: Optional[SpacyDoc] = None
    huggingface_results: Dict[str, Any] = field(default_factory=dict)
    langchain_results: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.text = self.data
        if not self.tokens:
            self.tokens = self.text.split()  # Basic tokenization if not provided

    def add_spacy_doc(self, doc: SpacyDoc):
        self.spacy_doc = doc
        self.text = doc.text
        self.tokens = [token.text for token in doc]
        self.entities = [
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]

    def add_huggingface_output(self, task: str, output: Any):
        self.huggingface_results[task] = output

    def add_langchain_output(self, task: str, output: Any):
        self.langchain_results[task] = output

    def get_tokens(self) -> List[str]:
        return self.tokens

    def get_entities(self) -> List[Dict[str, Any]]:
        return self.entities

    def get_embeddings(self) -> Optional[List[float]]:
        return self.embeddings

    def set_embeddings(self, embeddings: List[float]):
        self.embeddings = embeddings

    def get_spacy_doc(self) -> Optional[SpacyDoc]:
        return self.spacy_doc

    def get_huggingface_output(self, task: str) -> Any:
        return self.huggingface_results.get(task)

    def get_langchain_output(self, task: str) -> Any:
        return self.langchain_results.get(task)

    def _update_attributes(self):
        self.tokens = [token.text for token in self._doc]
        self.pos_tags = [token.pos_ for token in self._doc]
        self.entities = [ent.text for ent in self._doc.ents]

    @property
    def doc(self) -> SpacyDoc:
        if self._doc is None:
            raise ValueError(
                "spaCy Doc is not set. Use a preprocessor to set the spaCy Doc."
            )
        return self._doc

    def word_count(self) -> int:
        return len(self.tokens)

    def char_count(self) -> int:
        return len(self.text)

    def update_ccd(
        self,
        new_problems: List[ProblemConcept],
        new_medications: List[MedicationConcept],
        new_allergies: List[AllergyConcept],
        overwrite: bool = False,
    ) -> None:
        """
        Updates the existing CcdData object with new data.

        Args:
            new_problems (List[ProblemConcept]): List of new problem concepts to add or update.
            new_medications (List[MedicationConcept]): List of new medication concepts to add or update.
            new_allergies (List[AllergyConcept]): List of new allergy concepts to add or update.
            overwrite (bool, optional): If True, replaces existing data; if False, appends new data. Defaults to False.

        Raises:
            ValueError: If there is no existing CcdData object to update.
        """
        if self.ccd_data is None:
            self.ccd_data = CcdData()

        if overwrite:
            self.ccd_data.problems = new_problems
            self.ccd_data.medications = new_medications
            self.ccd_data.allergies = new_allergies
        else:
            self.ccd_data.problems.extend(new_problems)
            self.ccd_data.medications.extend(new_medications)
            self.ccd_data.allergies.extend(new_allergies)

    def __iter__(self) -> Iterator[str]:
        return iter(self.tokens)

    def __len__(self) -> int:
        return self.word_count()


@dataclass
class Tabular(DataContainer[pd.DataFrame]):
    """
    A container for tabular data, wrapping a pandas DataFrame.

    Attributes:
        data (pd.DataFrame): The pandas DataFrame containing the tabular data.

    Methods:
        __post_init__(): Validates that the data is a pandas DataFrame.
        columns: Property that returns a list of column names.
        index: Property that returns the DataFrame's index.
        dtypes: Property that returns a dictionary of column names and their data types.
        column_count(): Returns the number of columns in the DataFrame.
        row_count(): Returns the number of rows in the DataFrame.
        get_dtype(column: str): Returns the data type of a specific column.
        __iter__(): Returns an iterator over the column names.
        __len__(): Returns the number of rows in the DataFrame.
        describe(): Returns a string description of the tabular data.
        remove_column(name: str): Removes a column from the DataFrame.
        from_csv(path: str, **kwargs): Class method to create a Tabular object from a CSV file.
        from_dict(data: Dict[str, Any]): Class method to create a Tabular object from a dictionary.
        to_csv(path: str, **kwargs): Saves the DataFrame to a CSV file.
    """

    def __post_init__(self):
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("data must be a pandas DataFrame")

    @property
    def columns(self) -> List[str]:
        return list(self.data.columns)

    @property
    def index(self) -> pd.Index:
        return self.data.index

    @property
    def dtypes(self) -> Dict[str, str]:
        return {col: str(dtype) for col, dtype in self.data.dtypes.items()}

    def column_count(self) -> int:
        return len(self.columns)

    def row_count(self) -> int:
        return len(self.data)

    def get_dtype(self, column: str) -> str:
        return str(self.data[column].dtype)

    def __iter__(self) -> Iterator[str]:
        return iter(self.columns)

    def __len__(self) -> int:
        return self.row_count()

    def describe(self) -> str:
        return f"Tabular data with {self.column_count()} columns and {self.row_count()} rows"

    def remove_column(self, name: str) -> None:
        self.data.drop(columns=[name], inplace=True)

    @classmethod
    def from_csv(cls, path: str, **kwargs) -> "Tabular":
        return cls(pd.read_csv(path, **kwargs))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tabular":
        df = pd.DataFrame(**data["data"])
        return cls(df)

    def to_csv(self, path: str, **kwargs) -> None:
        self.data.to_csv(path, **kwargs)
