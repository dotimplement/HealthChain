import pandas as pd

from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from healthchain.io.containers.base import DataContainer


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
