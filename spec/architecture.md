# Restaurant Waiter Agent — Architecture Specification

## 1. Architecture Overview

The system uses a monorepo architecture consisting of:

* FastAPI backend;
* PostgreSQL database;
* Google ADK-based AI agent;
* Telegram Bot integration;
* React dashboard;
* Tailwind CSS.

The database is the source of truth for business state.

```text
Customer
   │
   │ Scan QR
   ▼
Telegram
   │
   ▼
FastAPI
   │
   ├── Session / Table Services
   │
   └── Google ADK Agent
           │
           └── Explicit Tools
                   │
                   ▼
            Application Services
                   │
                   ▼
              PostgreSQL

React Dashboard
       │
       │ JWT
       ▼
    FastAPI
       │
       ▼
Application Services
       │
       ▼
 PostgreSQL
```

---

# 2. Technology Decisions

## 2.1 Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic

FastAPI is responsible for:

* REST API;
* Telegram webhook handling;
* business logic orchestration;
* authentication;
* agent tool backend;
* session management;
* background session/payment timeout processing.

---

## 2.2 Database

PostgreSQL is the primary persistent datastore.

PostgreSQL is the source of truth for:

* customers;
* menu;
* tables;
* sessions;
* orders;
* payments;
* favorites;
* preferences;
* memory;
* transactional analytics data.

---

## 2.3 AI Agent

Google ADK is used as the agent framework.

The AI agent is responsible for:

* conversational interaction;
* intent understanding;
* deciding which tools to use;
* preference discovery;
* personalized recommendation;
* customer-memory interaction;
* order drafting and confirmation flow.

The agent must not directly own transactional business state.

---

## 2.4 Customer Channel

Telegram is the customer-facing communication channel.

Telegram Bot API is used for:

* receiving customer messages;
* sending agent responses;
* receiving QR/deep-link entry;
* identifying Telegram customers.

---

## 2.5 Dashboard

Dashboard:

* React;
* Tailwind CSS.

Dashboard communicates with FastAPI through authenticated HTTP APIs.

---

# 3. Repository Architecture

```text
restaurant-waiter-agent/
│
├── .agents/
│   └── ...                     # Google Agents CLI workspace skills
│
├── .agents-cli-spec.md
│
├── spec/
│   ├── requirements.md
│   └── architecture.md
│
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   ├── repositories/
│   │   │   ├── auth/
│   │   │   └── main.py
│   │   └── tests/
│   │
│   └── dashboard/
│       ├── src/
│       └── package.json
│
├── agent/
│   ├── agents/
│   ├── tools/
│   ├── prompts/
│   └── tests/
│
├── migrations/
├── tests/
├── docker-compose.yml
├── AGENTS.md
└── README.md
```

---

# 4. Backend Layering

Backend follows:

```text
API Layer
    ↓
Application Service Layer
    ↓
Repository Layer
    ↓
PostgreSQL
```

Business rules must reside in application/domain services rather than API handlers or agent prompts.

---

# 5. AI Agent Boundary

The agent interacts with business functionality through explicit tools.

Required boundary:

```text
Agent
  ↓
Tool
  ↓
Application Service
  ↓
Repository
  ↓
PostgreSQL
```

Prohibited:

```text
Agent
  ↓
SQLAlchemy
  ↓
PostgreSQL
```

The agent must not receive unrestricted database credentials.

---

# 6. Trusted Runtime Context

Agent tools that operate on customer/session state must not accept customer identity as arbitrary LLM-generated data.

For example, the agent should not freely generate:

```text
customer_id
dining_session_id
table_id
```

as authoritative identity values.

Instead:

```text
Telegram Webhook
      ↓
Backend identifies:
- customer
- active session
- table
      ↓
Trusted runtime context
      ↓
ADK Agent / Tool execution
      ↓
Application Service
```

The backend/session runtime provides the authoritative customer and session context.

Tool-specific business parameters, such as menu ID and quantity, may still originate from the agent and must be validated by the application service.

---

# 7. QR and Table Reservation Architecture

Each table has a unique identifier represented in its QR code.

Flow:

```text
Customer
   ↓
Scan QR
   ↓
Telegram Deep Link
   ↓
FastAPI
   ↓
Validate Table
   ↓
Check Table Availability
   │
   ├── AVAILABLE
   │      ↓
   │   Create Session
   │      ↓
   │   OCCUPIED
   │
   └── OCCUPIED
          ↓
       Reject Session
```

A valid QR scan reserves/occupies the table immediately.

Table reservation and dining session creation must happen transactionally.

A customer cannot create another active session if they already have one.

---

# 8. Dining Session State

Conceptually:

```text
AVAILABLE
    │
    │ valid QR scan
    ▼
OCCUPIED
    │
    ├── /done
    │
    ├── automatic session timeout
    │
    └── other explicit termination
           │
           ▼
       AVAILABLE
```

The table status is derived from authoritative session state or maintained transactionally with it.

---

# 9. Session Timeout Architecture

The session timeout is **not based on order creation time**.

The preferred anchor is the completion of the most recent order:

```text
last_order_completed_at
```

Expiration:

```text
expiration_at =
    last_order_completed_at + configured_session_timeout
```

Default:

```text
SESSION_AUTO_TERMINATE_MINUTES=30
```

If the session has never had an order:

```text
expiration_at =
    session.created_at + configured_session_timeout
```

Therefore:

```text
Order created
    ↓
ORDERED
    ↓
IN_PROGRESS
    ↓
DONE
    ↓
last_order_completed_at updated
    ↓
30-minute inactivity window starts
```

A new order that eventually reaches `DONE` resets the session inactivity window.

An order in `ORDERED` or `IN_PROGRESS` does not reset the completed-order inactivity anchor.

---

# 10. Payment Timeout Architecture

Payment timeout is separate from session timeout.

When an order reaches `DONE`:

```text
payment_status = UNPAID
payment_due_at =
    order.completed_at + configured_payment_timeout
```

Default:

```text
PAYMENT_TIMEOUT_MINUTES=10
```

Flow:

```text
Order
 ↓
DONE
 ↓
UNPAID
 ↓
10-minute payment window
 ↓
PAID?
 ├── Yes → Payment completed
 └── No  → Payment becomes overdue
```

After payment timeout:

* payment remains `UNPAID`;
* order remains persisted;
* payment is not automatically marked as paid;
* payment is not automatically cancelled;
* dashboard must expose the order as overdue.

Automatic cancellation is outside MVP.

---

# 11. Relationship Between Session and Payment Timeout

Session timeout and payment timeout are independent timers.

```text
Order DONE
   │
   ├───────────────┐
   │               │
   ▼               ▼
Session Timer    Payment Timer
30 minutes       10 minutes
   │               │
   ▼               ▼
Session          Payment
expiration       overdue
```

If a session is manually terminated while an unpaid order exists:

1. customer receives a warning;
2. customer explicitly confirms;
3. session may be completed;
4. table becomes available;
5. unpaid order remains persisted;
6. payment status remains `UNPAID`.

---

# 12. Order Architecture

Order creation:

```text
Customer
   ↓
Agent
   ↓
Order Draft
   ↓
Customer Confirmation
   ↓
create_order()
   ↓
Order Service
   ↓
PostgreSQL
```

The agent must not execute `create_order()` before explicit customer confirmation.

Order lifecycle:

```text
ORDERED
   ↓
IN_PROGRESS
   ↓
DONE
```

When an order becomes `DONE`, the backend transaction must update relevant session/payment timestamps.

---

### 12.1 Order Item Historical Snapshot

`OrderItem` must preserve the menu information that was effective at the time the order was created.

Conceptually:

```text
OrderItem
├── id
├── order_id
├── menu_item_id
├── name
├── quantity
├── unit_price
├── subtotal
└── notes

# 13. Customer Memory Architecture

Customer memory is persistent and customer-scoped.

Example model:

```text
CustomerMemory
├── id
├── customer_id
├── type
├── description
├── metadata
├── created_at
└── updated_at
```

Example:

```text
type:
preference

description:
Customer menyukai makanan gurih dan tidak terlalu pedas.
```

`description` allows memory to represent natural-language information without requiring every memory type to have a dedicated database column.

Structured metadata may be used when deterministic filtering is required.

The agent accesses memory through explicit tools.

---

## 14. Menu Data Architecture

Menu data is persisted in PostgreSQL and managed through separate application and repository layers.

### 14.1 Menu Categories

Menu categories are persistent entities used to group menu items.

Each category contains at minimum:

* `id`;
* `name`;
* `description`.

Category names must be unique within the restaurant.

Category management is an administrative operation and must be protected by the existing Admin JWT authentication boundary.

### 14.2 Category Management

The Admin Dashboard must retrieve categories from the backend and must not maintain a hardcoded list of category names.

The category management flow is:

```text
Admin Dashboard
       |
       v
GET /api/admin/categories
       |
       v
Category Service
       |
       v
Category Repository
       |
       v
PostgreSQL
```

Administrators can:

* view categories;
* create categories;
* update category name and description;
* delete categories that are not referenced by menu items.

Category deletion must be validated by the backend.

A category that is still referenced by one or more menu items must not be deleted if doing so would orphan the menu items. The backend must reject the deletion and return a clear validation error.

The system must not silently orphan menu items.

### 14.3 Menu Category Selection

When creating or editing a menu item, the Admin Dashboard must retrieve the available categories from the backend.

```text
Admin Dashboard
       |
       +-- GET /api/admin/categories
       |
       v
Category List
       |
       v
Menu Create/Edit Form
       |
       v
category_id
       |
       v
Menu API
```

Category names must not be hardcoded in the frontend.

A category created through Category Management must automatically become available as a selectable category for menu creation and editing.

The backend remains the authoritative source for category data and validation.

### 14.4 Menu and Category Relationship

Each menu item may reference a menu category through `category_id`.

The relationship is maintained by PostgreSQL and must preserve referential integrity.

```text
MenuCategory
    |
    | 1 : N
    v
MenuItem
```

Category deletion rules must be enforced at the application layer and must not depend solely on frontend validation.

Customer-facing Telegram and Google ADK Agent components must not have access to administrative category management operations.

---

# 15. Retrieval Architecture

Structured PostgreSQL retrieval is the default mechanism.

Examples:

```text
"Menu di bawah 50 ribu"
        ↓
PostgreSQL filter

"Menu yang sedang tersedia"
        ↓
PostgreSQL filter

"Menu ayam yang tidak pedas"
        ↓
PostgreSQL structured query
```

Semantic/vector retrieval is not required for MVP.

If semantic retrieval becomes necessary later, it can be introduced without changing the core transactional architecture.

No vector database or embedding infrastructure should be introduced solely for the initial menu retrieval requirements.

---

# 16. Telegram Architecture

```text
Customer
   ↓
Telegram
   ↓
Telegram Webhook
   ↓
FastAPI
   ↓
Resolve Customer + Session Context
   ↓
Google ADK Agent
   ↓
Agent Tools
   ↓
Application Services
```

Telegram identity is used for customer identification.

Telegram identity must not provide dashboard authentication.

---

# 17. Dashboard Architecture

```text
React Dashboard
      │
      │ JWT
      ▼
FastAPI API
      │
      ▼
Application Services
      │
      ▼
PostgreSQL
```

Dashboard modules:

* Login;
* Dashboard;
* Menu;
* Orders;
* Tables;
* Customers;
* Analytics.

---

# 18. Authentication Architecture

Dashboard authentication uses JWT.

```text
Admin
  ↓
Login
  ↓
FastAPI
  ↓
Password verification
  ↓
JWT
  ↓
Protected API requests
```

All administrative endpoints must validate JWT authentication.

---

# 19. Background Timeout Processing

MVP should use a lightweight background mechanism for timeout processing.

The system must process:

* session inactivity timeout;
* payment timeout.

No Redis/Celery infrastructure is required for MVP.

The timeout processor must be idempotent.

A timeout operation must not modify an entity that has already transitioned into a terminal or otherwise incompatible state.

---

# 20. Concurrency and Data Integrity

The backend must enforce:

* at most one active session per table;
* at most one active session per customer;
* order creation only for active sessions;
* no new orders after session completion;
* transactional table reservation.

Table reservation must be safe against concurrent QR scans.

---

# 21. Analytics Architecture

Analytics are derived from transactional data.

Popular menu:

```text
OrderItem
   ↓
GROUP BY menu_id
   ↓
COUNT
```

Table usage:

```text
DiningSession
   ↓
GROUP BY table_id
   ↓
COUNT
```

Analytics are not the source of truth for transactional state.

---

# 22. Security Architecture

Security boundaries:

```text
Customer
   ↓
Telegram
   ↓
Agent
   ↓
Backend Tools
```

and:

```text
Admin
   ↓
JWT
   ↓
Dashboard API
```

Requirements:

* passwords must be securely hashed;
* dashboard APIs require authentication;
* customer cannot access admin endpoints;
* agent cannot access arbitrary database operations;
* payment confirmation requires admin authorization;
* business state changes must be validated server-side.

---

# 23. Development Workflow

Google Agents CLI is installed at workspace scope.

```text
.agents/
```

contains Google Agents CLI skills/context available to the coding agent.

Project specification entry point:

```text
.agents-cli-spec.md
```

Detailed specifications:

```text
spec/
├── requirements.md
└── architecture.md
```

Development flow:

```text
.agents-cli-spec.md
        ↓
requirements.md
        ↓
architecture.md
        ↓
implementation plan
        ↓
implementation
        ↓
tests
        ↓
evaluation
```

Google Agents CLI skills provide development guidance and workflow support but do not override the approved project requirements or architecture.

---

# 24. Future Improvements

The following are intentionally deferred:

* Telegram inline keyboard/button confirmation;
* online payment gateway;
* automatic payment cancellation;
* advanced semantic/vector retrieval;
* advanced recommendation model;
* Redis/Celery-based scheduling;
* advanced staff roles;
* multi-restaurant support.

---

# 25. Architectural Principles

1. PostgreSQL is the source of truth.
2. Google ADK owns agent orchestration, not business state.
3. Agent tools are the boundary between AI reasoning and business operations.
4. Business rules belong in backend application services.
5. The agent must never have unrestricted database access.
6. Structured menu data uses PostgreSQL retrieval by default.
7. Customer memory is persistent and customer-scoped.
8. QR scan immediately reserves an available table.
9. Table reservation must be concurrency-safe.
10. Session timeout is based on the last completed order.
11. Payment timeout is separate from session timeout.
12. Session timeout defaults to 30 minutes.
13. Payment timeout defaults to 10 minutes.
14. Payment timeout does not automatically cancel or mark payment as paid.
15. Dashboard authentication is independent of Telegram identity.
16. The project remains a monorepo.
17. Additional infrastructure should only be introduced when justified by requirements.
