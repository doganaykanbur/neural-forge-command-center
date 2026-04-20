# TASK_PLAN.md — Phase 2: Implementation

> Goal: Atomic ticket generation for Builder Agents.

## [Ticket #1] Database Migration
**Priority:** 1 (Critical)
**Status:** Queued
**Description:** Implement `users.sql` schema with normalized relations.
**Validation:** PostgreSQL syntax compliance.

## [Ticket #2] BCrypt User Hashing
**Priority:** 2 (High)
**Status:** Queued
**Description:** Sentezleme of BCrypt rounds=12 for password security.
**Constraint:** 0 architectural drift from AUTH_V2 spec.

## [Ticket #3] Unit Testing Suite
**Priority:** 3 (Normal)
**Status:** Queued
**Description:** 85% coverage for `/auth/login` endpoint.
**Agent:** Tester Role
