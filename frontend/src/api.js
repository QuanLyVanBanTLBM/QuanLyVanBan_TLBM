import apiClient, { apiClientBlob, apiClientStream } from "./lib/apiClient";

const apiPath = (path) => `/api/ai${path}`;

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient(apiPath("/upload"), { method: "POST", body: formData });
}

export async function uploadDocumentAsync(file, replaceExisting = false) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("replace_existing", String(replaceExisting));
  return apiClient(apiPath("/upload/async"), { method: "POST", body: formData });
}

export async function getUploadProgress(jobId) {
  return apiClient(apiPath(`/upload/progress/${encodeURIComponent(jobId)}`));
}

export async function askQuestion(question, history = [], category = null, filename = null, language = null) {
  const payload = { question, history };
  if (category) payload.category = category;
  if (filename) payload.filename = filename;
  const lang = language || (typeof window !== "undefined" ? localStorage.getItem("tlbm_lang") : null) || "vi";
  payload.language = lang;
  return apiClient.post(apiPath("/chat"), payload);
}

export async function askQuestionStream(
  question,
  {
    history = [],
    category = null,
    filename = null,
    language = null,
    signal = null,
    onSources = null,
    onDelta = null,
    onDone = null,
  } = {}
) {
  const payload = { question, history };
  if (category) payload.category = category;
  if (filename) payload.filename = filename;
  const lang = language || (typeof window !== "undefined" ? localStorage.getItem("tlbm_lang") : null) || "vi";
  payload.language = lang;

  const response = await apiClientStream(apiPath("/chat/stream"), {
    method: "POST",
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.body) {
    throw new Error("ReadableStream is not supported by this browser");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let fullAnswer = "";
  let sources = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";

    for (const rawEvent of events) {
      if (!rawEvent.trim()) continue;
      let eventType = "message";
      let dataStr = "";

      for (const line of rawEvent.split("\n")) {
        if (line.startsWith("event: ")) {
          eventType = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          dataStr = line.slice(6);
        }
      }

      if (!dataStr) continue;
      let parsed = null;
      try {
        parsed = JSON.parse(dataStr);
      } catch {
        parsed = dataStr;
      }

      if (eventType === "sources") {
        sources = Array.isArray(parsed) ? parsed : [];
        onSources?.(sources);
      } else if (eventType === "delta") {
        const delta = typeof parsed === "object" && parsed !== null ? parsed.text || "" : String(parsed);
        fullAnswer += delta;
        onDelta?.(delta, fullAnswer);
      } else if (eventType === "done") {
        if (typeof parsed === "object" && parsed !== null && parsed.answer) {
          fullAnswer = parsed.answer;
        }
        if (typeof parsed === "object" && parsed !== null && Array.isArray(parsed.sources)) {
          sources = parsed.sources;
        }
        onDone?.({ answer: fullAnswer, sources });
      } else if (eventType === "error") {
        const errMessage = typeof parsed === "object" && parsed !== null ? parsed.error : String(parsed);
        throw new Error(errMessage || "Stream error");
      }
    }
  }

  return { answer: fullAnswer, sources };
}

export async function getDocuments() {
  return apiClient(apiPath("/documents"));
}

export async function getCategories() {
  return apiClient(apiPath("/categories"));
}

export async function deleteDocuments(confirmation) {
  return apiClient.delete(apiPath("/documents"), {
    body: JSON.stringify({ confirmation }),
  });
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
  return apiClient(apiPath("/settings"));
}

export async function updateAISettings(settings) {
  return apiClient.post(apiPath("/settings"), settings);
}
