from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RecipeBase(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Pancakes"})
    views: Optional[int] = 0
    cook_time: int = Field(..., gt=0, json_schema_extra={"example": 15})


class RecipeCreate(RecipeBase):
    views: Optional[int] = 0
    ingredients: str = Field(
    ...,
    json_schema_extra={"example": "Flour, Eggs, Milk"},
)
    description: Optional[str] = Field(
        None, json_schema_extra={"example": "Mix ingredients and fry."}
    )


class RecipeDetailOut(BaseModel):
    name: str
    cook_time: int
    ingredients: str
    description: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RecipeOut(RecipeBase):
    id: int
    views: int
    details: Optional[RecipeDetailOut]

    model_config = ConfigDict(from_attributes=True)
