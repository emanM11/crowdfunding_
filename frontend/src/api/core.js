import api from "./axios";

// PROJECT_SPEC.md section 6 — core app endpoints.
export const listComments = (projectId, page = 1) =>
  api.get(`/projects/${projectId}/comments/`, { params: { page } });

export const addComment = (projectId, text) =>
  api.post(`/projects/${projectId}/comments/`, { text });

export const replyToComment = (commentId, text) =>
  api.post(`/comments/${commentId}/reply/`, { text });

export const rateProject = (projectId, value) =>
  api.post(`/projects/${projectId}/rate/`, { value });

export const reportContent = ({ project = null, comment = null, reason }) =>
  api.post("/reports/", { project, comment, reason });

export const getHomepage = () => api.get("/homepage/");

export const search = (q, page = 1) =>
  api.get("/search/", { params: { q, page } });
