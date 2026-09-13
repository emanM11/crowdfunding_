import api from "./axios";

// One function per endpoint from PROJECT_SPEC.md section 6 (accounts app).
export const register = (formData) =>
  api.post("/auth/register/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const activate = (uid, token) => api.post(`/auth/activate/${uid}/${token}/`);

export const login = (email, password) =>
  api.post("/auth/token/", { email, password });

export const refreshToken = (refresh) =>
  api.post("/auth/token/refresh/", { refresh });

export const requestPasswordReset = (email) =>
  api.post("/auth/password-reset/", { email });

export const confirmPasswordReset = (uid, token, password, confirm_password) =>
  api.post(`/auth/password-reset/confirm/${uid}/${token}/`, { password, confirm_password });

export const facebookLogin = (accessToken) =>
  api.post("/auth/facebook/", { access_token: accessToken });

export const getProfile = () => api.get("/auth/profile/");

export const updateProfile = (formData) =>
  api.put("/auth/profile/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const deleteAccount = (password) =>
  api.delete("/auth/profile/", { data: { password } });
