"""Core-only CLI example using Database, Repository, and Manager directly.

Demonstrates using chapkit.core without FastAPI for command-line tools, batch jobs,
or background workers. Shows direct database operations with custom entities.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID

from chapkit.core import BaseManager, BaseRepository, Database, Entity, EntityIn, EntityOut

# --------------------------------------------------------------------- Domain Model


class Product(Entity):
    """Product entity for inventory management."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str]
    price: Mapped[float]
    stock: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)


# --------------------------------------------------------------------- Schemas


class ProductIn(EntityIn):
    """Input schema for creating and updating products."""

    sku: str
    name: str
    price: float
    stock: int = 0
    active: bool = True


class ProductOut(EntityOut):
    """Output schema for product responses."""

    sku: str
    name: str
    price: float
    stock: int
    active: bool


# --------------------------------------------------------------------- Repository


class ProductRepository(BaseRepository[Product, ULID]):
    """Repository for product data access with custom queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize product repository with database session."""
        super().__init__(session, Product)

    async def find_by_sku(self, sku: str) -> Product | None:
        """Find a product by SKU."""
        from sqlalchemy import select

        stmt = select(self.model).where(self.model.sku == sku)
        result = await self.s.execute(stmt)
        return result.scalar_one_or_none()

    async def find_low_stock(self, threshold: int = 10) -> list[Product]:
        """Find products with stock below threshold."""
        from sqlalchemy import select

        stmt = select(self.model).where(self.model.stock < threshold).where(self.model.active.is_(True))
        result = await self.s.execute(stmt)
        return list(result.scalars().all())


# --------------------------------------------------------------------- Manager


class ProductManager(BaseManager[Product, ProductIn, ProductOut, ULID]):
    """Manager for product business logic with validation."""

    def __init__(self, repo: ProductRepository) -> None:
        """Initialize product manager with repository."""
        super().__init__(repo, Product, ProductOut)
        self.repo: ProductRepository = repo

    async def find_by_sku(self, sku: str) -> ProductOut | None:
        """Find a product by SKU and return output schema."""
        product = await self.repo.find_by_sku(sku)
        return self._to_output_schema(product) if product else None

    async def find_low_stock(self, threshold: int = 10) -> list[ProductOut]:
        """Find products with low stock."""
        products = await self.repo.find_low_stock(threshold)
        return [self._to_output_schema(p) for p in products]

    async def restock(self, product_id: ULID, quantity: int) -> ProductOut:
        """Add stock to a product."""
        product = await self.repo.find_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        product.stock += quantity
        await self.repo.save(product)
        return self._to_output_schema(product)


# --------------------------------------------------------------------- Application Logic


async def main() -> None:
    """Demonstrate direct database usage with custom entities."""
    # Initialize database (in-memory for demo)
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()

    try:
        async with db.session() as session:
            repo = ProductRepository(session)
            manager = ProductManager(repo)

            # Create sample products
            print("Creating products...")
            laptop = await manager.save(
                ProductIn(
                    sku="LAPTOP-001",
                    name="Professional Laptop",
                    price=1299.99,
                    stock=15,
                )
            )
            print(f"✓ Created: {laptop.name} (SKU: {laptop.sku}, Stock: {laptop.stock})")

            mouse = await manager.save(
                ProductIn(
                    sku="MOUSE-001",
                    name="Wireless Mouse",
                    price=29.99,
                    stock=5,
                )
            )
            print(f"✓ Created: {mouse.name} (SKU: {mouse.sku}, Stock: {mouse.stock})")

            keyboard = await manager.save(
                ProductIn(
                    sku="KEYBOARD-001",
                    name="Mechanical Keyboard",
                    price=149.99,
                    stock=8,
                )
            )
            print(f"✓ Created: {keyboard.name} (SKU: {keyboard.sku}, Stock: {keyboard.stock})")

            # Find by SKU
            print("\nFinding product by SKU...")
            found = await manager.find_by_sku("LAPTOP-001")
            if found:
                print(f"✓ Found: {found.name} - ${found.price}")

            # Find low stock products
            print("\nFinding low stock products (threshold: 10)...")
            low_stock = await manager.find_low_stock(threshold=10)
            for product in low_stock:
                print(f"  ⚠ Low stock: {product.name} (SKU: {product.sku}, Stock: {product.stock})")

            # Restock a product
            print(f"\nRestocking {mouse.name}...")
            restocked = await manager.restock(mouse.id, 20)
            print(f"✓ Restocked: {restocked.name} - New stock: {restocked.stock}")

            # List all products
            print("\nAll products:")
            all_products = await manager.find_all()
            for product in all_products:
                status = "✓" if product.stock >= 10 else "⚠"
                print(f"  {status} {product.name}: ${product.price} (Stock: {product.stock})")

            # Stats
            total_count = await manager.count()
            print(f"\n✓ Total products: {total_count}")

    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
