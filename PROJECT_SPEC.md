# Crowdfunding Platform — Project Specification

## 1. Overview

A crowdfunding web platform for Egypt (similar to GoFundMe / Kickstarter, scoped to
the local market). Users create fundraising campaigns ("projects"), other users
donate, comment, rate, and report. Admins manage categories and featured projects.

## 2. Architecture

**Decoupled architecture** — two independent codebases in one repo:

```
/backend    -> Django + Django REST Framework (API only, no templates)
/frontend   -> React (consumes the API over HTTP)
```

- Backend and frontend are developed and run independently.
- Backend exposes JSON endpoints only. No server-rendered HTML pages.
- Auth is token-based (JWT via `djangorestframework-simplejwt`), not
  Django session/cookie login — React stores the access token and sends it
  in the `Authorization: Bearer <token>` header on every request.
- CORS must be enabled on the backend (`django-cors-headers`) so the React
  dev server (different port) can call the API during development.

## 3. Tech Stack

**Backend**
- Django + Django REST Framework
- PostgreSQL
- `djangorestframework-simplejwt` (auth tokens)
- `django-cors-headers` (CORS)
- Python

**Frontend**
- React (Vite recommended for setup speed)
- A routing library (`react-router-dom`)
- Axios for API calls, with the JWT attached automatically via an interceptor

## 4. Team & App Responsibilities

Team of 3 developers. Backend work is split by app; frontend is a single track:

| Person | Focus |
|--------|-------|
| Person 1 | Backend: `accounts` app |
| Person 2 | Backend: `projects` app + `core` app |
| Person 3 | Frontend: full React app |

This lets backend work (Person 1 + 2) proceed fully in parallel with
frontend work (Person 3), since once the API contract (section 6) is agreed
on paper, the React side can be built against the documented JSON shapes
before the real endpoints exist.

**`accounts` app is responsible for:**
Custom User, registration, activation, JWT authentication, profile
(view/edit/delete), password reset (bonus).

**`projects` app is responsible for:**
Category, Tag, Project, ProjectImage, Donation, project cancellation,
"my projects", "my donations".

**`core` app is responsible for:**
Comments, comment replies (bonus), ratings, reports, homepage aggregation,
search.

Git: one branch per feature (e.g. `feature/auth-registration`,
`feature/react-project-page`), merged into `develop`; `main` stays
stable/release-only. Backend and frontend changes should stay in separate
commits/PRs even when related, since they live in separate folders.

## 5. Data Model (`/backend`)

### 5.1 User (custom model, extends `AbstractUser`)
- `email` — unique, used as login identifier (`USERNAME_FIELD = "email"`)
- `first_name`, `last_name` (inherited)
- `password` (inherited)
- `phone_number` — must validate against Egyptian mobile format (starts with
  010/011/012/015, 11 digits total)
- `profile_picture` — image field
- `is_active` — **must default to False**; user cannot log in until email activation
- `activation_token` — random token generated at registration; must be
  generated securely (not guessable), and invalidated once used (cannot be
  reused after successful activation)
- `activation_token_created_at` — timestamp, used to expire the link after 24 hours
- `birthdate` — optional
- `facebook_profile` — optional URL
- `country` — optional

**Registration request fields:** `first_name`, `last_name`, `email`,
`password`, `confirm_password`, `phone_number`, `profile_picture`.
`confirm_password` is validation-only — it is **never stored** in the
database. The registration serializer must validate `password ==
confirm_password` and return a validation error if they don't match.

Business rules:
- On registration, send an activation email containing a link with the token
  (the link points to a **React route**, e.g. `/activate/<token>`, which on
  load calls a backend endpoint to actually activate the account).
- Link expires 24 hours after `activation_token_created_at`. If the user
  attempts activation after expiration, return a clear validation error
  (e.g. "activation link expired"). A resend-activation endpoint is a
  possible future addition, not required for the core scope.
- Login (JWT token endpoint) must reject users while `is_active=False`.
- Bonus: Facebook login.
- Bonus: password reset via emailed link.
- **Profile update**: user can edit all allowed fields except `email`. This
  must be enforced **server-side** in the serializer/view — the backend must
  ignore or reject any `email` value submitted in an update request,
  regardless of what the frontend sends or disables in its form.
- **Account deletion**: user can delete only their own account. Frontend
  shows a confirmation dialog first; bonus requires re-entering the current
  password, verified server-side (never trust frontend-only validation).
  Deletion strategy: `Project.creator`, `Donation.user`, `Comment.user`,
  `Rating.user`, and `Report.user` use `on_delete=models.PROTECT` or the
  account is **soft-deleted** (`is_active=False` + anonymized personal
  fields) rather than hard-deleted, so that donation history and project
  data are never silently destroyed by a user removing their account. Hard
  cascade delete is explicitly disallowed for this reason.

### 5.2 Category
- `name`, `slug` — managed by admins via Django admin (create/edit/delete).

### 5.3 Tag
- `name` — ManyToMany with Project.

### 5.4 Project
- `title`, `details`
- `category` — ForeignKey → Category
- `creator` — ForeignKey → User
- `tags` — ManyToMany → Tag
- `total_target` — DecimalField
- `start_date`, `end_date`
- `status` — choices: `running`, `cancelled`, `ended`
- `is_featured` — boolean, admin-controlled
- `created_at`

**Status rules** (see section 6 for how status is exposed via the API):
- **Running**: `status = running` AND `start_date <= now` AND `end_date >= now`.
- **Ended**: becomes ended once `now > end_date`.
- **Cancelled**: set only when the creator successfully cancels under the
  cancellation rule below — never automatic.
- Implementation strategy: store `status` as a field but treat `running` /
  `ended` as **derived at query/serialization time** from the date fields
  rather than relying on a scheduled job to flip it — this avoids stale or
  inconsistent status if a background task fails to run. A project's stored
  `status` field is only ever written to directly for the `cancelled` value;
  `running` vs `ended` is computed from the dates whenever the project is
  read. Cancelled and ended projects must never appear in the running
  projects slider.

**Cancellation rule:**
```
total_donations < total_target * 0.25
```
Exactly 25% (`total_donations == total_target * 0.25`) does **not** qualify
— only strictly less than 25% allows cancellation. Only the project creator
can cancel. `total_donations` must always be calculated **server-side**
(database aggregation over the `Donation` table) — never trust a total sent
by the frontend.

**Similar projects** (project detail response, max 4):
- Exclude the current project.
- Rank by number of shared tags, highest first.
- No duplicate projects in the result.
- Prefer running projects as a tiebreaker when shared-tag counts are equal.
- Never return more than 4.

Detail endpoint response must include: all project images (for the slider),
average rating, rating count, the authenticated user's own rating if any,
and the 4 similar projects above.

### 5.5 ProjectImage
- `project` — ForeignKey → Project
- `image`

Multiple images per project, uploaded via `multipart/form-data`.
**Chosen approach**: project creation is a single request — the project
fields, tags, and all images are submitted together in one
`multipart/form-data` POST to `/api/projects/`. This is simpler for the
frontend (one form, one submit) than a two-step create-then-upload flow, and
is straightforward to implement with a DRF serializer that accepts a list of
image files alongside the project fields.

### 5.6 Donation
- `user` — ForeignKey → User
- `project` — ForeignKey → Project
- `amount` — DecimalField (never `FloatField`)
- `created_at`

Business rules:
- User must be authenticated to donate.
- Cannot donate to a project that is `cancelled`, `ended`, or has not
  started yet (`start_date > now`) — i.e. donations are only accepted while
  the project is `running` per the definition in 5.4.
- `amount` must be greater than zero.
- **A project creator cannot donate to their own project.**

### 5.7 Comment
- `user` — ForeignKey → User
- `project` — ForeignKey → Project
- `text`
- `parent` — ForeignKey → self, nullable (threaded replies, bonus)
- `created_at`

### 5.8 Rating
- `user` — ForeignKey → User
- `project` — ForeignKey → Project
- `value` — integer, `1 <= value <= 5`
- unique together: (`user`, `project`)

If the same user rates the same project again, the backend must **update
the existing rating** rather than create a duplicate (i.e. the create
endpoint behaves as an upsert on this unique pair).

### 5.9 Report
- `user` — ForeignKey → User
- `project` — ForeignKey → Project, nullable
- `comment` — ForeignKey → Comment, nullable
- `reason` — text
- `created_at`

**Validation rule (enforced in the serializer):** a report must reference
**exactly one** target.
- Valid: `project` set, `comment` null (project report).
- Valid: `project` null, `comment` set (comment report).
- Invalid: both set.
- Invalid: both null.

## 6. Backend API Surface (`/backend`, DRF)

The endpoints and JSON field names below are the **exact, agreed contract**
between backend and frontend — not a flexible suggestion. If a field is
named `total_target` in one endpoint, it must be named `total_target`
everywhere it appears (never `target`, `target_amount`, or `goal` in another
endpoint). Renaming a documented field requires updating this document
first, not doing it ad hoc in code.

**Auth (`accounts` app)**
- `POST /api/auth/register/`
- `POST /api/auth/activate/<token>/`
- `POST /api/auth/token/` (login — returns JWT access + refresh)
- `POST /api/auth/token/refresh/`
- `POST /api/auth/password-reset/` (bonus)
- `GET/PUT /api/auth/profile/` (view/edit own profile, auth required; server
  rejects `email` changes — see 5.1)
- `DELETE /api/auth/profile/` (delete own account, auth required)

**Projects (`projects` app)**
- `GET/POST /api/projects/` (list is paginated; supports `?category=<slug>`
  filtering — see Category Browsing below)
- `GET/PUT /api/projects/<id>/` (PUT must verify the authenticated user is
  the project creator; includes images, avg rating, rating count, user's own
  rating, similar projects)
- `POST /api/projects/<id>/cancel/` (creator-only, enforces the 25% rule)
- `GET /api/projects/my-projects/` (paginated; all projects created by the
  authenticated user)
- `GET /api/categories/`
- `GET /api/categories/<slug>/projects/` (projects in a category, paginated —
  chosen over a `?category=` query param on the main list endpoint for a
  clean, bookmarkable category URL; `?category=<slug>` on `/api/projects/`
  is not additionally implemented, to avoid two ways of doing the same thing)
- `GET /api/tags/`

**Donations (`projects` app)**
- `POST /api/projects/<id>/donate/` (authenticated; enforces donation rules
  in 5.6)
- `GET /api/donations/my-donations/` (paginated; donation history of the
  authenticated user — response includes project id, project title, project
  image, donation amount, and donation date for each entry)

**Core (`core` app)**
- `GET/POST /api/projects/<id>/comments/` (paginated)
- `POST /api/comments/<id>/reply/` (bonus)
- `POST /api/projects/<id>/rate/` (authenticated; upserts per 5.8)
- `POST /api/reports/` (authenticated; enforces the exactly-one-target rule
  in 5.9)
- `GET /api/homepage/` (see Homepage below)
- `GET /api/search/?q=...` (paginated — see Search below)

**Search rules:** matches project `title` or any associated `tag` name,
case-insensitively. A project matching on both title and a tag must still
appear only **once** in the results (no duplicate rows from the join).

**Homepage (`GET /api/homepage/`) returns:**
- **Top rated slider**: up to 5 highest-rated **running** projects (per the
  running definition in 5.4). Ordered by average rating descending; when
  ratings tie, order by `created_at` descending as a deterministic
  tiebreaker.
- **Latest projects**: latest 5 projects, ordered by `created_at` descending.
- **Featured projects**: latest 5 projects with `is_featured=True`
  (admin-managed).
- **Categories**: full category list, for frontend category browsing.

### 6.1 Example request/response payloads

These are illustrative shapes to align both tracks before implementation —
exact field lists may be extended as needed, but existing field names must
not change once agreed.

**Register** — `POST /api/auth/register/`
```json
// request
{
  "first_name": "Mustafa",
  "last_name": "Khalil",
  "email": "mustafa@example.com",
  "password": "•••••••",
  "confirm_password": "•••••••",
  "phone_number": "01012345678"
}
// response (201)
{ "id": 1, "email": "mustafa@example.com", "is_active": false }
```

**Activate** — `POST /api/auth/activate/<token>/` → `{ "detail": "account activated" }`

**Login** — `POST /api/auth/token/`
```json
// request
{ "email": "mustafa@example.com", "password": "•••••••" }
// response
{ "access": "<jwt>", "refresh": "<jwt>" }
```

**Profile** — `GET /api/auth/profile/`
```json
{
  "id": 1, "email": "mustafa@example.com", "first_name": "Mustafa",
  "last_name": "Khalil", "phone_number": "01012345678",
  "profile_picture": "https://.../pic.jpg", "birthdate": null,
  "facebook_profile": null, "country": null
}
```

**Create project** — `POST /api/projects/` (`multipart/form-data`)
```
title, details, category, tags[], total_target, start_date, end_date,
images[] (multiple files)
```

**Project detail** — `GET /api/projects/<id>/`
```json
{
  "id": 5, "title": "...", "details": "...", "category": {"id":1,"name":"..."},
  "creator": {"id":1,"first_name":"..."}, "tags": ["health","kids"],
  "total_target": "250000.00", "start_date": "...", "end_date": "...",
  "status": "running", "images": ["url1","url2"],
  "average_rating": 4.3, "rating_count": 12, "my_rating": null,
  "similar_projects": [ /* up to 4 */ ]
}
```

**Donate** — `POST /api/projects/<id>/donate/`
```json
{ "amount": "500.00" }
```

**Create comment** — `POST /api/projects/<id>/comments/`
```json
{ "text": "...", "parent": null }
```

**Rate project** — `POST /api/projects/<id>/rate/`
```json
{ "value": 4 }
```

**Report** — `POST /api/reports/`
```json
{ "project": 5, "comment": null, "reason": "..." }
```

**Homepage** — `GET /api/homepage/`
```json
{
  "top_rated": [ /* up to 5 */ ], "latest": [ /* 5 */ ],
  "featured": [ /* 5 */ ], "categories": [ /* all */ ]
}
```

**Search** — `GET /api/search/?q=health` → paginated list of matching projects.

## 7. Authentication & JWT

Flow:
```
User submits login credentials
  -> POST /api/auth/token/
  -> backend returns { access, refresh }
  -> frontend stores both tokens
  -> axios interceptor attaches "Authorization: Bearer <access>" to every request
```

Token refresh:
```
Access token expires (401 received)
  -> frontend calls POST /api/auth/token/refresh/ with the refresh token
  -> receives a new access token
  -> retries the original request
```

Logout: frontend clears the stored tokens and resets auth context/state
client-side; no server-side session exists to invalidate (stateless JWT).

**Token storage decision**: tokens are stored in `localStorage` for this
project. This is a deliberate, documented tradeoff for an educational
project, not an oversight — `localStorage` is simple to implement but is
readable by any JavaScript running on the page, so it is vulnerable to XSS
if the frontend ever renders unsanitized user input. Mitigate by never
using `dangerouslySetInnerHTML` or unsanitized `innerHTML` with
user-provided content anywhere in the React app. (The alternative,
HttpOnly cookies, avoids the XSS token-theft risk but introduces CSRF
handling and stricter CORS configuration — out of scope for this project's
timeline.)

## 8. Permissions

| Action | Unauthenticated | Authenticated (non-owner) | Project creator |
|---|---|---|---|
| View projects/homepage/search | ✅ | ✅ | ✅ |
| Create project | ❌ | ✅ | — |
| Update project | ❌ | ❌ | ✅ (own project only) |
| Cancel project | ❌ | ❌ | ✅ (own project, 25% rule) |
| Donate | ❌ | ✅ (not own project) | ❌ (own project) |
| Comment | ❌ | ✅ | ✅ |
| Rate | ❌ | ✅ | ✅ |
| Report | ❌ | ✅ | ✅ |

`PUT /api/projects/<id>/` must check `request.user == project.creator`
server-side before allowing the update; a 403 is returned otherwise.

## 9. Validation & Error Responses

Use standard HTTP status codes consistently across the API:
- `400 Bad Request` — validation errors (e.g. password mismatch, invalid
  rating value, malformed report).
- `401 Unauthorized` — missing or invalid/expired JWT.
- `403 Forbidden` — authenticated but not permitted (e.g. non-creator
  attempting to update a project).
- `404 Not Found` — resource does not exist.

Error body formats:
```json
{ "detail": "You do not have permission to perform this action." }
```
```json
{ "field_name": ["Validation error message."] }
```

## 10. Pagination

Use DRF's standard pagination (e.g. `PageNumberPagination`) for any list
endpoint whose result set can grow unbounded:
- `/api/projects/`
- `/api/search/`
- `/api/categories/<slug>/projects/`
- `/api/projects/<id>/comments/`
- `/api/projects/my-projects/`
- `/api/donations/my-donations/`

The homepage endpoint's lists (`top_rated`, `latest`, `featured`) stay fixed
at their required sizes (5 or fewer) and are **not** paginated.

## 11. Query Performance

- Use `select_related` for ForeignKey lookups (e.g. `Project.category`,
  `Project.creator`, `Donation.project`).
- Use `prefetch_related` for many-to-many/reverse relations (e.g.
  `Project.tags`, `Project.images`, `Project.comments`).
- Compute `total_donations`, `average_rating`, and `rating_count` with
  database aggregation (`Sum`, `Avg`, `Count`) — never loop over querysets
  in Python to total these.
- Avoid N+1 queries on project list and detail views; verify with Django
  Debug Toolbar or `django.db.connection.queries` during development.

## 12. Date & Time

Django's timezone-aware datetime handling must be enabled
(`USE_TZ = True`), with `TIME_ZONE` set to an appropriate Egypt timezone
(`Africa/Cairo`). All comparisons involving `start_date`, `end_date`,
running-status checks, and activation-token expiry must use timezone-aware
`datetime` values (`django.utils.timezone.now()`), not naive `datetime.now()`.

## 13. Django Admin

Register and configure the admin for: `User`, `Category`, `Tag`, `Project`,
`ProjectImage`, `Donation`, `Comment`, `Rating`, `Report`.

Admins must be able to:
- **Categories**: create, edit, delete.
- **Projects**: view all projects, mark/unmark `is_featured`, view status.
- **Reports**: view reported projects and reported comments, review the
  submitted reason.

The admin interface is Django's built-in admin only — it is not exposed
through the React frontend unless explicitly implemented later.

## 14. Frontend Structure (`/frontend`)

Suggested React folder layout (Vite-based):
```
frontend/
  src/
    api/            -> axios instance + one file per resource (auth.js, projects.js, ...)
    components/      -> reusable UI
    pages/           -> route-level views
    context/          -> auth context (stores JWT, current user)
    App.jsx
    main.jsx
```

**Pages**: Home, Register, Login, Activation, Profile, My Projects,
My Donations, Create Project, Edit Project, Project List, Project Detail,
Category Projects, Search Results.

The Profile page displays: user profile information, "My Projects" (from
`/api/projects/my-projects/`), and "My Donations" (from
`/api/donations/my-donations/`).

**Reusable components**: ProjectCard, ProjectImageSlider, RatingStars,
DonationForm, CommentThread, ReportButton, SearchBar, CategoryList.

**Route guards**: the following routes/actions require an authenticated
user, and unauthenticated attempts must redirect to Login: Create Project,
Edit Project, Donate, Add Comment, Rate Project, Report, Profile,
My Projects, My Donations.

Activation page reads the token from the URL and calls the activation
endpoint on mount.

## 15. Build Order

Before any implementation:
1. Finalize the API contract (section 6) and example payloads (6.1).
2. Finalize model relationships (section 5).

Then:
3. **Backend setup**: Django + DRF + PostgreSQL connection,
   `django-cors-headers`, `.env` for secrets, apps `accounts` / `projects` /
   `core`.
4. **Frontend setup** (parallel): Vite React app scaffold, routing, axios
   instance, auth context — can start immediately against the documented
   JSON shapes in 6.1, before real endpoints exist.
5. **Custom User model**: set `AUTH_USER_MODEL` **before the first
   migration is ever run**. Do not start with Django's default `User` model
   and switch later — this is not a safe change to make mid-project.
   Then run `makemigrations` / `migrate`.
6. **Auth endpoints**: register (with confirm_password validation),
   activation, JWT login/refresh, profile (get/update with email locked,
   delete with soft-delete/protect strategy).
7. **Frontend auth screens**: register, login, activation landing page,
   profile page — wired to step 6.
8. **Category/Tag/Project/ProjectImage models + endpoints** (single-request
   multipart creation) + admin setup.
9. **Frontend**: project list, project detail page (slider, similar
   projects, rating display), create/edit-project forms.
10. **Donation endpoint + logic** (ownership + status checks, server-side
    total) + cancellation rule (strict `<25%`) + "my projects" / "my
    donations" endpoints + frontend donate flow + My Projects / My
    Donations pages.
11. **Comment/Rating/Report models + endpoints** (rating upsert, report
    exactly-one-target validation) + frontend comment thread, rating
    widget, report button.
12. **Homepage + category browsing + search endpoints** + frontend
    homepage (sliders, lists, category browsing, search bar).
13. Apply pagination, query-performance optimizations, and consistent
    error-response formatting across all list/detail endpoints.
14. **Bonus features** only after 1–13 are fully working: Facebook login,
    password reset, comment replies, threaded reports.

## 16. Explicit Notes

- Never use `FloatField` for money — always `DecimalField`.
- Egyptian phone number validation: custom Django validator on `phone_number`.
- The API contract (section 6) is shared and binding between backend and
  frontend developers — field names are not renamed ad hoc once agreed.
