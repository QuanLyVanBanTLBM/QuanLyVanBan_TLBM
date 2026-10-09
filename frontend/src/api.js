import apiClient, { apiClientBlob } from "./lib/apiClient";

const apiPath = (path) => `/api${path}`;

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient(apiPath("/upload"), { method: "POST", body: formData });
}

export async function uploadDocumentAsync(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient(apiPath("/upload/async"), { method: "POST", body: formData });
}

export async function getUploadProgress(jobId) {
  return apiClient(apiPath(`/upload/progress/${encodeURIComponent(jobId)}`));
}

export async function askQuestion(question, history = [], category = null) {
  const payload = { question, history };
  if (category) payload.category = category;
  return apiClient.post(apiPath("/chat"), payload);
}

export async function getDocuments() {
  return apiClient(apiPath("/documents"));
}

export async function getCategories() {
  return apiClient(apiPath("/categories"));
}

export async function deleteDocuments() {
  return apiClient.delete(apiPath("/documents"));
}

export async function deleteDocument(filename) {
  return apiClient.delete(apiPath(`/documents/${encodeURIComponent(filename)}`));
}

export async function reclassifyDocument(filename) {
  return apiClient.post(apiPath(`/reclassify/${encodeURIComponent(filename)}`));
}

export async function previewDocument(filename) {
  return apiClient(apiPath(`/documents/${encodeURIComponent(filename)}/preview`));
}

export async function getDocumentFile(filename) {
  return apiClientBlob(apiPath(`/documents/${encodeURIComponent(filename)}/file`));
}

export async function getAISettings() {
  return apiClient(apiPath("/settings/ai"));
}

export async function updateAISettings(settings) {
  return apiClient.post(apiPath("/settings/ai"), settings);
}
