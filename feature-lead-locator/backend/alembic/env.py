from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.platform.database.base import Base
from app.platform.database.config import settings

# Import ORM models so they are attached to Base.metadata
from app.models import *  # noqa: F403,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata

# PostGIS ships its own tables that are not in Base.metadata: spatial_ref_sys
# and the geometry_columns/geography_columns views in `public`, plus whole
# `tiger` and `topology` schemas from the postgis_tiger_geocoder / topology
# extensions the postgis image installs at initdb.
#
# Without this filter, `alembic revision --autogenerate` emits drop_table() for
# every one of them (verified: it tried to drop 'edges', 'county_lookup', ...).
# Applying that would break PostGIS. Filter them out of comparison entirely.
POSTGIS_SCHEMAS = {"tiger", "tiger_data", "topology"}
POSTGIS_PUBLIC_TABLES = {
    "spatial_ref_sys",
    "geometry_columns",
    "geography_columns",
    "raster_columns",
    "raster_overviews",
}


def include_object(object_, name, type_, reflected, compare_to):  # noqa: ANN001
    if getattr(object_, "schema", None) in POSTGIS_SCHEMAS:
        return False
    if type_ == "table" and name in POSTGIS_PUBLIC_TABLES:
        return False
    # Spatial indexes on PostGIS-owned tables come along for the ride.
    if type_ == "index" and getattr(object_, "table", None) is not None:
        table = object_.table
        if table.schema in POSTGIS_SCHEMAS or table.name in POSTGIS_PUBLIC_TABLES:
            return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # The postgis_tiger_geocoder extension rewrites the database's
        # search_path to '"$user", public, topology, tiger'. Alembic reflects
        # the *search_path*, so without pinning it autogenerate sees every
        # tiger/topology table as an unqualified table missing from the models
        # and emits drop_table() for all ~40 of them. They also arrive with
        # schema=None, so a schema-name filter alone cannot catch them.
        #
        # Pinned via libpq's -c at connect time, NOT by issuing `SET
        # search_path` on the connection: under SQLAlchemy 2.0 that statement
        # implicitly opens a transaction before alembic's own
        # begin_transaction(), so alembic's commit lands on a nested
        # transaction and every migration silently rolls back at close —
        # logging "Running upgrade" and exiting 0 while writing nothing.
        connect_args={"options": "-csearch_path=public"},
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()