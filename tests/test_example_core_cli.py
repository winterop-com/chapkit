"""Tests for core_cli example validating direct database operations.

Tests the CLI example that demonstrates using core Database, Repository,
and Manager directly without FastAPI for command-line tools and scripts.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from chapkit.core import Database
from examples.core_cli import Product, ProductIn, ProductManager, ProductRepository


@pytest.fixture
async def database() -> AsyncGenerator[Database, None]:
    """Create and initialize in-memory database for testing."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    try:
        yield db
    finally:
        await db.dispose()


@pytest.fixture
async def manager(database: Database) -> AsyncGenerator[ProductManager, None]:
    """Create product manager with initialized database."""
    async with database.session() as session:
        repo = ProductRepository(session)
        yield ProductManager(repo)


async def test_create_product(database: Database) -> None:
    """Test creating a product."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        product = await manager.save(
            ProductIn(
                sku="TEST-001",
                name="Test Product",
                price=99.99,
                stock=10,
            )
        )

        assert product.sku == "TEST-001"
        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.stock == 10
        assert product.active is True
        assert product.id is not None


async def test_find_by_sku(database: Database) -> None:
    """Test finding product by SKU."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create a product
        created = await manager.save(
            ProductIn(
                sku="FIND-001",
                name="Findable Product",
                price=49.99,
                stock=5,
            )
        )

        # Find by SKU
        found = await manager.find_by_sku("FIND-001")
        assert found is not None
        assert found.id == created.id
        assert found.sku == "FIND-001"
        assert found.name == "Findable Product"


async def test_find_by_sku_not_found(database: Database) -> None:
    """Test finding product by non-existent SKU returns None."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        found = await manager.find_by_sku("NONEXISTENT")
        assert found is None


async def test_find_low_stock(database: Database) -> None:
    """Test finding products with low stock."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create products with varying stock levels
        await manager.save(ProductIn(sku="HIGH-001", name="High Stock", price=10.0, stock=100))
        await manager.save(ProductIn(sku="LOW-001", name="Low Stock 1", price=10.0, stock=5))
        await manager.save(ProductIn(sku="LOW-002", name="Low Stock 2", price=10.0, stock=8))
        await manager.save(ProductIn(sku="ZERO-001", name="Out of Stock", price=10.0, stock=0))

        # Find low stock (threshold = 10)
        low_stock = await manager.find_low_stock(threshold=10)

        assert len(low_stock) == 3
        skus = {p.sku for p in low_stock}
        assert skus == {"LOW-001", "LOW-002", "ZERO-001"}


async def test_find_low_stock_excludes_inactive(database: Database) -> None:
    """Test that low stock query excludes inactive products."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create active and inactive products with low stock
        await manager.save(ProductIn(sku="ACTIVE-LOW", name="Active Low", price=10.0, stock=5, active=True))
        await manager.save(ProductIn(sku="INACTIVE-LOW", name="Inactive Low", price=10.0, stock=5, active=False))

        # Find low stock
        low_stock = await manager.find_low_stock(threshold=10)

        # Should only include active products
        assert len(low_stock) == 1
        assert low_stock[0].sku == "ACTIVE-LOW"


async def test_restock_product(database: Database) -> None:
    """Test restocking a product."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create a product
        product = await manager.save(
            ProductIn(
                sku="RESTOCK-001",
                name="Restockable Product",
                price=29.99,
                stock=5,
            )
        )

        initial_stock = product.stock

        # Restock
        restocked = await manager.restock(product.id, 20)

        assert restocked.id == product.id
        assert restocked.stock == initial_stock + 20
        assert restocked.stock == 25


async def test_restock_nonexistent_product(database: Database) -> None:
    """Test restocking non-existent product raises error."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        from ulid import ULID

        fake_id = ULID()

        with pytest.raises(ValueError, match="not found"):
            await manager.restock(fake_id, 10)


async def test_list_all_products(database: Database) -> None:
    """Test listing all products."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create multiple products
        await manager.save(ProductIn(sku="LIST-001", name="Product 1", price=10.0, stock=10))
        await manager.save(ProductIn(sku="LIST-002", name="Product 2", price=20.0, stock=20))
        await manager.save(ProductIn(sku="LIST-003", name="Product 3", price=30.0, stock=30))

        # List all
        all_products = await manager.find_all()

        assert len(all_products) == 3
        skus = {p.sku for p in all_products}
        assert skus == {"LIST-001", "LIST-002", "LIST-003"}


async def test_count_products(database: Database) -> None:
    """Test counting products."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Initially empty
        count = await manager.count()
        assert count == 0

        # Add products
        await manager.save(ProductIn(sku="COUNT-001", name="Product 1", price=10.0))
        await manager.save(ProductIn(sku="COUNT-002", name="Product 2", price=20.0))

        count = await manager.count()
        assert count == 2


async def test_update_product(database: Database) -> None:
    """Test updating a product."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create a product
        product = await manager.save(
            ProductIn(
                sku="UPDATE-001",
                name="Original Name",
                price=50.0,
                stock=10,
            )
        )

        # Update it
        updated = await manager.save(
            ProductIn(
                id=product.id,
                sku="UPDATE-001",
                name="Updated Name",
                price=75.0,
                stock=15,
            )
        )

        assert updated.id == product.id
        assert updated.sku == "UPDATE-001"
        assert updated.name == "Updated Name"
        assert updated.price == 75.0
        assert updated.stock == 15


async def test_delete_product(database: Database) -> None:
    """Test deleting a product."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create a product
        product = await manager.save(
            ProductIn(
                sku="DELETE-001",
                name="To Be Deleted",
                price=10.0,
            )
        )

        # Delete it
        await manager.delete_by_id(product.id)

        # Verify it's gone
        found = await manager.find_by_id(product.id)
        assert found is None


async def test_product_entity_defaults(database: Database) -> None:
    """Test product entity has correct default values."""
    async with database.session() as session:
        repo = ProductRepository(session)
        manager = ProductManager(repo)

        # Create with minimal data
        product = await manager.save(
            ProductIn(
                sku="DEFAULTS-001",
                name="Product with Defaults",
                price=10.0,
            )
        )

        # Check defaults
        assert product.stock == 0
        assert product.active is True


async def test_repository_find_by_id(database: Database) -> None:
    """Test repository find_by_id method."""
    async with database.session() as session:
        repo = ProductRepository(session)

        # Create a product directly via ORM
        product = Product(
            sku="REPO-001",
            name="Repository Test",
            price=25.0,
            stock=5,
            active=True,
        )
        await repo.save(product)
        await repo.commit()

        # Find by ID
        found = await repo.find_by_id(product.id)
        assert found is not None
        assert found.id == product.id
        assert found.sku == "REPO-001"
