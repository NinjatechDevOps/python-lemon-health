# Admin Panel API Reference

This document lists all API endpoints available for the admin panel, including their HTTP methods, paths, request/response schemas, and concise descriptions for integration with the admin web UI.

---

## 1. Admin Login

- **Endpoint:** `POST /login`
- **Request Body:**
  - `mobile_number` (string): Admin mobile number
  - `password` (string): Admin password
- **Response:** JWT tokens and admin user info

**Description:**
Authenticate an admin user using their mobile number and password. On success, returns access and refresh tokens for session management. Use these tokens for all subsequent admin API calls.

---

## 2. Dashboard Statistics

- **Endpoint:** `GET /dashboard/stats`
- **Query Params (optional):**
  - `duration` (string): `today`, `week`, `month`, or `custom`
  - `start_date` (string, YYYY-MM-DD): For custom range
  - `end_date` (string, YYYY-MM-DD): For custom range
- **Response:** Key metrics (total users, active users, etc.)
- **Auth:** Requires admin JWT

**Description:**
Fetches key statistics for the admin dashboard, such as total users, active users, and new users in selected timeframes. Useful for displaying summary metrics on the admin home page.

---

## 3. List Users

- **Endpoint:** `GET /users`
- **Query Params:**
  - `page` (int, default 1): Page number
  - `per_page` (int, default 20): Users per page
  - `search` (string, optional): Search by name, mobile, or email
  - `is_active` (bool, optional): Filter by active status
  - `is_verified` (bool, optional): Filter by verification status
  - `start_date`/`end_date` (string, optional): Filter by registration date
- **Response:** Paginated list of users
- **Auth:** Requires admin JWT

**Description:**
Returns a paginated, filterable list of all users. Supports searching and filtering by status, verification, and registration date. Use for user management tables in the admin UI.

---

## 4. Get User Details

- **Endpoint:** `GET /users/{user_id}`
- **Path Param:**
  - `user_id` (int): ID of the user
- **Response:** User details
- **Auth:** Requires admin JWT

**Description:**
Fetches detailed information about a specific user by their ID. Use this to display user profiles or for editing user information in the admin panel.

---

## 5. Create User

- **Endpoint:** `POST /users`
- **Request Body:**
  - `first_name`, `last_name`, `mobile_number`, `country_code`, `password`, `email` (optional), `is_verified`
- **Response:** Created user info
- **Auth:** Requires admin JWT

**Description:**
Allows the admin to create a new user account directly from the admin panel. All required user details must be provided. The user is created as active and optionally verified.

---

## 6. Update User

- **Endpoint:** `PUT /users/{user_id}`
- **Path Param:**
  - `user_id` (int): ID of the user
- **Request Body:**
  - Any updatable user fields (see schema)
- **Response:** Updated user info
- **Auth:** Requires admin JWT

**Description:**
Enables the admin to update user details, including name, contact info, status, and verification. Only provided fields are updated. Use for user edit forms in the admin UI.

---

## 7. List Chat Histories

- **Endpoint:** `GET /chat/history`
- **Query Params:**
  - `page`, `per_page`, `search`, `user_id`, `prompt_type`, `start_date`, `end_date`
- **Response:** Paginated list of chat conversations
- **Auth:** Requires admin JWT

**Description:**
Returns a paginated list of all chat conversations, with filters for user, prompt type, and date. Useful for monitoring and reviewing user interactions with the system.

---

## 8. Get Chat History Detail

- **Endpoint:** `GET /chat/history/{conv_id}`
- **Path Param:**
  - `conv_id` (string): Conversation ID
- **Response:** Full conversation details and messages
- **Auth:** Requires admin JWT

**Description:**
Fetches the complete message history for a specific conversation, including all messages and metadata. Use this to display detailed chat logs in the admin interface.

---

## Authentication & Security
- All endpoints except `/login` require a valid admin JWT token in the `Authorization: Bearer <token>` header.
- Only users with `is_admin = true` can access these APIs.

---

## Notes for FE Integration
- Use the provided request/response schemas for constructing API calls.
- Handle pagination and filtering for list endpoints.
- Always check for `success` in the response before using the data.
- Use the `/login` endpoint to obtain tokens for all subsequent requests. 