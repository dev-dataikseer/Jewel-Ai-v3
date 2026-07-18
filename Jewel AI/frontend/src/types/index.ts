export type JsonSchemaProperty = {
  type?: string;
  title?: string;
  description?: string;
  enum?: string[];
  minimum?: number;
  maximum?: number;
  default?: unknown;
};

export type JsonSchema = {
  type?: string;
  properties?: Record<string, JsonSchemaProperty>;
};

export type ModelInfo = {
  rank?: number;
  model_category?: string;
  architecture?: string;
  key_strengths?: string;
  tags?: string;
  pricing?: string;
  max_resolution?: string;
  multi_image_support?: string;
  aspect_ratios?: string;
};

export type ModelUiMeta = {
  provider: string;
  provider_label: string;
  tasks: string[];
  docs_url?: string | null;
  pricing_note?: string | null;
  supports_edit: boolean;
  supports_i2i: boolean;
  supports_t2i: boolean;
  badge?: string | null;
  max_images: number;
  min_images: number;
  max_prompt_chars?: number | null;
  recommended_max_prompt_chars?: number | null;
  official_max_prompt_chars?: number | null;
  official_prompt_status?: string | null;
};

export type ModelLimits = {
  min_images: number;
  max_images: number;
  max_prompt_chars?: number | null;
  recommended_max_prompt_chars?: number | null;
  official_max_prompt_chars?: number | null;
  official_prompt_status?: string | null;
  official_prompt_note?: string | null;
};

export type ModelDefinition = {
  endpoint_id: string;
  display_name: string;
  provider: string;
  category: string;
  capabilities: Record<string, boolean>;
  input_schema: JsonSchema;
  default_params: Record<string, unknown>;
  workflow_allowlist?: string[] | null;
  is_active: boolean;
  sort_order: number;
  cost_per_call?: number | null;
  model_info?: ModelInfo | null;
  ui?: ModelUiMeta | null;
  limits?: ModelLimits | null;
  family?: string | null;
};

export type Job = {
  id: string;
  workflow: string;
  status: string;
  prompt_text?: string | null;
  final_prompt?: string | null;
  jewelry_type?: string | null;
  metal_type?: string | null;
  gemstone_target_color?: string | null;
  background_style?: string | null;
  lighting_style?: string | null;
  input_url?: string | null;
  reference_url?: string | null;
  model_url?: string | null;
  output_url?: string | null;
  output_urls?: string[] | null;
  asset_id?: string | null;
  error_message?: string | null;
  provider_used?: string | null;
  provider_model?: string | null;
  provider_metadata?: Record<string, unknown> | null;
  master_version_id?: string | null;
  subject_version_id?: string | null;
  variant_version_id?: string | null;
  credits_used?: number;
  cost?: number | null;
  retry_count?: number;
  processing_started_at?: string | null;
  batch_id?: string | null;
  project_id?: string | null;
  user_id?: string | null;
  created_at: string;
  updated_at?: string;
  favorite?: boolean;
};

export type Asset = {
  id: string;
  original_url: string;
};

export type StylePreset = {
  id: string;
  name: string;
  workflow?: string | null;
  description?: string | null;
  prompt_addon: string;
  is_active?: boolean;
};

export type PromptLayer = {
  key: string;
  label: string;
  description?: string | null;
  order: number;
  enabled?: boolean;
  content?: string | null;
  locked?: boolean;
  type: "text" | "negative" | "insert_point" | "variant_insert" | "user_insert";
  priority?: "critical" | "important" | "optional";
  settings?: Record<string, unknown> | null;
  is_system?: boolean;
};

export type PromptTemplate = {
  id: string;
  name: string;
  workflow: string;
  prompt_text?: string | null;
  is_active: boolean;
  composition_mode?: string;
  layers?: PromptLayer[];
  active_version_id?: string | null;
};

export type SubjectPrompt = {
  id: string;
  workflow: string;
  jewelry_type: string;
  prompt_text?: string | null;
  is_active: boolean;
  composition_mode?: string;
  layers?: PromptLayer[];
  active_version_id?: string | null;
};

export type PromptVariant = {
  id: string;
  workflow: string;
  variant_key: string;
  label: string;
  prompt_text: string;
  is_active: boolean;
};

export type PromptVersion = {
  id: string;
  version: number;
  is_active: boolean;
  created_at?: string | null;
  prompt_text?: string | null;
  layers?: PromptLayer[];
};

export type StructuralLayerConfig = {
  key: string;
  label: string;
  type: string;
  priority?: string;
  enabled?: boolean;
  is_system?: boolean;
  after_key?: string | null;
};

export type WorkflowLayerConfig = {
  workflow: string;
  structural_layers: StructuralLayerConfig[];
};

export type Provider = {
  id: string;
  name: string;
  display_name: string;
  model_name: string;
  priority: number;
  is_active: boolean;
  health_status: string;
  has_api_key: boolean;
  has_admin_api_key?: boolean;
  capabilities?: Record<string, unknown>;
};

export type RateEntry = {
  id: string;
  rate_type: string;
  metal_type?: string | null;
  diamond_shape?: string | null;
  diamond_color?: string | null;
  diamond_clarity?: string | null;
  carat?: string | null;
  value: number;
  currency: string;
  city?: string | null;
  updated_at?: string;
  created_at?: string;
};

export type User = {
  id: string;
  email: string;
  name?: string | null;
  role: string;
  credits?: number;
};

export type AdminMetrics = {
  jobs: number;
  completed: number;
  failed: number;
  assets: number;
  batches: number;
  favorites: number;
  success_rate: number;
  recent_failures: Array<{
    id: string;
    workflow: string;
    error?: string | null;
    created_at?: string;
  }>;
};

export type UsageAnalytics = {
  window_days: number;
  summary: {
    total_jobs: number;
    completed: number;
    failed: number;
    pending: number;
    processing: number;
    success_rate: number;
    estimated_cost_usd_all_time: number;
    estimated_cost_usd_completed: number;
    estimated_cost_usd_window: number;
    jobs_in_window: number;
    status_counts: Record<string, number>;
    status_counts_window: Record<string, number>;
  };
  by_model: Array<{
    model: string;
    provider: string;
    total: number;
    completed: number;
    failed: number;
    pending: number;
    processing: number;
    estimated_cost_usd: number;
  }>;
  by_workflow: Array<{
    workflow: string;
    total: number;
    completed: number;
    failed: number;
    estimated_cost_usd: number;
  }>;
  by_user: Array<{
    user_id?: string | null;
    email: string;
    total: number;
    completed: number;
    failed: number;
    estimated_cost_usd: number;
  }>;
  by_day: Array<{
    date: string;
    total: number;
    completed: number;
    failed: number;
    estimated_cost_usd: number;
  }>;
  live_jobs: Array<{
    id: string;
    status: string;
    workflow: string;
    model?: string | null;
    user_email?: string | null;
    created_at?: string | null;
    processing_started_at?: string | null;
  }>;
  recent_jobs: Array<{
    id: string;
    status: string;
    workflow: string;
    jewelry_type?: string | null;
    provider?: string | null;
    model?: string | null;
    estimated_cost_usd?: number | null;
    user_email?: string | null;
    error_message?: string | null;
    retry_count: number;
    has_output: boolean;
    created_at?: string | null;
    updated_at?: string | null;
    processing_started_at?: string | null;
    duration_ms?: number | null;
  }>;
  notes?: string[];
};

export type ConfigOptions = {
  workflows: { id: string; label: string }[];
  jewelryTypes: string[];
  modelsEndpoint?: string;
  aspectRatios?: string[];
  gemstoneColors?: string[];
  backgroundStyles?: string[];
  metalTypes?: string[];
  lightingStyles?: string[];
};

export type JobsListResponse = {
  items: Job[];
  next_cursor: string | null;
};

export const WORKFLOWS = [
  { id: "CATALOG_IMAGE", label: "Catalog Image", bulk: true },
  { id: "VIRTUAL_TRY_ON", label: "Virtual Try-On", bulk: true },
  { id: "JEWELRY_ON_MODEL", label: "Jewelry On Model", bulk: true },
  { id: "GEMSTONE_COLOR_CHANGE", label: "Gemstone Color Change", bulk: true },
  { id: "CUSTOMER_TRY_ON", label: "Customer Try-On", bulk: true },
  { id: "REFERENCE_STYLE_MATCH", label: "Style from Reference", bulk: true },
  { id: "BACKGROUND_REPLACEMENT", label: "Background Replacement", bulk: true },
  { id: "LUXURY_ENHANCEMENT", label: "Luxury Enhancement", bulk: true },
  { id: "CUSTOM_PROMPT", label: "Custom Prompt", bulk: true },
  { id: "BULK_GENERATION", label: "Bulk Generation", bulk: true },
  { id: "RATE_TOOLS", label: "Rate Tools", bulk: false },
] as const;

/** Studio sidebar entries — consolidated UX (no Rates/Bulk pseudo-workflows). */
export const STUDIO_SIDEBAR_WORKFLOWS = [
  { id: "CATALOG_IMAGE", label: "Catalog Image" },
  { id: "VIRTUAL_TRY_ON", label: "Virtual Try-On" },
  { id: "GEMSTONE_COLOR_CHANGE", label: "Gemstone Color Change" },
  { id: "REFERENCE_STYLE_MATCH", label: "Style from Reference" },
  { id: "BACKGROUND_REPLACEMENT", label: "Background Replacement" },
  { id: "LUXURY_ENHANCEMENT", label: "Luxury Enhancement" },
  { id: "CUSTOM_PROMPT", label: "Custom Prompt" },
] as const;

export const HISTORY_WORKFLOW_FILTERS = [
  { id: "", label: "All workflows" },
  { id: "CATALOG_IMAGE", label: "Catalog Image" },
  { id: "JEWELRY_ON_MODEL", label: "Jewelry On Model" },
  { id: "CUSTOMER_TRY_ON", label: "Customer Try-On" },
  { id: "GEMSTONE_COLOR_CHANGE", label: "Gemstone Color Change" },
  { id: "REFERENCE_STYLE_MATCH", label: "Style from Reference" },
  { id: "BACKGROUND_REPLACEMENT", label: "Background Replacement" },
  { id: "LUXURY_ENHANCEMENT", label: "Luxury Enhancement" },
  { id: "CUSTOM_PROMPT", label: "Custom Prompt" },
] as const;

export function workflowLabel(id: string, options?: ConfigOptions) {
  const fromApi = options?.workflows?.find((w) => w.id === id)?.label;
  if (fromApi) return fromApi;
  return WORKFLOWS.find((w) => w.id === id)?.label || id.replaceAll("_", " ");
}

export function label(value?: string | null) {
  return (value || "Workflow")
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
