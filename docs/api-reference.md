# API Reference

Complete API documentation for all chapkit modules, classes, and functions.

## Core Layer

Framework-agnostic infrastructure components.

### Database

::: chapkit.core.database

### Models

::: chapkit.core.models

### Repository

::: chapkit.core.repository

### Manager

::: chapkit.core.manager

### Schemas

::: chapkit.core.schemas

### Exceptions

::: chapkit.core.exceptions

### Scheduler

::: chapkit.core.scheduler

### Types

::: chapkit.core.types

### Logging

::: chapkit.core.logging

## FastAPI Layer

FastAPI-specific components for building web services.

### Service Builders

Service builder classes for composing FastAPI applications.

#### BaseServiceBuilder

::: chapkit.core.api.service_builder.BaseServiceBuilder

#### ServiceInfo

::: chapkit.core.api.service_builder.ServiceInfo

### Routers

Base router classes and generic routers.

#### Router

::: chapkit.core.api.router.Router

#### CrudRouter

::: chapkit.core.api.crud.CrudRouter

#### CrudPermissions

::: chapkit.core.api.crud.CrudPermissions

#### HealthRouter

::: chapkit.core.api.routers.HealthRouter

#### JobRouter

::: chapkit.core.api.routers.JobRouter

#### SystemRouter

::: chapkit.core.api.routers.SystemRouter

### App System

Static web application hosting system.

#### AppLoader

::: chapkit.core.api.app.AppLoader

#### AppManifest

::: chapkit.core.api.app.AppManifest

#### App

::: chapkit.core.api.app.App

#### AppManager

::: chapkit.core.api.app.AppManager

#### AppInfo

::: chapkit.core.api.app.AppInfo

### Authentication

API key authentication middleware and utilities.

#### APIKeyMiddleware

::: chapkit.core.api.auth.APIKeyMiddleware

### Middleware

Error handling and logging middleware.

::: chapkit.core.api.middleware

### Dependencies

FastAPI dependency injection functions.

::: chapkit.core.api.dependencies

### Pagination

Pagination helpers for collection endpoints.

::: chapkit.core.api.pagination

### Utilities

Utility functions for FastAPI applications.

::: chapkit.core.api.utilities

## Application Layer

High-level application orchestration.

### ServiceBuilder

Domain-aware service builder with module support.

::: chapkit.api.service_builder.ServiceBuilder

### MLServiceBuilder

Specialized builder for machine learning services.

::: chapkit.api.service_builder.MLServiceBuilder

### Dependencies

Application-level dependency injection functions.

::: chapkit.api.dependencies

## Domain Modules

Vertical slice modules with complete functionality.

### Config Module

Key-value configuration with JSON data support.

::: chapkit.modules.config

### Artifact Module

Hierarchical artifact tree storage.

::: chapkit.modules.artifact

### Task Module

Script execution template system.

::: chapkit.modules.task

### ML Module

Machine learning train and predict operations.

::: chapkit.modules.ml
