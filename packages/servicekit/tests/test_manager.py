from ulid import ULID

from chapkit import ConfigIn, ConfigManager, ConfigOut, ConfigRepository, SqliteDatabaseBuilder

from .conftest import DemoConfig


class TestBaseManager:
    """Tests for the ConfigManager class."""

    async def test_save_with_input_schema(self) -> None:
        """Test saving an entity using input schema."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create input schema
            config_in = ConfigIn[DemoConfig](name="test_config", data=DemoConfig(x=1, y=2, z=3, tags=["test"]))

            # Save and get output schema
            result = await manager.save(config_in)

            assert isinstance(result, ConfigOut)
            assert result.id is not None
            assert result.name == "test_config"
            assert result.data is not None
            assert isinstance(result.data, DemoConfig)
            assert result.data.x == 1
            assert result.data.y == 2
            assert result.data.z == 3
            assert result.data.tags == ["test"]

        await db.dispose()

    async def test_save_with_id_none_removes_id(self) -> None:
        """Test that save() removes id field when it's None."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create input schema with id=None (default)
            config_in = ConfigIn[DemoConfig](id=None, name="test", data=DemoConfig(x=1, y=2, z=3, tags=[]))

            result = await manager.save(config_in)

            # Should have a generated ID
            assert result.id is not None
            assert isinstance(result.id, ULID)

        await db.dispose()

    async def test_save_preserves_explicit_id(self) -> None:
        """Test that save() keeps a provided non-null ID intact."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            explicit_id = ULID()
            config_in = ConfigIn[DemoConfig](
                id=explicit_id,
                name="explicit_id_config",
                data=DemoConfig(x=5, y=5, z=5, tags=["explicit"]),
            )

            result = await manager.save(config_in)

            assert result.id == explicit_id
            assert result.name == "explicit_id_config"

        await db.dispose()

    async def test_save_all(self) -> None:
        """Test saving multiple entities using input schemas."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create multiple input schemas
            configs_in = [
                ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i * 2, z=i * 3, tags=[f"tag{i}"])) for i in range(3)
            ]

            # Save all
            results = await manager.save_all(configs_in)

            assert len(results) == 3
            assert all(isinstance(r, ConfigOut) for r in results)
            assert all(r.id is not None for r in results)
            assert results[0].name == "config0"
            assert results[1].name == "config1"
            assert results[2].name == "config2"

        await db.dispose()

    async def test_delete_by_id(self) -> None:
        """Test deleting an entity by ID."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create and save entity
            config_in = ConfigIn[DemoConfig](name="to_delete", data=DemoConfig(x=1, y=2, z=3, tags=[]))
            result = await manager.save(config_in)

            # Verify it exists
            assert await manager.count() == 1

            # Delete it
            assert result.id is not None
            await manager.delete_by_id(result.id)

            # Verify it's gone
            assert await manager.count() == 0

        await db.dispose()

    async def test_delete_all(self) -> None:
        """Test deleting all entities."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create multiple entities
            configs_in = [ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i, z=i, tags=[])) for i in range(5)]
            await manager.save_all(configs_in)

            # Verify they exist
            assert await manager.count() == 5

            # Delete all
            await manager.delete_all()

            # Verify all gone
            assert await manager.count() == 0

        await db.dispose()

    async def test_delete_many_by_ids(self) -> None:
        """Test deleting multiple entities by their IDs."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entities
            configs_in = [ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i, z=i, tags=[])) for i in range(5)]
            results = await manager.save_all(configs_in)

            # Delete some by ID
            assert results[1].id is not None
            assert results[3].id is not None
            to_delete = [results[1].id, results[3].id]
            await manager.delete_all_by_id(to_delete)

            # Should have 3 remaining
            assert await manager.count() == 3

        await db.dispose()

    async def test_delete_all_by_id_empty_list(self) -> None:
        """Test that delete_all_by_id with empty list does nothing."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entities
            configs_in = [ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i, z=i, tags=[])) for i in range(3)]
            await manager.save_all(configs_in)

            # Delete with empty list
            await manager.delete_all_by_id([])

            # All should still exist
            assert await manager.count() == 3

        await db.dispose()

    async def test_count(self) -> None:
        """Test counting entities through manager."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Initially empty
            assert await manager.count() == 0

            # Add entities
            configs_in = [ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i, z=i, tags=[])) for i in range(7)]
            await manager.save_all(configs_in)

            # Count should be 7
            assert await manager.count() == 7

        await db.dispose()

    async def test_output_schema_validation(self) -> None:
        """Test that output schemas are properly validated from ORM models."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entity with complex data
            config_in = ConfigIn[DemoConfig](
                name="validation_test",
                data=DemoConfig(x=10, y=20, z=30, tags=["production", "critical", "v2.0"]),
            )

            result = await manager.save(config_in)

            # Verify output schema is correct
            assert isinstance(result, ConfigOut)
            assert isinstance(result.id, ULID)
            assert result.name == "validation_test"
            assert result.data is not None
            assert isinstance(result.data, DemoConfig)
            assert result.data.x == 10
            assert result.data.y == 20
            assert result.data.z == 30
            assert result.data.tags == ["production", "critical", "v2.0"]

        await db.dispose()

    async def test_save_all_returns_list_of_output_schemas(self) -> None:
        """Test that save_all returns a list of output schemas."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            configs_in = [
                ConfigIn(name="config1", data=DemoConfig(x=1, y=1, z=1, tags=["a"])),
                ConfigIn(name="config2", data=DemoConfig(x=2, y=2, z=2, tags=["b"])),
            ]

            results = await manager.save_all(configs_in)

            assert isinstance(results, list)
            assert len(results) == 2
            assert all(isinstance(r, ConfigOut) for r in results)
            assert all(r.id is not None for r in results)

        await db.dispose()

    async def test_manager_commits_after_save(self) -> None:
        """Test that manager commits changes after save."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            config_in = ConfigIn[DemoConfig](name="committed", data=DemoConfig(x=1, y=2, z=3, tags=[]))
            await manager.save(config_in)

            # Check in a new session that it was committed
            async with db.session() as session2:
                repo2 = ConfigRepository(session2)
                manager2 = ConfigManager[DemoConfig](repo2, DemoConfig)
                assert await manager2.count() == 1

        await db.dispose()

    async def test_manager_commits_after_delete(self) -> None:
        """Test that manager commits changes after delete."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        # Save in one session
        async with db.session() as session1:
            repo1 = ConfigRepository(session1)
            manager1 = ConfigManager[DemoConfig](repo1, DemoConfig)
            config_in = ConfigIn[DemoConfig](name="to_delete", data=DemoConfig(x=1, y=2, z=3, tags=[]))
            result = await manager1.save(config_in)
            assert result.id is not None
            saved_id = result.id

        # Delete in another session
        async with db.session() as session2:
            repo2 = ConfigRepository(session2)
            manager2 = ConfigManager[DemoConfig](repo2, DemoConfig)
            await manager2.delete_by_id(saved_id)

            # Verify in yet another session
            async with db.session() as session3:
                repo3 = ConfigRepository(session3)
                manager3 = ConfigManager[DemoConfig](repo3, DemoConfig)
                assert await manager3.count() == 0

        await db.dispose()

    async def test_find_by_id(self) -> None:
        """Test finding an entity by ID through manager."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entity
            config_in = ConfigIn[DemoConfig](name="findable", data=DemoConfig(x=10, y=20, z=30, tags=["test"]))
            saved = await manager.save(config_in)

            # Find by ID
            assert saved.id is not None
            found = await manager.find_by_id(saved.id)

            assert found is not None
            assert isinstance(found, ConfigOut)
            assert found.id == saved.id
            assert found.name == "findable"
            assert found.data is not None
            assert found.data.x == 10

            # Non-existent ID should return None
            random_id = ULID()
            not_found = await manager.find_by_id(random_id)
            assert not_found is None

        await db.dispose()

    async def test_find_all(self) -> None:
        """Test finding all entities through manager."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entities
            configs_in = [
                ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i * 2, z=i * 3, tags=[f"tag{i}"])) for i in range(5)
            ]
            await manager.save_all(configs_in)

            # Find all
            all_configs = await manager.find_all()

            assert len(all_configs) == 5
            assert all(isinstance(c, ConfigOut) for c in all_configs)
            assert all(c.id is not None for c in all_configs)

        await db.dispose()

    async def test_find_all_by_id(self) -> None:
        """Test finding multiple entities by IDs through manager."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entities
            configs_in = [ConfigIn(name=f"config{i}", data=DemoConfig(x=i, y=i, z=i, tags=[])) for i in range(5)]
            results = await manager.save_all(configs_in)

            # Find by specific IDs
            assert results[0].id is not None
            assert results[2].id is not None
            assert results[4].id is not None
            target_ids = [results[0].id, results[2].id, results[4].id]
            found = await manager.find_all_by_id(target_ids)

            assert len(found) == 3
            assert all(isinstance(c, ConfigOut) for c in found)
            assert all(c.id in target_ids for c in found)

        await db.dispose()

    async def test_exists_by_id(self) -> None:
        """Test checking if entity exists by ID through manager."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entity
            config_in = ConfigIn[DemoConfig](name="exists_test", data=DemoConfig(x=1, y=2, z=3, tags=[]))
            saved = await manager.save(config_in)

            # Should exist
            assert saved.id is not None
            assert await manager.exists_by_id(saved.id) is True

            # Random ID should not exist
            random_id = ULID()
            assert await manager.exists_by_id(random_id) is False

        await db.dispose()

    async def test_find_by_name_handles_missing(self) -> None:
        """Test that find_by_name returns schema when found and None otherwise."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            assert await manager.find_by_name("unknown") is None

            config_in = ConfigIn[DemoConfig](name="known", data=DemoConfig(x=7, y=8, z=9, tags=["known"]))
            saved = await manager.save(config_in)

            assert saved.id is not None

            found = await manager.find_by_name("known")
            assert found is not None
            assert found.id == saved.id
            assert isinstance(found.data, DemoConfig)

        await db.dispose()

    async def test_output_schema_includes_timestamps(self) -> None:
        """Test that output schemas include created_at and updated_at timestamps."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            repo = ConfigRepository(session)
            manager = ConfigManager[DemoConfig](repo, DemoConfig)

            # Create entity
            config_in = ConfigIn[DemoConfig](name="timestamp_test", data=DemoConfig(x=1, y=2, z=3, tags=[]))
            result = await manager.save(config_in)

            # Verify timestamps exist
            assert result.created_at is not None
            assert result.updated_at is not None
            assert result.id is not None

        await db.dispose()
