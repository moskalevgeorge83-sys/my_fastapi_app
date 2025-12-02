from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    views = Column(Integer, default=0)
    cook_time = Column(Integer, nullable=False)

    details = relationship(
        "RecipeDetail",
        back_populates="recipe",
        uselist=False,
        cascade="all, delete-orphan",
    )


class RecipeDetail(Base):
    __tablename__ = "recipe_details"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)  # Дублируется для удобства
    cook_time = Column(Integer, nullable=False)
    ingredients = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    recipe = relationship("Recipe", back_populates="details")
