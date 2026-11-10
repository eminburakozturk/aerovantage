/**
 * Tarayıcı tarafı API tabanı — same-origin BFF proxy.
 * Bearer secret burada yoktur; auth `app/api/backend` route'unda eklenir.
 */
const API_ROOT = "/api/backend";
const API_BASE_URL = `${API_ROOT}/api/v1`;

export { API_BASE_URL, API_ROOT };
