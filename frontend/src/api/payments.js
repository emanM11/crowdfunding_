import api from "./axios";

// PROJECT_SPEC.md 5.6 — payment endpoints. The checkout modal picks between
// the Stripe Elements flow and the offline sandbox based on the gateway the
// backend reports; card data never travels through these calls in Stripe
// mode (it is tokenized in the browser).

export const getPaymentGatewayConfig = () => api.get("/payments/config/");

export const processDonation = (projectId, payload) =>
  api.post(`/projects/${projectId}/donate/process/`, payload);

export const confirmDonation = (projectId, paymentIntentId) =>
  api.post(`/projects/${projectId}/donate/confirm/`, { payment_intent_id: paymentIntentId });