import React, { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { getAISettings, updateAISettings } from "../api";
import { useTranslation } from "../i18n/translate";

export default function AISettingsModal({ onClose, onSaved }) {
  const { t } = useTranslation();
  const [provider, setProvider] = useState("gemini");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [llmModel, setLlmModel] = useState("gemini-3.8-flash");

  const [currentConfig, setCurrentConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const dialogRef = useRef(null);
  const savingRef = useRef(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const selector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
    const getFocusable = () => Array.from(dialog?.querySelectorAll(selector) || []);
    getFocusable()[0]?.focus();
    document.body.style.overflow = "hidden";

    const handleTab = (event) => {
      if (event.key !== "Tab" || !dialog) return;
      const focusable = getFocusable();
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleTab);
    return () => {
      document.removeEventListener("keydown", handleTab);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, []);

  // Lắng nghe phím Escape để đóng modal thuận tiện
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && !savingRef.current) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, saving]);

  async function fetchSettings() {
    setLoading(true);
    try {
      const data = await getAISettings();
      setCurrentConfig(data);
      if (data.provider) setProvider(data.provider);
      const availableModels = data.model_options?.[data.provider]?.llm_models || [];
      setLlmModel(availableModels.includes(data.llm_model) ? data.llm_model : availableModels[0] || "");
    } catch (err) {
      console.error("Lỗi khi tải cấu hình:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    savingRef.current = true;
    setSaving(true);
    setMessage(null);

    const payload = {
      provider,
      api_key: apiKey.trim() || undefined,
      llm_model: llmModel.trim() || undefined,
    };

    try {
      const res = await updateAISettings(payload);
      setMessage({
        type: "success",
        key: "aiSettingsModal.saveSuccess",
      });
      setApiKey("");
      await fetchSettings();
      window.dispatchEvent(new CustomEvent("tlbm_ai_config_updated", { detail: res }));
      if (onSaved) onSaved(res);
    } catch (err) {
      const errorCode = err.data?.code;
      const supportedErrors = [
        "provider_not_supported",
        "api_key_required",
        "model_not_supported",
        "provider_switch_reindex_required",
        "model_access_denied",
        "embedding_access_denied",
        "invalid_api_key",
        "provider_unavailable",
      ];
      setMessage({
        type: "danger",
        key: supportedErrors.includes(errorCode)
          ? `aiSettingsModal.errors.${errorCode}`
          : "aiSettingsModal.saveFailed",
      });
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  const modalContent = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-4 md:p-6 overflow-y-auto animate-in fade-in duration-150">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={saving ? undefined : onClose}
      />

      {/* Modal Dialog Card */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-settings-dialog-title"
        tabIndex={-1}
        className="relative bg-surface border border-border-subtle rounded-2xl shadow-2xl w-[680px] max-w-full flex flex-col max-h-[92vh] my-auto overflow-hidden animate-in zoom-in-95 duration-150 z-10"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle bg-surface-elevated/40 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-primary to-primary-hover text-white flex items-center justify-center text-lg shadow-sm shrink-0">
              <i className="fa-solid fa-microchip" />
            </div>
            <div>
              <h3 id="ai-settings-dialog-title" className="text-base font-bold text-main m-0">
                {t("aiSettingsModal.title")}
              </h3>
              <p className="text-xs text-muted m-0 mt-0.5">
                {t("aiSettingsModal.subtitle")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="w-8 h-8 rounded-lg text-muted hover:text-main hover:bg-hover flex items-center justify-center transition-colors cursor-pointer disabled:opacity-50"
            title={t("aiSettingsModal.close")}
            aria-label={t("aiSettingsModal.close")}
          >
            <i className="fa-solid fa-xmark text-sm" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-5 custom-scrollbar">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-muted">
              <i className="fa-solid fa-circle-notch fa-spin text-2xl text-primary" />
              <span className="text-sm font-medium">{t("aiSettingsModal.loading")}</span>
            </div>
          ) : (
            <form onSubmit={handleSave} className="space-y-5">
              {/* Alert Feedback Banner */}
              {message && (
                <div
                  className={`rounded-xl p-3.5 flex items-start gap-3 text-xs leading-relaxed transition-all ${
                    message.type === "success"
                      ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
                      : "bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-300"
                  }`}
                  role="alert"
                >
                  <i
                    className={`fa-solid ${
                      message.type === "success" ? "fa-circle-check" : "fa-triangle-exclamation"
                    } text-base shrink-0 mt-0.5`}
                  />
                  <div className="flex-1 font-medium">{t(message.key)}</div>
                </div>
              )}

              {/* Engine Status Banner */}
              <div className="bg-surface-elevated/70 border border-border-subtle rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-[11px] font-semibold text-secondary uppercase tracking-wider block mb-1">
                    {t("aiSettingsModal.running")}
                  </span>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${
                        currentConfig?.provider === "openai"
                          ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                          : "bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30"
                      }`}
                    >
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                      {currentConfig?.provider === "gemini"
                        ? "Google Gemini"
                        : currentConfig?.provider === "openai"
                        ? "OpenAI"
                        : t("aiSettingsModal.notConfigured")}
                    </span>
                    <span className="text-xs text-main font-mono font-semibold bg-surface px-2.5 py-1 rounded-md border border-border-subtle">
                      {t("aiSettingsModal.currentModel", { model: currentConfig?.llm_model || t("aiSettingsModal.notConfigured") })}
                    </span>
                  </div>
                </div>

                {currentConfig?.api_key_masked_by_provider?.[provider] ? (
                  <div className="sm:text-right">
                    <span className="text-[11px] text-muted block mb-0.5">{t("aiSettingsModal.currentApiKey")}</span>
                    <code className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 bg-surface px-2.5 py-1 rounded-md border border-border-subtle inline-block">
                      {currentConfig.api_key_masked_by_provider[provider]}
                    </code>
                  </div>
                ) : (
                  <div className="sm:text-right">
                    <span className="inline-flex items-center gap-1.5 text-xs text-amber-500 font-medium bg-amber-500/10 px-2.5 py-1 rounded-md border border-amber-500/20">
                      <i className="fa-solid fa-triangle-exclamation text-[11px]" />
                      {t("aiSettingsModal.missingApiKey")}
                    </span>
                  </div>
                )}
              </div>

              {/* Step 1: Provider Selection */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-secondary mb-2.5 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[11px] font-bold">
                    1
                  </span>
                  <span>{t("aiSettingsModal.providerStep")}</span>
                </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5" role="radiogroup" aria-label={t("aiSettingsModal.providerStep")}>
                  {/* Google Gemini Card */}
                  <div
                    role="radio"
                    aria-checked={provider === "gemini"}
                    tabIndex={provider === "gemini" ? 0 : -1}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setProvider("gemini");
                        setLlmModel(currentConfig?.model_options?.gemini?.llm_models?.[0] || "");
                      } else if (["ArrowRight", "ArrowDown"].includes(event.key)) {
                        event.preventDefault();
                        setProvider("openai");
                        setLlmModel(currentConfig?.model_options?.openai?.llm_models?.[0] || "");
                        dialogRef.current?.querySelector('[role="radio"][aria-checked="false"]')?.focus();
                      } else if (["ArrowLeft", "ArrowUp"].includes(event.key)) {
                        event.preventDefault();
                        setProvider("openai");
                        setLlmModel(currentConfig?.model_options?.openai?.llm_models?.[0] || "");
                        dialogRef.current?.querySelectorAll('[role="radio"]')[1]?.focus();
                      }
                    }}
                    onClick={() => {
                      setProvider("gemini");
                      setLlmModel(currentConfig?.model_options?.gemini?.llm_models?.[0] || "");
                    }}
                    className={`relative p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      provider === "gemini"
                        ? "border-primary bg-primary/5 shadow-xs ring-1 ring-primary/20"
                        : "border-border-subtle bg-surface hover:border-primary/40 hover:bg-hover/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2.5">
                        <span className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-sky-400 text-white flex items-center justify-center text-sm shadow-xs shrink-0">
                          <i className="fa-solid fa-wand-magic-sparkles" />
                        </span>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 min-w-0">
                          <strong className="text-main text-sm block">Google Gemini</strong>
                          <span className="inline-block bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                            {t("aiSettingsModal.geminiRecommended")}
                          </span>
                        </div>
                      </div>
                      <div className="pt-0.5">
                        {provider === "gemini" ? (
                          <i className="fa-solid fa-circle-check text-primary text-base" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border-2 border-border-subtle" />
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted leading-relaxed m-0">
                      {t("aiSettingsModal.geminiDescription")}
                    </p>
                  </div>

                  {/* OpenAI Card */}
                  <div
                    role="radio"
                    aria-checked={provider === "openai"}
                    tabIndex={provider === "openai" ? 0 : -1}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setProvider("openai");
                        setLlmModel(currentConfig?.model_options?.openai?.llm_models?.[0] || "");
                      } else if (["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"].includes(event.key)) {
                        event.preventDefault();
                        setProvider("gemini");
                        setLlmModel(currentConfig?.model_options?.gemini?.llm_models?.[0] || "");
                        dialogRef.current?.querySelectorAll('[role="radio"]')[0]?.focus();
                      }
                    }}
                    onClick={() => {
                      setProvider("openai");
                      setLlmModel(currentConfig?.model_options?.openai?.llm_models?.[0] || "");
                    }}
                    className={`relative p-4 rounded-xl border-2 transition-all cursor-pointer ${
                      provider === "openai"
                        ? "border-emerald-500 bg-emerald-500/5 shadow-xs ring-1 ring-emerald-500/20"
                        : "border-border-subtle bg-surface hover:border-emerald-500/40 hover:bg-hover/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2.5">
                        <span className="w-9 h-9 rounded-lg bg-gradient-to-tr from-emerald-600 to-teal-400 text-white flex items-center justify-center text-sm shadow-xs shrink-0">
                          <i className="fa-solid fa-robot" />
                        </span>
                        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 min-w-0">
                          <strong className="text-main text-sm block">OpenAI</strong>
                          <span className="inline-block bg-secondary-subtle text-secondary text-[10px] font-bold px-2 py-0.5 rounded-full">
                            {t("aiSettingsModal.openaiBadge")}
                          </span>
                        </div>
                      </div>
                      <div className="pt-0.5">
                        {provider === "openai" ? (
                          <i className="fa-solid fa-circle-check text-emerald-500 text-base" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border-2 border-border-subtle" />
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted leading-relaxed m-0">
                      {t("aiSettingsModal.openaiDescription")}
                    </p>
                  </div>
                </div>
              </div>

              {/* Step 2: API Key & Model Configuration */}
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-secondary mb-2.5 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[11px] font-bold">
                    2
                  </span>
                  <span>{t("aiSettingsModal.credentialsStep")}</span>
                </label>

                <div className="bg-surface-elevated/40 border border-border-subtle rounded-xl p-4 sm:p-5 space-y-4">
                  {/* API Key Field */}
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <label
                        htmlFor="ai-api-key-input"
                        className="text-xs font-bold text-main flex items-center gap-1.5"
                      >
                        <i className="fa-solid fa-key text-primary text-xs" />
                        <span>{provider === "gemini" ? t("aiSettingsModal.geminiApiKey") : t("aiSettingsModal.openaiApiKey")}</span>
                        <span className="text-danger">*</span>
                      </label>
                      <a
                        href={
                          provider === "gemini"
                            ? "https://aistudio.google.com/app/apikey"
                            : "https://platform.openai.com/api-keys"
                        }
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-semibold text-primary hover:text-primary-hover hover:underline inline-flex items-center gap-1.5 transition-colors"
                      >
                        <i className="fa-solid fa-arrow-up-right-from-square text-[10px]" />
                        <span>
                          {provider === "gemini"
                            ? t("aiSettingsModal.getGeminiKey")
                            : t("aiSettingsModal.getOpenAiKey")}
                        </span>
                      </a>
                    </div>

                    <div className="relative flex items-center">
                      <div className="absolute left-3.5 text-muted pointer-events-none flex items-center justify-center text-sm">
                        <i className="fa-solid fa-lock" />
                      </div>
                      <input
                        id="ai-api-key-input"
                        type={showKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={
                          currentConfig?.api_keys?.[provider]
                            ? `${t("aiSettingsModal.maskedKey")} (${t("aiSettingsModal.keepExistingKey")})`
                            : provider === "gemini"
                            ? t("aiSettingsModal.pasteGeminiKey")
                            : t("aiSettingsModal.pasteOpenAiKey")
                        }
                        className="w-full text-sm bg-surface border border-border-subtle rounded-xl pl-10 pr-24 py-2.5 text-main font-mono placeholder:text-muted/60 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all shadow-2xs"
                        spellCheck={false}
                        autoComplete="off"
                      />
                      <button
                        type="button"
                        onClick={() => setShowKey(!showKey)}
                        className="absolute right-2 px-2.5 py-1 text-xs font-semibold rounded-lg text-secondary hover:text-main hover:bg-hover flex items-center gap-1.5 transition-colors cursor-pointer border border-border-subtle/70"
                        title={showKey ? t("aiSettingsModal.hideKey") : t("aiSettingsModal.showKey")}
                      >
                        <i className={`fa-solid ${showKey ? "fa-eye-slash" : "fa-eye"} text-xs`} />
                        <span>{showKey ? t("aiSettingsModal.hideKey") : t("aiSettingsModal.showKey")}</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 text-[11px] text-muted mt-2">
                      <i className="fa-solid fa-shield-halved text-emerald-500 text-xs shrink-0" />
                      <span>
                        {t("aiSettingsModal.keyStorage")}
                      </span>
                    </div>
                  </div>

                  {/* Models Configuration (LLM & Embedding) */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 pt-3 border-t border-border-subtle/60">
                    {/* LLM Model Select */}
                    <div>
                      <label
                        htmlFor="ai-llm-select"
                        className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5"
                      >
                        <i className="fa-solid fa-microchip text-primary text-xs" />
                        <span>{t("aiSettingsModal.llmModel")}</span>
                      </label>
                      <div className="relative">
                        <select
                          id="ai-llm-select"
                          value={llmModel}
                          onChange={(e) => setLlmModel(e.target.value)}
                          className="w-full text-sm bg-surface border border-border-subtle rounded-xl px-3.5 py-2.5 text-main appearance-none pr-9 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all cursor-pointer font-medium shadow-2xs"
                        >
                          {(currentConfig?.model_options?.[provider]?.llm_models || []).map((model, index) => (
                            <option key={model} value={model}>
                              {model}{index === 0 ? ` (${t("aiSettingsModal.recommended")})` : ""}
                            </option>
                          ))}
                        </select>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-muted text-xs">
                          <i className="fa-solid fa-chevron-down" />
                        </div>
                      </div>
                    </div>

                    {/* Embedding Model Box */}
                    <div>
                      <label className="block text-xs font-semibold text-secondary mb-1.5 flex items-center gap-1.5">
                        <i className="fa-solid fa-network-wired text-indigo-500 text-xs" />
                        <span>{t("aiSettingsModal.embeddingModel")}</span>
                      </label>
                      <div
                        className="w-full min-w-0 bg-hover/70 border border-border-subtle rounded-xl px-3.5 py-2.5 text-secondary shadow-2xs flex flex-wrap items-center justify-between gap-2"
                        aria-label={`${t("aiSettingsModal.embeddingModel")}: ${currentConfig?.model_options?.[provider]?.embed_model || currentConfig?.embed_model || ""}`}
                        title={currentConfig?.model_options?.[provider]?.embed_model || currentConfig?.embed_model || ""}
                      >
                        <code className="min-w-0 max-w-full break-all text-xs font-mono">
                          {currentConfig?.model_options?.[provider]?.embed_model || currentConfig?.embed_model || ""}
                        </code>
                        <span className="shrink-0 px-2 py-0.5 rounded-md text-[10px] font-bold font-mono bg-surface border border-border-subtle text-muted flex items-center gap-1">
                          <i className="fa-solid fa-lock text-[9px]" />
                          <span>{provider === "gemini" ? t("aiSettingsModal.geminiDimensions") : t("aiSettingsModal.openAiDimensions")}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Footer Buttons */}
              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-border-subtle shrink-0">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-semibold rounded-xl text-secondary hover:text-main hover:bg-hover border border-border-subtle transition-all cursor-pointer disabled:opacity-50"
                >
                  {t("aiSettingsModal.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 text-sm font-bold rounded-xl text-white bg-primary hover:bg-primary-hover shadow-sm hover:shadow-glow hover:-translate-y-0.5 active:scale-[0.98] transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                >
                  {saving ? (
                    <>
                      <i className="fa-solid fa-circle-notch fa-spin text-sm" />
                      <span>{t("aiSettingsModal.activating")}</span>
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-circle-check text-sm" />
                      <span>{t("aiSettingsModal.activate")}</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );

  return typeof window !== "undefined" ? createPortal(modalContent, window.document.body) : modalContent;
}
