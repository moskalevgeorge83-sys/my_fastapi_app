from typing import AsyncGenerator, Any
from contextlib import asynccontextmanager
from database import engine, async_session, Base
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import status, HTTPException
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models, schemas


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Менеджер жизненного цикла приложения FastAPI.
    Создаёт таблицы базы данных при старте и закрывает подключение к базе при остановке.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость FastAPI для получения асинхронной сессии базы данных.
    """
    async with async_session() as session:
        yield session


@app.get("/recipes", response_class=HTMLResponse)
async def recipes_list(request: Request, session: AsyncSession = Depends(get_session)) -> Any:
    """
    Возвращает HTML страницу с таблицей рецептов,
    отсортированных по убыванию просмотров и возрастанию времени приготовления.
    """
    query = select(models.Recipe).order_by(models.Recipe.views.desc(), models.Recipe.cook_time.asc())
    result = await session.execute(query)
    recipes = result.scalars().all()
    return templates.TemplateResponse("recipes_list.html", {"request": request, "recipes": recipes})


@app.get("/recipes/{recipe_id}", response_class=HTMLResponse)
async def recipe_detail(request: Request, recipe_id: int, session: AsyncSession = Depends(get_session)) -> Any:
    """
    Возвращает HTML страницу с подробной информацией о рецепте, включая детали.
    При каждом вызове увеличивает счётчик просмотров в таблицах рецепта и деталей.

    Возвращает 404, если рецепт не найден.
    """
    query = (
        select(models.Recipe)
        .options(selectinload(models.Recipe.details))
        .where(models.Recipe.id == recipe_id)
    )
    result = await session.execute(query)
    recipe = result.scalars().first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Рецепт не найден")

    recipe.views = (recipe.views or 0) + 1  # type: ignore[assignment]
    if recipe.details and hasattr(recipe.details, "views"):
        recipe.details.views = (recipe.details.views or 0) + 1

    await session.commit()
    await session.refresh(recipe)

    return templates.TemplateResponse("recipe_detail.html", {"request": request, "recipe": recipe})


@app.post("/recipes", response_model=schemas.RecipeOut, status_code=status.HTTP_201_CREATED)
async def create_recipe(recipe_in: schemas.RecipeCreate, session: AsyncSession = Depends(get_session)) -> schemas.RecipeOut:
    """
    Создаёт новый рецепт и связанные детали в базе данных.

    Аргументы:
    - recipe_in: входные данные рецепта по схеме RecipeCreate.
    - session: асинхронная сессия базы данных.

    Возвращает:
    - созданный рецепт с подробностями по схеме RecipeDetailOut.

    Ошибки:
    - Возбуждает HTTPException 409 при дублировании имени рецепта.
    """
    try:
        new_recipe = models.Recipe(
            name=recipe_in.name,
            views=recipe_in.views or 0,
            cook_time=recipe_in.cook_time,
        )
        session.add(new_recipe)
        await session.flush()

        recipe_detail = models.RecipeDetail(
            recipe_id=new_recipe.id,
            name=recipe_in.name,
            cook_time=recipe_in.cook_time,
            ingredients=recipe_in.ingredients,
            description=recipe_in.description,
        )
        session.add(recipe_detail)

        await session.commit()
        await session.refresh(new_recipe)
        new_recipe.details = recipe_detail

        return new_recipe

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Рецепт с таким именем уже существует."
        )

