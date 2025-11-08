---
layout: default
title: Changelog
nav_order: 99
---

# Changelog

All notable changes to this project will be documented here.

## Unreleased

- **Feature**: Added a database backend to store and track extraction jobs, schedules, and application configuration. This includes new tables for jobs, schedules, and configuration, as well as a `DatabaseManager` to handle CRUD operations.
- **Feature**: Implemented a two-tiered testing strategy with mocked API tests and isolated database tests using a temporary SQLite database.
- **Feature**: Added a new `/config` endpoint to the API for managing application configuration.
- **Update**: Updated the API for job and schedule management to include database-generated IDs and timestamps.
- Documentation refactor: new navigation, Operations guide, improved landing page links

## 0.1.0 - Initial release

- Initial multi-cloud extractors and FastAPI service
