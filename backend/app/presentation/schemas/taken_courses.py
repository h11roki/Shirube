from pydantic import BaseModel


class TakenCoursesOut(BaseModel):
    names: list[str]
