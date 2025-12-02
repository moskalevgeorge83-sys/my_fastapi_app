# isort: skip_file
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from routes import Base, app, get_session


# Создаем тестовую базу данных
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="function")
async def client():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Переопределяем зависимость get_session
    async def override_get_session():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_recipes_list(client: AsyncClient):
    """
    Интеграционный тест для эндпоинта GET /recipes.
    Проверяет, что запрос успешно возвращает статус 200 и содержит заголовок 'Recipes List' в HTML-ответе.
    """
    response = await client.get("/recipes")
    assert response.status_code == 200
    assert "Recipes List" in response.text


@pytest.mark.anyio
async def test_recipe_detail(client: AsyncClient):
    """
    Интеграционный тест для эндпоинта GET /recipes/{recipe_id}.
    Сначала создаёт новый рецепт через POST /recipes,
    затем проверяет успешный запрос по ID рецепта с кодом 200
    и подтверждает, что в HTML-ответе содержится имя созданного рецепта.
    """
    recipe_data = {
        "name": "Test Recipe",
        "views": 0,
        "cook_time": 30,
        "ingredients": "Test ingredients",
        "description": "Test description",
    }
    create_response = await client.post("/recipes", json=recipe_data)
    assert create_response.status_code == 201
    recipe_id = create_response.json()["id"]

    response = await client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 200
    assert "Test Recipe" in response.text


@pytest.mark.anyio
async def test_create_recipe(client: AsyncClient):
    """
    Интеграционный тест для эндпоинта POST /recipes.
    Проверяет успешное создание нового рецепта и наличие имени рецепта в JSON-ответе.
    """
    recipe_data = {
        "name": "New Recipe",
        "views": 0,
        "cook_time": 45,
        "ingredients": "New ingredients",
        "description": "New description",
    }
    response = await client.post("/recipes", json=recipe_data)
    assert response.status_code == 201
    assert "New Recipe" in response.json()["name"]
