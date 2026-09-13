import api from "./axios";

// PROJECT_SPEC.md section 6 — projects app endpoints.
export const listProjects = (page = 1) =>
  api.get("/projects/", { params: { page } });

export const getProject = (id) => api.get(`/projects/${id}/`);

export const createProject = (formData) =>
  api.post("/projects/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const updateProject = (id, formData) =>
  api.put(`/projects/${id}/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const cancelProject = (id) => api.post(`/projects/${id}/cancel/`);

export const myProjects = (page = 1) =>
  api.get("/projects/my-projects/", { params: { page } });

export const listCategories = () => api.get("/categories/");

export const categoryProjects = (slug, page = 1) =>
  api.get(`/categories/${slug}/projects/`, { params: { page } });

export const listTags = () => api.get("/tags/");

export const myDonations = (page = 1) =>
  api.get("/donations/my-donations/", { params: { page } });

export const projectUpdates = (projectId) => api.get(`/projects/${projectId}/updates/`);

export const addProjectUpdate = (projectId, { title, body }) =>
  api.post(`/projects/${projectId}/updates/`, { title, body });

export const projectRewards = (projectId) => api.get(`/projects/${projectId}/rewards/`);

export const addRewardTier = (projectId, data) =>
  api.post(`/projects/${projectId}/rewards/`, data);
