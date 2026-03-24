from pydantic import BaseModel
from typing import List, Dict, Union, Optional

class Point(BaseModel):
    id: str
    x: Optional[float] = None
    y: Optional[float] = None

class Constraint(BaseModel):
    type: str # 'length', 'angle', 'parallel', etc.
    targets: List[str]
    value: Union[float, str]
