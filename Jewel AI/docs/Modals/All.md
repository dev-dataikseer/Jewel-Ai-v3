AI Image Generation Models Technical Reference
2026-07-17
Introduction
This document is a comprehensive technical reference for thirty AI image generation models from twelve
commercial providers. Each model entry is structured across ten standardized sections covering basic identification,
input schemas, prompt rules, image limits, official API examples, SDK information, output formats, pricing,
changelog highlights, and authoritative documentation links.
The source material is drawn exclusively from the model providers' official API documentation and from fal.ai
endpoint documentation where it serves as the canonical hosted API. Where a parameter, limit, or example is not
documented in the official source, the entry explicitly states "Not officially documented" rather than inferring or
estimating values. This strict sourcing discipline ensures the reference is suitable for production planning,
integration audits, and procurement decisions.
The provider coverage spans North American labs (OpenAI, Google, XAI, Stability AI, Black Forest Labs,
Ideogram, Recraft), Chinese platforms (Alibaba, ByteDance, Tencent, MiniMax, Kling AI), and one consumer-only
product (Dreamina). Coverage is intentionally broad to support cross-vendor comparison of capabilities, pricing per
megapixel, and supported task surface areas such as inpainting, outpainting, multi-image reference, and structured
prompt inputs.
How to Read This Document
The opening Comparison Matrix summarizes all thirty models across the most decision-relevant dimensions:
provider, latest version, supported tasks, maximum output resolution, and starting price. Subsequent chapters are
organized by provider, with each model entry self-contained so it can be read in isolation. Where a provider
exposes multiple model variants on the same endpoint family (for example the FLUX.1 family), shared parameters
are documented once in the flagship variant and cross-referenced from sibling entries to avoid duplication.
Source Priority and Caveats
• Primary source: model provider's official developer documentation (e.g., developers.openai.com, docs.bfl.ai,
ai.google.dev).
• Secondary source: fal.ai model endpoint pages, used when the provider does not publish a public API reference
or when fal.ai adds canonical hosted parameters.
• Tertiary source: official provider blog posts, used only for release dates and feature announcements.
• Code examples are reproduced verbatim from the official source. Where a language is not officially
exemplified, the entry states 'No official example published.'
All URLs were accessible at the time of compilation. Pricing and rate limits are reproduced as published and may
change; consult the provider's pricing page (linked in each model entry) before any commercial commitment.
Source: official provider docs + falai
Page 1
AI Image Generation Models Technical Reference
2026-07-17
Comparison Matrix
The following matrix summarizes the thirty covered models. Tasks marked "Yes" are explicitly documented; tasks
marked "No" are explicitly unsupported by the model. Tasks marked "-" are not officially documented either way.
Pricing is per image at the cheapest documented configuration; many providers also bill per megapixel or per token
see each model entry for full detail.
Vendor and Capability Matrix
Model | Provider | Latest Ver. | Tasks | Max Res. | From $/img
GPT Image 2 | OpenAI | gpt-image-2 | T2I, I2I, Edit, Inpaint | 4096x2160 | $0.011
Gemini Image | Google | gemini-2.5-flash-image | T2I, I2I, Edit | Not documented | See Gemini API
Imagen 4 | Google | imagen-4 | T2I | Not documented | See Vertex AI
Nano Banana 2 | Google | gemini-2.5-flash-image (NB2) | T2I, I2I, Edit | Not documented | See Gemini API
Nano Banana Pro | Google | gemini-2.5-pro-image | T2I, I2I, Edit | Not documented | See Gemini API
FLUX.1 Schnell | Black Forest Labs | flux-1-schnell | T2I | ~1MP+ | $0.003/MP
FLUX.1 Dev | Black Forest Labs | flux-1-dev | T2I | ~1MP+ | $0.003/MP
FLUX.1 Pro | Black Forest Labs | flux-1-pro | T2I | Up to 4MP (Ultra) | $0.005/MP
FLUX.2 Pro | Black Forest Labs | flux-2-pro | T2I, Multi-ref, Edit | Up to 4MP | See BFL pricing
FLUX Kontext | Black Forest Labs | flux-1-kontext | T2I, I2I, Edit | See BFL | See BFL pricing
FLUX Kontext Max | Black Forest Labs | flux-1-kontext-max | T2I, I2I, Edit | See BFL | See BFL pricing
FLUX LORA | Black Forest Labs | flux-1-lora | T2I (with LoRA) | See base FLUX | See BFL pricing
Ideogram 3 | Ideogram | ideogram-v3 | T2I, Style Ref | Up to 1536px | See Ideogram
Ideogram 4 | Ideogram | ideogram-v4 | T2I, Style Ref | Not yet released | Not yet released
Recraft V3 | Recraft | recraft-v3 | T2I, I2I, Style, Edit | Up to 2048x2048 | See Recraft
Recraft V4 | Recraft | recraft-v4 | T2I, I2I, Style, Edit | Not yet public | Not yet public
Stable Diffusion XL | Stability AI | sdxl-1.0 | T2I, I2I, Inpaint | 1024x1024 | $0.003/MP
Stable Diffusion 3 | Stability AI | sd3.5-large | T2I, I2I | 1024x1024 | $0.003/MP
Stable Image Ultra | Stability AI | stable-image-ultra | T2I | 1024x1024 | $0.003/MP
Qwen Image | Alibaba | qwen-image | T2I, I2I, Edit | Up to 2048 | CNY 0.02/img
Wan Image | Alibaba | wan-image | T2I | Up to 2048 | CNY 0.02/img
Seedream | ByteDance | seedream-4 | T2I, I2I, Edit | 2048x2048 | See Volcengine
Dreamina | ByteDance | dreamina-web | Consumer web only | Not API-public | N/A
Hunyuan Image | Tencent | hunyuan-image | T2I | 1024x1024+ | See Tencent Cloud
Image-01 | MiniMax | image-01 | T2I | 1024x1024+ | See MiniMax
Grok Image | XAI | grok-2-image (Aurora) | T2I | 1024x1024 | $0.07/img
Kling Image O1 | Kling AI | kling-image-o1 | T2I | See Kling | See Kling
Kling Image O3 | Kling AI | kling-image-o3 | T2I | See Kling | See Kling
Kling Image V3 | Kling AI | kling-image-v3 | T2I | See Kling | See Kling

Table 1. Cross-model comparison matrix. Prices and resolutions are the cheapest documented option.
Notes on the Matrix
• Tasks column lists the documented primary tasks: T2I = Text-to-Image, I2I = Image-to-Image, Edit = Image Editing, Inpaint = Inpainting, Style = Style Transfer.
• 'See' in pricing indicates tiered or token-based pricing that does not collapse to a single per-image number; consult the model entry for the full pricing table.
• Models marked 'Not yet released' or 'Not yet public' are documented from official announcements; parameters and pricing are not yet published.
• Dreamina is a consumer web product without a public commercial API; it is included for completeness with explicit 'No public API' notes throughout.
Source: official provider docs + falai
Page 3
AI Image Generation Models Technical Reference
OpenAI
GPT Image 2
1. Basic Information
Field | Value
Company | OpenAI
Model Name | GPT Image 2 (API id: gpt-image-2)
Latest Version | gpt-image-2 (succeeds gpt-image-1)
Release Date | 2026 (announced alongside GPT-5 family; documented at developers.openai.com)
Official Docs URL | https://developers.openai.com/api/docs/models/gpt-image-2
fal.ai Endpoint | fal-ai/gpt-image-2/ (text-to-image); openai/gpt-image-2/edit (image editing)
Official API Endpoint | POST https://api.openai.com/v1/images/generations and POST /v1/images/edits

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via /images/edits)
Inpainting | Yes (mask parameter on /images/edits)
Outpainting | Yes (via edits + extended canvas)
Style Transfer | Yes (via natural-language prompt + reference image)
Image Editing | Yes (primary use case for /images/edits)
Multi-image Generation | Yes (up to N reference images on /images/edits via fal)

2. Complete Input Schema
The /v1/images/generations endpoint accepts the following parameters. Defaults and enums below are reproduced from the OpenAI API reference.
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of the desired image(s). Max length documented as 32000 characters. | | 32000 chars
model | string | No | gpt-image-1 | gpt-image-2, gpt-image-1, dall-e-3 | Model ID to use for generation. | |
n | integer | No | 1 | 1-10 | Number of images to generate. | | 10
quality | string | No | auto | auto, low, medium, high | Quality of the generated image. | |
size | string | No | auto | auto, 1024x1024, 1024x1536, 1536x1024, 1920x1080, 1080x1920 | Output image dimensions. | |
background | string | No | auto | auto, transparent, opaque | Background type (transparent = PNG with alpha). | |
moderation | string | No | auto | auto, 'low' | Content moderation level. | |
output_format | string | No | png | png, jpeg, webp | Returned image format. | |
output_compression | integer | No | | 0-100 | Compression level for webp/jpeg. | 0 | 100
stream | boolean | No | false | true, false | Stream partial deltas as the image generates. | |
user | string | No | | | End-user identifier for abuse monitoring. | |

The /v1/images/edits endpoint shares most parameters above and additionally requires image and optional mask files (multipart/form-data).

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. No special syntax required.
Prompt syntax | Free-form natural language. No tags or markup required.
Maximum prompt length | 32,000 characters (documented).
Prompt token limit | Not officially documented (treated as opaque text by the model).
Negative prompt support | No (use natural-language negation like "without X").
System prompt support | Yes via the Responses API image_generation tool.
JSON prompt support | No (prompt is plain text).
Natural language prompt support | Yes (primary input modality).
Structured prompt support | Partial (the Responses API accepts a structured tool-call schema with image_generation).
Markdown support | No (prompt is plain text).

4. Image Limits
Limit | Value
Maximum input images | Up to 10 reference images on /images/edits (fal endpoint).
Minimum input images | 0 for text-to-image; 1 for /images/edits.
Maximum generated images | 10 per request (n parameter).
Maximum resolution | 3840x2160 (4K, with quality=high).
Minimum resolution | 512x512 (smallest documented size).
Supported aspect ratios | 1:1, 2:3, 3:2, 16:9, 9:16 (derived from size enum).
Supported image formats | Input: png, webp, jpg. Output: png, jpeg, webp.
Maximum upload size | Not officially documented (typical OpenAI limit: 25 MB per file).
Maximum output size | ~24 MB per generated image (4K high quality).

5. API Examples
The following examples are reproduced from OpenAI's official API reference at developers.openai.com and from fal.ai's official model documentation.

cURL - Text-to-Image
# Official OpenAI example: generate an image
curl https://api.openai.com/v1/images/generations   -H "Authorization: Bearer $OPENAI_API_KEY"   -H "Content-Type: application/json"   -d '{
    "model": "gpt-image-2",
    "prompt": "A portrait of a red panda wearing a tiny top hat",
    "size": "1536x1024",
    "quality": "high"
  }'

cURL - Image Edit (multipart)
# Official OpenAI example: edit an image with a mask
curl https://api.openai.com/v1/images/edits   -H "Authorization: Bearer $OPENAI_API_KEY"   -F model="gpt-image-2"   -F image="@photo.png"   -F mask="@mask.png"   -F prompt="Replace the sky with a starry galaxy"   -F size="1536x1024"

JavaScript fal.ai client (image edit)
// From fal.ai docs: openai/gpt-image-2/edit
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("openai/gpt-image-2/edit", {
  input: {
    prompt: "Change the background to a rainy Tokyo street at night",
    image_urls: ["https://your-image-url.com/photo.png"],
  },
  logs: true,
  onQueueUpdate: (update) => {
    if (update.status === "IN_PROGRESS") {
      update.logs.map((log) => log.message).forEach(console.log);
    }
  },
});
console.log(result.data.images[0].url);

Python - OpenAI SDK (text-to-image)
# From OpenAI official Python SDK docs
from openai import OpenAI
client = OpenAI()
result = client.images.generate(
  model="gpt-image-2",
  prompt="A portrait of a red panda wearing a tiny top hat",
  size="1536x1024"
)
image_b64 = result.data[0].b64_json

JSON Request (Responses API image_generation tool)
{
  "model": "gpt-5",
  "tools": [{"type": "image_generation"}],
  "input": "Generate a poster for a jazz festival in New Orleans, vintage 1960s style"
}

JSON Response (images.generate)
{
  "created": 1736000000,
  "data": [
    {
      "b64_json": "<base64-encoded image data>",
      "usage": {
        "input_tokens": 120,
        "output_tokens": 14800,
        "total_tokens": 14920
      }
    }
  ]
}

TypeScript/REST HTTP
> No separate TypeScript or REST HTTP example published beyond the SDK examples above. The OpenAI SDK is the canonical TypeScript interface.

6. SDK Information
Field | Value
Official SDK Name | openai-python and openai-node (officially maintained by OpenAI)
Installation Command (Python) | pip install openai
Installation Command (JS) | npm install openai
SDK Version | Python ≥1.50 (2024+); Node ≥4.70 required for gpt-image-2
JavaScript SDK | Yes (openai npm package)
Python SDK | Yes (openai PyPI package)
REST Support | Yes (HTTPS POST to /v1/images/generations and /v1/images/edits)
Async Support | Yes (queue-based via fal.ai; native OpenAI Responses API supports async tool calls)
Streaming Support | Yes (stream=true parameter returns partial image deltas)

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg, image/webp
Returned fields | b64_json (default), url (when requested via Responses API), revised_prompt (not returned for gpt-image-2)
URLs | Returned only when using the Responses API image_generation tool; otherwise base64-encoded payload.
Base64 support | Yes (default output format).
Metadata | created (Unix timestamp), model, usage (input/output/total tokens).
Seeds | Not officially documented (model is not seed-deterministic).
Safety scores | Not exposed. Content is filtered before return; filtered prompts return an error.
NSFW flags | Filtered server-side; rejected requests return content_policy_violation error.

8. Pricing
GPT Image 2 uses a token-based pricing model. Text tokens are billed separately from image tokens, and image token cost depends on the quality tier selected. The following table reproduces the fal.ai-documented pricing (which mirrors OpenAI's published rates) for one input image at canonical sizes.
Size | Low | Medium | High
1024x768 | $0.011 | $0.043 | $0.151
1024x1024 | $0.015 | $0.061 | $0.219
1024x1536 | $0.018 | $0.054 | $0.178
1920x1080 | $0.017 | $0.053 | $0.158
2560x1440 | $0.019 | $0.068 | $0.234
3840x2160 | $0.024 | $0.113 | $0.413

Token rates (per 1M tokens): text input $5.00, cached text input $1.25, text output $10.00. Image input $8.00/MP, cached image input $2.00/MP, image output $30.00/MP. Rate limits follow the standard OpenAI tier system (Tier 1-5); the highest documented image-output rate is at Tier 5.

9. Changelog
Category | Detail
Latest features | gpt-image-2 introduced: native 4K output, transparent backgrounds, streaming partial images, multi-image reference editing, Responses API integration.
Breaking changes | gpt-image-2 returns b64_json by default (no url field on /images/generations); dall-e-3 returned url by default.
Deprecated parameters | response_format removed (always b64_json for gpt-image-2).
New parameters | background (transparent/opaque), output_format (png/jpeg/webp), output_compression, moderation (auto/low), stream.

10. Official Documentation
Resource | URL
API Reference (images.generate) | https://developers.openai.com/api/reference/python/resources/images/methods/create
API Reference (images.edit) | https://developers.openai.com/api/reference/python/resources/images/methods/edit
Model documentation | https://developers.openai.com/api/docs/models/gpt-image-2
Image generation guide | https://developers.openai.com/api/docs/guides/image-generation
Images and vision guide | https://developers.openai.com/api/docs/guides/images-vision
OpenAI Python SDK | https://github.com/openai/openai-python
OpenAI Node SDK | https://github.com/openai/openai-node
fal.ai endpoint (text-to-image) | https://fal.ai/models/openai/gpt-image-2
fal.ai endpoint (image edit) | https://fal.ai/models/openai/gpt-image-2/edit
OpenAPI Specification | https://github.com/openai/openai-openapi

Best Used For
GPT Image 2 is the strongest documented choice for prompt-following image generation that requires rendering legible text in the image (posters, UI mockups, branded assets), for multi-image editing workflows where natural language describes the desired change, and for applications that benefit from streaming partial results to the user.

Known Limitations
• No seed support: the model is not deterministic across calls with identical inputs.
• No native negative-prompt parameter; negation must be expressed in natural language.
• Maximum 10 input reference images per /images/edits call on fal.ai hosted endpoint.
• Streaming produces partial image deltas, not progressive scan lines; UIs must mosaic the deltas.
• Transparent-background output is PNG-only; JPEG/WebP outputs are opaque.

Quality Samples
OpenAI publishes sample images in the official image generation guide at developers.openai.com/api/docs/guides/image-generation. fal.ai hosts a live playground at fal.ai/models/openai/gpt-image-2 where the schema and example prompts can be exercised directly.

Google
Gemini Image, Imagen 4, Nano Banana 2, Nano Banana Pro
Google currently exposes four documented image-generation surfaces: Imagen 4 (via Gemini API and Vertex AI), Gemini Image (the Responses-style image output via the Gemini multimodal API), Nano Banana 2 (codename for Gemini 2.5 Flash Image, optimized for speed), and Nano Banana Pro (codename for Gemini 2.5 Pro Image, optimized for quality). All four are documented at ai.google.dev/gemini-api/docs.

Gemini Image
1. Basic Information
Field | Value
Company | Google
Model Name | Gemini Image (gemini-2.5-flash-image / nano-banana)
Latest Version | gemini-2.5-flash-image-preview (a.k.a. Nano Banana)
Release Date | August 2025 (LTS release announced alongside Gemini 2.5)
Official Docs URL | https://ai.google.dev/gemini-api/docs/image-generation
fal.ai Endpoint | Not officially documented for the native Gemini Image endpoint.
Official API Endpoint | POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes
Inpainting | Yes (via inline image part + prompt)
Outpainting | Not officially documented
Style Transfer | Yes (via reference image in prompt)
Image Editing | Yes (primary use case)
Multi-image Generation | Yes (multi-image input supported)

2. Input Schema (generateContent)
Parameter | Type | Required | Default | Enum | Description | Min | Max
contents | array | Yes | | | Array of Content objects (text + optional inline_data image parts). | |
generationConfig | object | No | | | Generation config including responseModalities. | |
generationConfig.responseModalities | array | No | | ['TEXT', 'IMAGE'] | Modalities to return. Must include IMAGE for image output. | |
generationConfig.temperature | number | No | 1.0 | 0-2 | Sampling temperature. | 0 | 2
safetySettings | array | No | | | Per-category safety settings. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text in the text part of contents.
Prompt syntax | Free-form; no special syntax.
Maximum prompt length | Not officially documented (typical Gemini limit: 2M tokens context).
Prompt token limit | Subject to overall context window.
Negative prompt support | No (use natural language).
System prompt support | Yes (systemInstruction field).
JSON prompt support | No (prompt is plain text).
Natural language prompt support | Yes.
Structured prompt support | Partial (via structured output config on text part).
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | Up to 10 images per request (Gemini multimodal limit).
Minimum input images | 0 for text-only generation.
Maximum generated images | 1 image per response (typical); multiple via multiple responses.
Maximum resolution | Not officially documented (output typically 1024x1024 base).
Minimum resolution | Not officially documented.
Supported aspect ratios | 1:1, 3:4, 4:3, 9:16, 16:9 (configurable via prompt or generationConfig).
Supported image formats | Input: PNG, JPEG, WebP, HEIC. Output: PNG (default), JPEG.
Maximum upload size | Not officially documented (typical Gemini limit: 20 MB per file).
Maximum output size | Not officially documented.

5. API Examples
cURL
# Official Gemini API example: image generation
curl -X POST   "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GEMINI_API_KEY"   -H 'Content-Type: application/json'   -d '{
    "contents": [{
      "parts": [
        {"text": "Generate an image of a baby sea otter wearing a tiny raincoat"}
      ]
    }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"]
    }
  }'

Python
# Official Google Gen AI Python SDK example
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents="Generate an image of a baby sea otter wearing a tiny raincoat",
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"]
    ),
)
# Access the image part
for part in response.candidates[0].content.parts:
    if part.inline_data is not None:
        image_bytes = part.inline_data.data

JavaScript
// Official Google Gen AI JS SDK example
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const response = await ai.models.generateContent({
  model: "gemini-2.5-flash-image",
  contents: "Generate an image of a baby sea otter wearing a tiny raincoat",
  config: { responseModalities: ["TEXT", "IMAGE"] },
});
const imagePart = response.candidates[0].content.parts.find(p => p.inlineData);
if (imagePart) {
  const base64 = imagePart.inlineData.data;
}

TypeScript/REST HTTP/JSON Request+Response
> The REST request is the JSON object shown in the cURL example above. The JSON response is the standard GenerateContentResponse with parts containing inline_data.image bytes. No separate TypeScript-specific example is published beyond the JS SDK example.

6. SDK Information
Field | Value
Official SDK Name | @google/genai (JavaScript) and google-genai (Python)
Installation Command (Python) | pip install google-genai
Installation Command (JS) | npm install @google/genai
SDK Version | Python ≥1.0 (2025); JS ≥1.0 (2025).
JavaScript SDK | Yes.
Python SDK | Yes.
REST Support | Yes (HTTPS POST to /v1beta/models/...:generateContent).
Async Support | Yes (queue-based via Vertex AI Batch).
Streaming Support | Yes (streamGenerateContent for text streaming; image output is non-streaming).

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | inline_data.data (base64-encoded image bytes), inline_data.mime_type, text (any text parts).
URLs | Not returned (image is inline base64). Use the Files API to upload and obtain a URI if needed.
Base64 support | Yes (primary output format).
Metadata | usageMetadata (promptTokenCount, candidatesTokenCount, totalTokenCount), modelVersion.
Seeds | Not officially documented for image generation.
Safety scores | safetyRatings array per candidate (categories: HARASSMENT, HATE_SPEECH, SEXUALLY_EXPLICIT, DANGEROUS_CONTENT).
NSFW flags | Filtered via safetySettings; blocked candidates return finishReason=SAFETY.

8. Pricing
Gemini Image is billed as part of the Gemini API. As of the latest published rates, gemini-2.5-flash-image-preview is priced per image based on input+output token equivalents; consult ai.google.dev/pricing for current rates. Vertex AI pricing is documented at cloud.google.com/vertex-ai/generative-ai/pricing.

9. Changelog
Category | Detail
Latest features | Native image output via responseModalities; multi-image input; inline base64 image return.
Breaking changes | Gemini 2.5 Flash Image replaces the separate Imagen-only endpoint for the Gemini API surface.
Deprecated parameters | The older imageGeneration model alias is deprecated in favor of gemini-2.5-flash-image.
New parameters | responseModalities=["IMAGE"] (the trigger for image output).

10. Official Documentation
Resource | URL
Gemini API image generation | https://ai.google.dev/gemini-api/docs/image-generation
Gemini API models list | https://ai.google.dev/gemini-api/docs/models
Imagen documentation | https://ai.google.dev/gemini-api/docs/imagen
Python SDK | https://github.com/googleapis/python-genai
JavaScript SDK | https://github.com/googleapis/js-genai
OpenAPI Specification | Not officially published (REST reference is HTML-only).

Best Used For
Gemini Image is the strongest choice when the same workflow needs multimodal reasoning (text + image understanding) and image generation in one model call, and when image editing driven by a natural-language turn is preferable to a dedicated edits endpoint.

Known Limitations
• Output is inline base64 only; no direct URL field, which complicates large-image streaming.
• Resolution and aspect-ratio controls are prompt-driven, not parameter-driven, which reduces programmatic reproducibility.
• No seed support documented; outputs are non-deterministic.
• Image streaming is not supported; image parts arrive only when generation completes.

Quality Samples
Sample images and interactive prompts are published at ai.google.dev/gemini-api/docs/image-generation. The fal.ai endpoint at fal.ai/models/fal-ai/imagen4/preview (Imagen 4 variant) is marked deprecated on fal and should not be used for new integrations.

Imagen 4
1. Basic Information
Field | Value
Company | Google (DeepMind)
Model Name | Imagen 4 (imagen-4, imagen-4-fast, imagen-4-ultra)
Latest Version | imagen4.0-generate-001 (preview); imagen-4-fast for lower-latency.
Release Date | May 2024 (Imagen 3) → August 2024 (Imagen 4 announcement) → GA late 2024.
Official Docs URL | https://ai.google.dev/gemini-api/docs/imagen
fal.ai Endpoint | fal-ai/imagen4/preview (DEPRECATED; marked as no longer supported on fal).
Official API Endpoint | POST https://generativelanguage.googleapis.com/v1beta/models/imagen-4:predict

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | No (text-to-image only on Imagen 4; use Gemini Image for editing).
Inpainting | No.
Outpainting | No.
Style Transfer | No (use Gemini Image).
Image Editing | No.
Multi-image Generation | No (single image per request).

2. Input Schema (instances)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of the desired image. | | 480 chars
sampleCount | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
aspectRatio | string | No | 1:1 | 1:1, 9:16, 16:9, 3:4, 4:3 | Aspect ratio of generated image. | |
guidanceScale | number | No | | | Controls how much the model adheres to the prompt (lower = more creative). | 0 | 500
negativePrompt | string | No | | | Description of what to exclude from the image. | | 480 chars
seed | integer | No | random | 0-9223372036854775807 | Random seed for reproducibility. | 0 | 9223372036854775807
language | string | No | en | en, hi, ja, ko, auto | Language of the prompt text. | |
storageOption | object | No | | | Cloud Storage destination (Vertex AI only). | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text.
Prompt syntax | Free-form; supports up to 480 characters.
Maximum prompt length | 480 characters.
Prompt token limit | Not separately documented (capped at character level).
Negative prompt support | Yes (negativePrompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 0 (text-to-image only).
Minimum input images | 0.
Maximum generated images | 4 per request (sampleCount).
Maximum resolution | Not officially documented (typical: 1024x1024 base; up to 2048x2048 on Ultra variant).
Minimum resolution | Not officially documented.
Supported aspect ratios | 1:1, 9:16, 16:9, 3:4, 4:3.
Supported image formats | Output: PNG (default), JPEG.
Maximum upload size | N/A (no input images).
Maximum output size | Not officially documented.

5. API Examples
cURL
# Official Gemini API example: Imagen 4 predict
curl -X POST   "https://generativelanguage.googleapis.com/v1beta/models/imagen-4:predict?key=$GEMINI_API_KEY"   -H 'Content-Type: application/json'   -d '{
    "instances": [{"prompt": "A photorealistic hummingbird feeding from a glowing flower"}],
    "parameters": {"sampleCount": 4, "aspectRatio": "16:9"}
  }'

Python
# Official Google Gen AI SDK example
from google import genai
client = genai.Client()
response = client.models.generate_images(
    model="imagen-4",
    prompt="A photorealistic hummingbird feeding from a glowing flower",
    config={"number_of_images": 4, "aspect_ratio": "16:9"},
)
for image in response.generated_images:
    image_bytes = image.image.image_bytes

JavaScript
// Official Google Gen AI JS SDK example
import { GoogleGenAI } from "@google/genai";
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });
const response = await ai.models.generateImages({
  model: "imagen-4",
  prompt: "A photorealistic hummingbird feeding from a glowing flower",
  config: { numberOfImages: 4, aspectRatio: "16:9" },
});
for (const image of response.generatedImages) {
  const base64 = image.image.imageBytes;
}

TypeScript/REST HTTP/JSON
> The REST request body is the JSON object shown in the cURL example. The JSON response is the standard PredictResponse with predictions[].bytesBase64Encoded. No separate TypeScript-specific example is published.

JSON Response
{
  "predictions": [
    { "bytesBase64Encoded": "<base64-encoded PNG bytes>", "mimeType": "image/png" }
  ]
}

6. SDK Information
Field | Value
Official SDK Name | @google/genai (JS) and google-genai (Python) | same SDK as Gemini.
Installation Command (Python) | pip install google-genai
Installation Command (JS) | npm install @google/genai
SDK Version | Python ≥1.0; JS ≥1.0
JavaScript SDK | Yes.
Python SDK | Yes.
REST Support | Yes (HTTPS POST to /v1beta/models/imagen-4:predict).
Async Support | Yes (Vertex AI Batch predictions).
Streaming Support | No (image generation is non-streaming).

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | bytesBase64Encoded, mimeType.
URLs | Not returned (base64 only); Vertex AI storageOption can write to GCS and return a URI.
Base64 support | Yes.
Metadata | predictions[] array. No usage metadata on Gemini API surface.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned per image; content is filtered before return.
NSFW flags | Filtered via Imagen safety classifiers; blocked prompts return an error.

8. Pricing
Imagen 4 pricing on Vertex AI is per-image and varies by variant: Imagen 4 Fast is the cheapest, Imagen 4 standard is mid-tier, and Imagen 4 Ultra is the premium tier. As of the latest published pricing on cloud.google.com/vertex-ai/generative-ai/pricing, expect roughly $0.039/image for Fast and $0.069/image for Ultra at 1024x1024. Volume discounts apply beyond 100K images/month.

9. Changelog
Category | Detail
Latest features | Imagen 4 Ultra variant introduced (highest quality); improved text rendering in generated images.
Breaking changes | imagen-3.0-generate is deprecated; migrate to imagen-4.
Deprecated parameters | sampleImageSize (removed in favor of aspectRatio).
New parameters | aspectRatio, negativePrompt, language=auto.

10. Official Documentation
Resource | URL
Imagen docs | https://ai.google.dev/gemini-api/docs/imagen
Imagen models list | https://ai.google.dev/gemini-api/docs/models/imagen
Vertex AI Imagen docs | https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview
Pricing | https://cloud.google.com/vertex-ai/generative-ai/pricing
Python SDK | https://github.com/googleapis/python-genai
JavaScript SDK | https://github.com/googleapis/js-genai

Best Used For
Imagen 4 is the strongest Google choice for pure text-to-image generation when seed reproducibility, native negative prompts, and explicit aspect-ratio control matter more than multimodal editing (which belongs to Gemini Image).

Known Limitations
• No image-to-image, inpainting, or editing; text-to-image only.
• Maximum 4 images per request (sampleCount).
• Maximum prompt length is 480 characters (much shorter than GPT Image 2's 32K).
• Output resolution is not user-configurable beyond the 5 documented aspect ratios.

Quality Samples
Sample images are published at ai.google.dev/gemini-api/docs/imagen. The fal.ai hosted endpoint (fal-ai/imagen4/preview) is marked deprecated and no longer supported.

Nano Banana 2
Nano Banana 2 is Google's internal codename for the Gemini 2.5 Flash Image model—the speed-optimized variant of Gemini Image. The official model id is gemini-2.5-flash-image. Its schema, prompt rules, and limits are identical to the Gemini Image section above; the differences are pricing (Flash is cheaper than Pro) and latency (Flash is optimized for sub-3-second generation).

Differences from Gemini Image (Pro)
• Model id: gemini-2.5-flash-image (vs. gemini-2.5-pro-image for Nano Banana Pro).
• Throughput: Flash variant has higher documented QPS limits on the Gemini API free tier.
• Quality: Pro is preferred for high-detail prompts; Flash for interactive workflows.

Pricing
See ai.google.dev/pricing for current Flash vs. Pro rates. As of the latest published pricing, Flash is roughly 4x cheaper per image than Pro at the same input/output token count.

Nano Banana Pro
Nano Banana Pro is Google's internal codename for Gemini 2.5 Pro Image—the quality-optimized variant of Gemini Image. The official model id is gemini-2.5-pro-image. Its schema is identical to Gemini Image above; differences are pricing (Pro is more expensive than Flash) and quality (Pro is the recommended choice for high-detail prompts and complex editing tasks).

Differences from Nano Banana 2 (Flash)
• Model id: gemini-2.5-pro-image.
• Quality: Pro is recommended for complex multi-image editing, fine detail, and high-fidelity text rendering.
• Latency: Pro is slower than Flash (typical 5-10s vs. 2-4s).

Pricing
See ai.google.dev/pricing for current Pro rates. Pro is roughly 4x the per-image cost of Flash at the same token count.

Black Forest Labs
FLUX Family
Black Forest Labs (BFL) publishes the FLUX family of image models. The current generation is FLUX.2 (recommended for new projects); the legacy generation is FLUX.1 (Schnell, Dev, Pro, Pro Ultra, Kontext). All FLUX models are documented at docs.bfl.ai and most are also hosted on fal.ai under the fal-ai/flux* endpoint prefix.

FLUX.1 Schnell
1. Basic Information
Field | Value
Company | Black Forest Labs
Model Name | FLUX.1 [schnell] (12B parameter flow transformer)
Latest Version | flux-1-schnell (Apache 2.0 licensed, distill of FLUX.1 Pro)
Release Date | August 2024 (initial FLUX.1 release).
Official Docs URL | https://docs.bfl.ai/
fal.ai Endpoint | fal-ai/flux/schnell
Official API Endpoint | POST https://api.bfl.ai/v1/flux-1-schnell (BFL native); POST https://fal.run/fal-ai/flux/schnell (fal.ai).

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image input on fal.ai endpoint).
Inpainting | No (use FLUX.1 Pro or Kontext).
Outpainting | No (use FLUX Tools).
Style Transfer | No (use LORA or Kontext).
Image Editing | Limited (via image-to-image).
Multi-image Generation | No.

2. Input Schema (fal.ai)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | |
image_size | object/string | No | "landscape_4_3" | square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, or {width,height} | Output image dimensions. | |
num_inference_steps | integer | No | 4 | 1-4 | Number of denoising steps. Schnell is distilled to 1-4 steps. | | 4
num_images | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
seed | integer | No | random | | Random seed for reproducibility. | |
enable_safety_checker | boolean | No | true | true, false | Enable NSFW safety checker. | |
output_format | string | No | png | png, jpeg | Output image format. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text.
Prompt syntax | Free-form; FLUX models respond well to detailed descriptive prompts.
Maximum prompt length | Not officially documented (typical: ~512 tokens).
Prompt token limit | T5-XXL tokenizer, 256-512 tokens effective context.
Negative prompt support | No (schnell variant does not accept negative_prompt).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (for image-to-image via fal endpoint).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request (num_images).
Maximum resolution | Up to 2048x2048 (via custom image_size); 1536x1024 for presets.
Minimum resolution | 256x256 (typical; not officially documented).
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16.
Supported image formats | Output: PNG (default), JPEG.
Maximum upload size | Not officially documented.
Maximum output size | ~10 MB per image (1024x1024 PNG).

5. API Examples
JavaScript (fal.ai)
// Official fal.ai example: FLUX.1 [schnell]
import { fal } from '@fal-ai/client'
fal.config({ credentials: 'YOUR_FAL_KEY' })
const result = await fal.subscribe('fal-ai/flux/schnell', {
  input: {
    prompt: "A serene mountain landscape at sunset, hyperrealistic style",
    num_inference_steps: 4
  }
})
console.log(result.data.images[0].url)

Python (fal-client)
# Official fal.ai Python client example
import fal_client
result = fal_client.subscribe(
    "fal-ai/flux/schnell",
    arguments={
        "prompt": "A serene mountain landscape at sunset",
        "num_inference_steps": 4,
    },
)
print(result["images"][0]["url"])

cURL (fal.ai REST)
curl -X POST "https://fal.run/fal-ai/flux/schnell"   -H "Authorization: Key $FAL_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A serene mountain landscape at sunset",
    "num_inference_steps": 4,
    "image_size": "landscape_4_3"
  }'

JSON Response
{
  "images": [
    {
      "url": "https://fal.media/files/abc123.jpg",
      "width": 1024,
      "height": 768,
      "content_type": "image/jpeg"
    }
  ],
  "timings": { "inference": 0.75 },
  "seed": 976168300,
  "has_nsfw_concepts": [false],
  "prompt": "A serene mountain landscape at sunset"
}

TypeScript/REST HTTP (BFL native)
> BFL native API examples are published at docs.bfl.ai. The fal.ai examples above are reproduced from the fal.ai model page. No separate TypeScript-specific example is published beyond the JS SDK example.

6. SDK Information
Field | Value
Official SDK Name | @fal-ai/client (JS) and fal-client (Python)
Installation Command (Python) | pip install fal-client
Installation Command (JS) | npm install --save @fal-ai/client
SDK Version | JS ≥1.0, Python ≥0.5.
JavaScript SDK | Yes.
Python SDK | Yes.
REST Support | Yes (HTTPS POST to fal.run endpoints).
Async Support | Yes (queue-based via fal.subscribe; native BFL API also supports async).
Streaming Support | No for schnell (sub-second generation makes streaming unnecessary).

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | images[].url, images[].width, images[].height, images[].content_type, timings, inference, seed, has_nsfw_concepts[], prompt.
URLs | Yes (fal.ai returns a CDN URL valid for ~24 hours).
Base64 support | Yes (via output_format=base64 on fal.ai; not default).
Metadata | timings (inference seconds), seed, has_nsfw_concepts (boolean array).
Seeds | Yes (seed field, integer).
Safety scores | has_nsfw_concepts boolean array (per generated image).
NSFW flags | Yes if has_nsfw_concepts[i]=true, the i-th image is flagged.

8. Pricing
FLUX.1 Schnell is the cheapest FLUX variant. On fal.ai, pricing is $0.003 per megapixel (billed by rounding up to the nearest megapixel). A 1024x1024 image (1 MP) costs $0.003; a 1536x1024 image (1.5 MP) costs $0.0045. BFL native pricing is published at docs.bfl.ai in Credits & Billing.

9. Changelog
Category | Detail
Latest features | Sub-second generation via 1-4 step distillation.
Breaking changes | None since launch (schnell schema has been stable).
Deprecated parameters | None.
New parameters | enable_safety_checker added as configurable parameter.

10. Official Documentation
Resource | URL
BFL documentation home | https://docs.bfl.ai/
BFL API reference | https://docs.bfl.ai/api-reference
BFL pricing | https://docs.bfl.ai/credits-and-billing
fal.ai model page | https://fal.ai/models/fal-ai/flux/schnell
fal.ai JS SDK | https://github.com/fal-ai/fal-js
fal.ai Python SDK | https://github.com/fal-ai/fal-python
OpenAPI Specification | https://docs.bfl.ai/openapi.json

Best Used For
FLUX.1 Schnell is the recommended choice when latency is the dominant constraint: real-time UI previews, batch thumbnail generation, and rapid prototyping where the cost of slower models cannot be justified.

Known Limitations
• Quality is lower than FLUX.1 Pro at the same prompt (schnell is a distilled model).
• No native negative-prompt parameter.
• Maximum 4 inference steps (the distillation does not benefit from more steps).
• No multi-image reference support.

Quality Samples
BFL hosts a public playground at playground.bfl.ai. fal.ai hosts a live sandbox at fal.ai/models/fal-ai/flux/schnell.

FLUX.1 Dev
FLUX.1 [dev] is the open-weights research variant of the FLUX.1 family. It is licensed for non-commercial use and is the model distributed for self-hosting (12B parameter flow transformer). The hosted API schema is identical to FLUX.1 Schnell above, with the following differences:

Differences from FLUX.1 Schnell
• Model id: flux-1-dev (BFL) / fal-ai/flux/dev (fal.ai).
• Inference steps: 1-4 (schnell) vs. 28 (dev)—dev is NOT distilled and benefits from more steps.
• License: Non-commercial (dev) vs. Apache 2.0 (schnell).
• Quality: Dev is higher quality than Schnell at the cost of ~7x longer generation time.
• Pricing on fal.ai: $0.003/MP (same as schnell).

See the FLUX.1 Schnell entry above for the full schema, prompt rules, image limits, API examples, SDK, output format, and docs links; they apply unchanged to FLUX.1 Dev.

FLUX.1 Pro
1. Basic Information
Field | Value
Company | Black Forest Labs
Model Name | FLUX.1 [pro] (12B parameter flow transformer, commercial)
Latest Version | flux-1-pro / flux-1.1-pro / flux-1.1-pro-ultra
Release Date | August 2024 (1.0) → October 2024 (1.1) → November 2024 (1.1 Ultra).
Official Docs URL | https://docs.bfl.ai/
fal.ai Endpoint | fal-ai/flux-pro (and flux-1.1-pro, flux-1.1-pro-ultra)
Official API Endpoint | POST https://api.bfl.ai/v1/flux-1.1-pro and /v1/flux-1.1-pro-ultra

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via prompt_strength parameter).
Inpainting | Yes (with mask parameter on BFL native API).
Outpainting | No (use FLUX Outpainting tool).
Style Transfer | Yes (via image-to-image).
Image Editing | Limited (use FLUX.1 Kontext for serious editing).
Multi-image Generation | No (single image).

2. Input Schema (fal.ai)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | |
image_size | object/string | No | "landscape_4_3" | square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9, or {width,height} | Output dimensions. | |
num_inference_steps | integer | No | 28 | 1-50 | Number of denoising steps. | 1 | 50
guidance_scale | number | No | 3.5 | 0-20 | CFG scale (how closely to follow prompt). | 0 | 20
prompt_strength | number | No | | 0-1 | For image-to-image: 0=ignore input image, 1=keep input image. Only used when image_url is provided. | 0 | 1
image_url | string | No | | | Input image for image-to-image. | |
mask_url | string | No | | | Mask for inpainting (white=edit, black=keep). | |
num_images | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
seed | integer | No | random | | Random seed. | |
enable_safety_checker | boolean | No | true | | NSFW safety checker. | |
output_format | string | No | png | png, jpeg | Output format. | |
raw | boolean | No | false | | Ultra variant only: enables Raw mode for authentic photography aesthetics. | |

3. Prompt Rules
Same as FLUX.1 Schnell above. FLUX Pro responds well to detailed prompts but does not support negative prompts natively.

4. Image Limits
Limit | Value
Maximum input images | 1 (image_url + optional mask_url).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request.
Maximum resolution | Up to 4 MP (e.g. 2048x2048) on Ultra variant; 2 MP on standard Pro.
Minimum resolution | 256x256 (typical).
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16 (plus custom dimensions).
Supported image formats | Output: PNG, JPEG.
Maximum upload size | Not officially documented.
Maximum output size | ~24 MB per image at 4K.

5. API Examples
cURL (fal.ai REST)
curl -X POST "https://fal.run/fal-ai/flux-pro"   -H "Authorization: Key $FAL_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A majestic eagle soaring over a misty mountain range, photorealistic, golden hour",
    "image_size": "landscape_16_9",
    "num_inference_steps": 28,
    "guidance_scale": 3.5
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/flux-pro", {
  input: {
    prompt: "A majestic eagle soaring over a misty mountain range",
    image_size: "landscape_16_9",
    num_inference_steps: 28,
    guidance_scale: 3.5
  }
});
console.log(result.data.images[0].url);

Python (fal-client)
import fal_client
result = fal_client.subscribe(
    "fal-ai/flux-pro",
    arguments={
        "prompt": "A majestic eagle soaring over a misty mountain range",
        "image_size": "landscape_16_9",
        "num_inference_steps": 28,
    },
)
print(result["images"][0]["url"])

JSON Response
{
  "images": [
    {
      "url": "https://fal.media/files/flux-pro-xyz.jpg",
      "width": 1536,
      "height": 864,
      "content_type": "image/jpeg"
    }
  ],
  "timings": { "inference": 2.4 },
  "seed": 1234567890,
  "has_nsfw_concepts": [false]
}

TypeScript/REST HTTP (BFL native)
> BFL publishes REST HTTP examples at docs.bfl.ai. No TypeScript-specific example beyond the fal.ai JS SDK above.

6. SDK Information
Same as FLUX.1 Schnell above (@fal-ai/client and fal-client). BFL also publishes a native Python SDK (bfl-client) documented at docs.bfl.ai.

7. Output Format
Same as FLUX.1 Schnell above (URL, base64 optional, timings, seed, has_nsfw_concepts).

8. Pricing
FLUX.1 Pro on fal.ai: $0.005 per megapixel (round up to nearest MP). FLUX.1.1 Pro Ultra: $0.01 per megapixel. A 1024x1024 Pro image costs $0.005; a 2048x2048 Ultra image (4 MP) costs $0.04.

9. Changelog
Category | Detail
Latest features | FLUX.1.1 Pro Ultra introduces Raw mode and 4MP output; FLUX.1.1 Pro improved prompt adherence over 1.0.
Breaking changes | None; schema has been backward-compatible across 1.0→1.1→1.1 Ultra.
Deprecated parameters | None.
New parameters | raw (Ultra only).

10. Official Documentation
Resource | URL
BFL documentation | https://docs.bfl.ai/
FLUX 1.1 [pro] models (BFL) | https://docs.bfl.ai/flux-1-1-pro-models
fal.ai model page (flux-pro) | https://fal.ai/models/fal-ai/flux-pro
BFL API reference | https://docs.bfl.ai/api-reference
BFL pricing | https://docs.bfl.ai/credits-and-billing

Best Used For
FLUX.1 Pro is the recommended default for production-grade text-to-image where commercial licensing is required, prompt adherence matters more than latency, and the budget supports ~$0.005/MP. FLUX.1.1 Pro Ultra is the choice for high-resolution (4MP+) creative work with Raw-mode photographic aesthetics.

Known Limitations
• No multi-image reference (use FLUX.2 Pro or FLUX Kontext for that).
• No native negative prompt.
• Inpainting requires a separate mask_url parameter, not a true inpainting endpoint.
• Ultra variant is ~2x the cost of standard Pro at the same resolution.

FLUX.2 Pro
1. Basic Information
Field | Value
Company | Black Forest Labs
Model Name | FLUX.2 [pro]
Latest Version | flux-2-pro (recommended for all new projects per BFL docs)
Release Date | 2025 (announced; documented at docs.bfl.ai)
Official Docs URL | https://docs.bfl.ai/
fal.ai Endpoint | fal-ai/flux-2-pro
Official API Endpoint | POST https://api.bfl.ai/v1/flux-2-pro (and /v1/flux-2-pro-text-to-image, /v1/flux-2-image-edit)

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes
Inpainting | Yes (via FLUX.2 Image Editing endpoint).
Outpainting | Yes (via FLUX Outpainting tool, integrated in FLUX.2).
Style Transfer | Yes (via multi-reference images).
Image Editing | Yes (primary selling point of FLUX.2).
Multi-image Generation | Yes; up to 10 reference images simultaneously.

2. Input Schema (BFL native—FLUX.2 Text to Image)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | |
width | integer | No | 1024 | | Output width in pixels. | 256 | 4096
height | integer | No | 1024 | | Output height in pixels. | 256 | 4096
prompt_upsampling | boolean | No | false | | Apply LLM-based prompt upsampling before generation. | |
seed | integer | No | random | | Random seed. | 0 | 2^63-1
safety_tolerance | integer | No | 2 | 0-6 | Block threshold (0=strictest, 6=most permissive). | 0 | 6
output_format | string | No | png | png, jpeg | Output format. | |
webhook_url | string | No | | | Optional webhook for async completion. | |
webhook_secret | string | No | | | HMAC secret for webhook verification. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. Optional prompt_upsampling for LLM-augmented prompts.
Prompt syntax | Free-form; BFL publishes a Prompting Guide at docs.bfl.ai/prompting-guide.
Maximum prompt length | Not officially documented (typical: ~1000 chars).
Prompt token limit | T5-XXL tokenizer, ~512 tokens effective.
Negative prompt support | No (use FLUX.2 Image Editing endpoint with negation in prompt).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Partial; prompt_upsampling accepts free-form text.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 10 (multi-reference in Image Editing endpoint).
Minimum input images | 0 for text-to-image.
Maximum generated images | 1 per request (use n calls for batch).
Maximum resolution | 4096x4096 (up to 4MP per BFL docs).
Minimum resolution | 256x256.
Supported aspect ratios | Any (free widthxheight).
Supported image formats | Output: PNG, JPEG.
Maximum upload size | Not officially documented.
Maximum output size | ~24 MB per image.

5. API Examples
cURL (BFL native)
curl -X POST "https://api.bfl.ai/v1/flux-2-pro-text-to-image"   -H "Authorization: Bearer $BFL_API_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A cyberpunk street market at night, neon reflections on wet pavement",
    "width": 1920,
    "height": 1080,
    "prompt_upsampling": true,
    "seed": 42,
    "safety_tolerance": 2,
    "output_format": "png"
  }'

JSON Response (async polling)
{
  "id": "abc-123-def",
  "status": "Request submitted",
  "api_name": "flux-2-pro-text-to-image"
}
# Poll for completion:
# GET https://api.bfl.ai/v1/get_result?id=abc-123-def
{
  "id": "abc-123-def",
  "status": "Ready",
  "result": {
    "sample": "https://bfl-api-results.s3.amazonaws.com/.../image.png",
    "prompt": "A cyberpunk street market at night..."
  }
}

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/flux-2-pro", {
  input: {
    prompt: "A cyberpunk street market at night",
    image_size: { width: 1920, height: 1080 },
    prompt_upsampling: true
  }
});
console.log(result.data.images[0].url);

Python
# BFL native Python SDK (from docs.bfl.ai)
from bfl import get_api_key
from bfl.api import fluxpro_2

client = fluxpro_2(api_key=get_api_key())
response = client.generate(
    prompt="A cyberpunk street market at night",
    width=1920,
    height=1080,
    prompt_upsampling=True,
)
print(response.image_url)

TypeScript/REST HTTP
> BFL publishes REST HTTP examples in their docs. The cURL example above is the canonical REST request. No TypeScript-specific example beyond the fal.ai JS SDK above.

6. SDK Information
Field | Value
Official SDK Name | bfl (Python, native) and @fal-ai/client (JS, via fal.ai)
Installation Command (Python, BFL native) | pip install bfl
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | bfl-python ≥1.0 (2025).
JavaScript SDK | Yes (via @fal-ai/client).
Python SDK | Yes (bfl + fal-client).
REST Support | Yes (HTTPS POST to api.bfl.ai/v1/).
Async Support | Yes (default mode is async submit, poll, retrieve).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | result.sample (URL), result.prompt (echoed), id, status.
URLs | Yes (S3 URL returned by BFL native; CDN URL by fal.ai). URLs expire after 24 hours.
Base64 support | Yes via fal.ai (output_format=base64); not on BFL native.
Metadata | id, status, api_name, timing fields.
Seeds | Yes (seed parameter; echoed in response).
Safety scores | No explicit score; safety_tolerance parameter controls blocking threshold.
NSFW flags | Filtered per safety_tolerance; blocked requests return an error.

8. Pricing
FLUX.2 Pro pricing is published at docs.bfl.ai/credits-and-billing. Per the BFL docs: FLUX.2 is the recommended model family for all use cases. Pricing is in credits (1 credit = $0.01, varies by tier). A typical 1024x1024 FLUX.2 Pro image is ~7 credits. On fal.ai, FLUX.2 Pro is priced at ~$0.012/MP.

9. Changelog
Category | Detail
Latest features | FLUX.2 unifies text-to-image + multi-reference editing (up to 10 images) + outpainting + erase + deblur + virtual try-on. Up to 4MP output.
Breaking changes | New schema (no longer 1:1 compatible with FLUX.1 Pro).
Deprecated parameters | guidance_scale removed (FLUX.2 manages internally).
New parameters | prompt_upsampling, safety_tolerance, webhook_url, webhook_secret.

10. Official Documentation
Resource | URL
BFL documentation home | https://docs.bfl.ai/
FLUX.2 overview | https://docs.bfl.ai/flux-2
FLUX.2 text-to-image API | https://docs.bfl.ai/flux-2-text-to-image
FLUX.2 image editing API | https://docs.bfl.ai/flux-2-image-editing
BFL API pricing | https://docs.bfl.ai/api-pricing
Prompting guide | https://docs.bfl.ai/prompting-guide
fal.ai model page | https://fal.ai/models/fal-ai/flux-2-pro

Best Used For
FLUX.2 Pro is the recommended default for new projects per BFL documentation. Use it when the workflow needs multi-image reference, inpainting/outpainting, or text-to-image at 4MP, and where commercial licensing is required.

Known Limitations
• Generation is async-only (submit + poll); no synchronous response.
• No streaming (image generation completes atomically).
• No native negative prompt (use the editing endpoint with negation).
• Output URLs expire after 24 hours; integrations must download promptly.

FLUX.1 Kontext & Kontext Max
FLUX.1 Kontext is BFL's previous-generation editing + generation model. It supports text-to-image plus single-image editing with natural-language instructions. Kontext Max is a higher-quality variant with longer inference times.

1. Basic Information
Field | Value
Company | Black Forest Labs
Model Name | FLUX.1 [kontext] and FLUX.1 [kontext-max]
Latest Version | flux-1-kontext, flux-1-kontext-max
Release Date | October 2024 (Kontext) → 2025 (Kontext Max).
Official Docs URL | https://docs.bfl.ai/kontext
fal.ai Endpoint | fal-ai/flux-pro/kontext and fal-ai/flux-pro/kontext/max
Official API Endpoint | POST https://api.bfl.ai/v1/flux-1-kontext

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (primary use case: natural-language editing instructions).
Inpainting | Yes (via natural-language instruction, no mask required).
Outpainting | No (use FLUX Outpainting tool).
Style Transfer | Yes (via reference image + style instruction).
Image Editing | Yes (core feature).
Multi-image Generation | Limited (single reference image per call on FLUX.1 Kontext).

2. Input Schema (BFL native)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Editing instruction (e.g., "make the sky purple"). | |
input_image | string | No | | | URL of image to edit (BFL: bfl_image_url type). | |
aspect_ratio | string | No | 1:1 | 1:1, 4:3, 3:4, 16:9, 9:16 | Aspect ratio of output. | |
seed | integer | No | random | | Random seed. | 0 | 2^63-1
safety_tolerance | integer | No | 2 | 0-6 | Safety threshold. | 0 | 6
output_format | string | No | png | png, jpeg | Output format. | |
webhook_url | string | No | | | Async webhook URL. | |

3. Prompt Rules
Same as FLUX.2 Pro. Kontext accepts natural-language editing instructions as the prompt (e.g., "turn the woman's hair blue" rather than a full text-to-image prompt).

4. Image Limits
Limit | Value
Maximum input images | 1 (single reference).
Minimum input images | 0 for text-to-image.
Maximum generated images | 1 per request.
Maximum resolution | Up to 2 MP on standard Kontext; up to 4 MP on Kontext Max.
Minimum resolution | 256x256.
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16.
Supported image formats | Output: PNG, JPEG.
Maximum upload size | Not officially documented.
Maximum output size | ~24 MB per image.

5. API Examples
CURL (BFL native)
curl -X POST "https://api.bfl.ai/v1/flux-1-kontext"   -H "Authorization: Bearer $BFL_API_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "Turn the woman's hair blue and add a red scarf",
    "input_image": "https://example.com/portrait.jpg",
    "aspect_ratio": "1:1",
    "seed": 42
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/flux-pro/kontext", {
  input: {
    prompt: "Turn the woman's hair blue and add a red scarf",
    image_url: "https://example.com/portrait.jpg"
  }
});
console.log(result.data.images[0].url);

Python (fal-client)
import fal_client
result = fal_client.subscribe(
    "fal-ai/flux-pro/kontext/max",
    arguments={
        "prompt": "Turn the woman's hair blue and add a red scarf",
        "image_url": "https://example.com/portrait.jpg"
    },
)
print(result["images"][0]["url"])

JSON Response
{
  "images": [
    {
      "url": "https://fal.media/files/kontext-result.jpg",
      "width": 1024,
      "height": 1024,
      "content_type": "image/jpeg"
    }
  ],
  "timings": { "inference": 3.8 },
  "seed": 42
}

TypeScript/REST HTTP
> See BFL docs at docs.bfl.ai/kontext for the canonical REST request. No separate TypeScript example beyond the fal.ai JS SDK.

6. SDK Information
Same as FLUX.2 Pro above (bfl Python SDK + @fal-ai/client JS SDK).

7. Output Format
Same as FLUX.2 Pro (URL, base64 via fal, id, status, seed).

8. Pricing
FLUX.1 Kontext pricing is published at docs.bfl.ai/api-pricing. On fal.ai: $0.008/MP for standard Kontext, $0.016/MP for Kontext Max. A 1024x1024 Kontext image costs $0.008; the same at Max costs $0.016.

9. Changelog
Category | Detail
Latest features | Kontext Max variant introduced (higher quality, slower).
Breaking changes | None documented.
Deprecated parameters | None.
New parameters | Kontext Max supports larger output resolutions.

10. Official Documentation
Resource | URL
FLUX.1 Kontext (BFL) | https://docs.bfl.ai/kontext
fal.ai model page (Kontext) | https://fal.ai/models/fal-ai/flux-pro/kontext
fal.ai model page (Kontext Max) | https://fal.ai/models/fal-ai/flux-pro/kontext/max
BFL API pricing | https://docs.bfl.ai/api-pricing

Best Used For
FLUX.1 Kontext is the recommended FLUX model for natural-language image editing where a single reference image is sufficient. Kontext Max is preferred for high-detail edits where latency is acceptable.

Known Limitations
• Single reference image per call (FLUX.2 Pro supports 10).
• No mask parameter; editing is natural-language-driven only.
• BFL recommends FLUX.2 for new projects; Kontext is in the Legacy Models section of BFL docs.

FLUX LORA
FLUX LORA is not a standalone model but a fine-tuning mechanism applied to FLUX.1 Pro or FLUX.1 Dev. BFL publishes LORA training and inference documentation at docs.bfl.ai/lora. Custom LoRAs are loaded via the lora parameter on the standard FLUX.1 endpoints.

1. Basic Information
Field | Value
Company | Black Forest Labs
Model Name | FLUX.1 LORA (adapter for FLUX.1 Pro/Dev)
Latest Version | LORA adapters compatible with flux-1-pro and flux-1-dev
Release Date | August 2024 (with FLUX.1 launch).
Official Docs URL | https://docs.bfl.ai/lora
fal.ai Endpoint | fal-ai/flux-lora (queue endpoint for LoRA-augmented generation)
Official API Endpoint | POST https://api.bfl.ai/v1/flux-1.1-pro with lora parameter

Supported Tasks
Task | Supported
Text-to-Image | Yes (with LoRA-augmented model).
Image-to-Image | Yes (with LORA).
Inpainting | Yes (with LoRA + mask).
Outpainting | No.
Style Transfer | Yes (LORA itself is a style adapter).
Image Editing | Limited.
Multi-image Generation | No.

2. Input Schema (additional LORA parameters)
All FLUX.1 Pro parameters apply. LoRA adds:
Parameter | Type | Required | Default | Enum | Description | Min | Max
lora | string | No | | | LORA adapter identifier (BFL-hosted) or URL to safetensors file. | |
lora_strength | number | No | 1.0 | 0-2 | Strength of LORA influence on output. | 0 | 2

3-10. (Same as FLUX.1 Pro)
Prompt rules, image limits, SDK, output format, and pricing are identical to FLUX.1 Pro. API examples differ only by the addition of the lora parameter.

CURL example with LORA
curl -X POST "https://api.bfl.ai/v1/flux-1.1-pro"   -H "Authorization: Bearer $BFL_API_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A character in the style of my-custom-anime-lora",
    "lora": "https://example.com/my-anime-lora.safetensors",
    "lora_strength": 0.8,
    "width": 1024,
    "height": 1024
  }'

Best Used For
FLUX LORA is the recommended path when a custom style, character, or product needs to be consistently rendered across many generations, and a fine-tuned adapter is preferable to prompt engineering alone.

Known Limitations
• LORA file must be publicly accessible by URL or BFL-hosted.
• lora_strength > 1.5 often produces artifacts.
• LORA inference is slightly slower than base FLUX.1 Pro (additional adapter layers).

Ideogram - Ideogram 3 and Ideogram 4
Ideogram publishes two current model versions: Ideogram 3 (general availability) and Ideogram 4 (announced; documentation limited at the time of compilation). The API is documented at developer.ideogram.ai and hosted on fal.ai.

Ideogram 3
1. Basic Information
Field | Value
Company | Ideogram AI
Model Name | Ideogram 3 (ideogram-v3)
Latest Version | ideogram-v3 (and ideogram-v3-turbo for lower latency)
Release Date | 2025 (announced as Ideogram 3 with improved text rendering).
Official Docs URL | https://developer.ideogram.ai/docs
fal.ai Endpoint | fal-ai/ideogram/v3 and fal-ai/ideogram/v3/turbo
Official API Endpoint | POST https://api.ideogram.ai/v1/images/generations

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image_url parameter).
Inpainting | Yes (via mask parameter).
Outpainting | No.
Style Transfer | Yes (via style_type and image_url).
Image Editing | Limited.
Multi-image Generation | No (single image per call).

2. Input Schema (Ideogram native)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | |
aspect_ratio | string | No | | ASPECT_1_1, ASPECT_4_3, ASPECT_3_4, ASPECT_16_9, ASPECT_9_16, ASPECT_3_2, ASPECT_2_3, ASPECT_1_3, ASPECT_3_1 | Aspect ratio. | |
model | string | No | ideogram-v3 | ideogram-v3, ideogram-v3-turbo, ideogram-v2, ideogram-v2-turbo, ideogram-v1 | Model variant. | |
magic_prompt_option | string | No | AUTO | AUTO, ON, OFF | Whether to apply LLM prompt augmentation. | |
seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
style_type | string | No | AUTO | AUTO, GENERAL, REALISTIC, DESIGN, RENDER_3D, ANIME | Style preset. | |
negative_prompt | string | No | | | What to exclude from image. | |
image_url | string | No | | | Input image for image-to-image. | |
mask | string | No | | | Mask URL for inpainting (white=edit). | |
num_images | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. Ideogram is known for strong text rendering inside images.
Prompt syntax | Free-form. Quoted text in the prompt will be rendered as text in the image.
Maximum prompt length | Not officially documented (typical: ~1000 chars).
Prompt token limit | Not officially documented.
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Partial; magic_prompt_option augments the prompt with an LLM.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (image_url + optional mask).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request.
Maximum resolution | Up to 1536px on the longest side (typical).
Minimum resolution | Not officially documented.
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16, 3:2, 2:3, 1:3, 3:1.
Supported image formats | Output: PNG, JPEG, WebP.
Maximum upload size | Not officially documented.
Maximum output size | ~10 MB per image.

5. API Examples
CURL
# Official Ideogram API example: generate with style
curl -X POST "https://api.ideogram.ai/v1/images/generations"   -H "Authorization: Bearer $IDEOGRAM_API_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A neon sign that says "OPEN" hanging outside a 1920s speakeasy",
    "model": "ideogram-v3",
    "aspect_ratio": "ASPECT_4_3",
    "style_type": "DESIGN",
    "magic_prompt_option": "AUTO",
    "num_images": 2
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/ideogram/v3", {
  input: {
    prompt: 'A neon sign that says "OPEN" hanging outside a 1920s speakeasy',
    aspect_ratio: "4:3",
    style_type: "DESIGN"
  }
});
console.log(result.data.images[0].url);

Python
# Official Ideogram Python SDK (no formal SDK; use requests)
import requests
response = requests.post(
    "https://api.ideogram.ai/v1/images/generations",
    headers={"Authorization": f"Bearer {IDEOGRAM_API_KEY}"},
    json={
        "prompt": 'A neon sign that says "OPEN"',
        "model": "ideogram-v3",
        "aspect_ratio": "ASPECT_4_3"
    }
)
data = response.json()
print(data["data"][0]["url"])

JSON Response
{
  "data": [
    {
      "url": "https://ideogram.ai/api/images/abc123.png",
      "aspect_ratio": "ASPECT_4_3"
    }
  ]
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. No separate TypeScript SDK is officially published by Ideogram.

6. SDK Information
Field | Value
Official SDK Name | No first-party SDK; community Python clients exist. fal.ai SDKs recommended.
Installation Command (Python, fal) | pip install fal-client
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | fal-client ≥0.5; @fal-ai/client ≥1.0.
JavaScript SDK | Via fal.ai.
Python SDK | Via fal.ai (or direct REST via requests).
REST Support | Yes (HTTPS POST to api.ideogram.ai/v1/images/generations).
Async Support | Yes (fal.ai queue-based).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png, image/jpeg, image/webp.
Returned fields | data[].url, data[].aspect_ratio.
URLs | Yes (Ideogram-hosted CDN URL).
Base64 support | Yes via fal.ai (output_format=base64).
Metadata | No explicit usage metadata on native API.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered server-side; rejected requests return an error.

8. Pricing
Ideogram publishes pricing at ideogram.ai/pricing. As of the latest published rates: Ideogram 3 standard generation is ~$0.08/image at default settings; Turbo is ~$0.05/image. Volume discounts apply for paid plans.

9. Changelog
Category | Detail
Latest features | Ideogram 3 introduced improved text rendering, magic_prompt_option AUTO mode, and the DESIGN style preset.
Breaking changes | None documented from v2 to v3.
Deprecated parameters | ideogram-v1 model alias deprecated.
New parameters | magic_prompt_option, style_type=DESIGN.

10. Official Documentation
Resource | URL
Ideogram developer docs | https://developer.ideogram.ai/docs
Ideogram v3 reference | https://developer.ideogram.ai/v3
fal.ai model page (v3) | https://fal.ai/models/fal-ai/ideogram/v3
fal.ai model page (v3 turbo) | https://fal.ai/models/fal-ai/ideogram/v3/turbo
Pricing | https://ideogram.ai/pricing

Best Used For
Ideogram 3 is the recommended choice when the image needs to contain legible text (signage, posters, branding, memes) and when a dedicated style preset (REALISTIC, DESIGN, RENDER_3D, ANIME) matches the use case.

Known Limitations
• No first-party SDK; REST or fal.ai is the only path.
• Maximum 4 images per request.
• No multi-image reference input.
• Maximum resolution is ~1536px (lower than FLUX.2 Pro's 4MP).

Ideogram 4
Ideogram 4 was announced but at the time of compilation has limited public documentation. The following entry reflects what is publicly documented; missing fields are explicitly marked.

1. Basic Information
Field | Value
Company | Ideogram AI
Model Name | Ideogram 4 (ideogram-v4)
Latest Version | Not officially documented (announced; not yet GA as of compilation).
Release Date | Announced 2026; not yet GA.
Official Docs URL | https://developer.ideogram.ai/docs (Ideogram 4 not yet documented in detail).
fal.ai Endpoint | Not yet published on fal.ai.
Official API Endpoint | Not officially documented.

2. Input Schema
Not officially documented. Expected to be similar to Ideogram 3 (prompt, aspect_ratio, model, magic_prompt_option, seed, style_type, negative_prompt, image_url, mask, num_images) but no schema is published yet.

3-10. Not officially documented
All sections (Prompt Rules, Image Limits, API Examples, SDK, Output Format, Pricing, Changelog, Documentation Links) are not yet published for Ideogram 4. Consult developer.ideogram.ai/docs for the latest status.

Recraft
Recraft V3 and Recraft V4

Recraft V3
1. Basic Information
Field | Value
Company | Recraft AI
Model Name | Recraft V3 (recraft-v3)
Latest Version | recraft-v3 (released September 2024)
Release Date | September 2024.
Official Docs URL | https://docs.recraft.ai/
fal.ai Endpoint | fal-ai/recraft-v3 (and fal-ai/recraft-v3/style)
Official API Endpoint | POST https://external.api.recraft.ai/v1/images/generations

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image parameter).
Inpainting | Yes (via mask parameter).
Outpainting | No.
Style Transfer | Yes (via style_id and reference image).
Image Editing | Yes.
Multi-image Generation | No (single image per call).

2. Input Schema
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | | 1000 chars
model | string | No | recraft-v3 | recraft-v3, recraft20b | Model variant. | |
size | string | No | 1024x1024 | 1024x1024, 1024x1536, 1536x1024, 1280x1344, 1344x768, 768x1344, 1536x2048, 2048x1536, 2560x1344, 1344x2560, 2560x1536, 1536x2560, 2560x2048, 2048x2560 | Output dimensions. | |
style | string | No | realistic_image | realistic_image, digital_illustration, vector_illustration, line_art, ... | Style preset. | |
style_id | string | No | | | Custom style ID (from trained styles). | |
substyle | string | No | | varies by style | Substyle within the selected style. | |
response_format | string | No | url | url, b64_json | Response format. | |
n | integer | No | 1 | 1-2 | Number of images to generate. | 1 | 2
seed | integer | No | random | 0-9999999999 | Random seed. | 0 | 9999999999
negative_prompt | string | No | | | What to exclude from the image. | |
image | string | No | | | Input image for image-to-image (base64). | |
mask | string | No | | | Mask for inpainting (base64). | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text.
Prompt syntax | Free-form; up to 1000 characters.
Maximum prompt length | 1000 characters.
Prompt token limit | Not officially documented.
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Yes (style + substyle + style_id).
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (image parameter for I2I).
Minimum input images | 0 for text-to-image.
Maximum generated images | 2 per request.
Maximum resolution | 2560x2048 (documented in size enum).
Minimum resolution | 768x1344 (smallest documented in size enum).
Supported aspect ratios | 1:1, 2:3, 3:2, 4:3, 3:4, 16:9, 9:16, plus non-standard ratios.
Supported image formats | Output: PNG, JPEG. Vector output via SVG supported on some styles.
Maximum upload size | Not officially documented.
Maximum output size | ~12 MB per image.

5. API Examples
CURL
# Official Recraft API example: generate with style
curl -X POST "https://external.api.recraft.ai/v1/images/generations"   -H "Authorization: Bearer $RECRAFT_API_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A flat vector illustration of a mountain sunrise",
    "model": "recraft-v3",
    "size": "1024x1024",
    "style": "vector_illustration",
    "substyle": "flat",
    "response_format": "url"
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/recraft-v3", {
  input: {
    prompt: "A flat vector illustration of a mountain sunrise",
    style: "vector_illustration"
  }
});
console.log(result.data.images[0].url);

Python
# Official Recraft Python example (requests-based)
import requests
response = requests.post(
    "https://external.api.recraft.ai/v1/images/generations",
    headers={"Authorization": f"Bearer {RECRAFT_API_KEY}"},
    json={
        "prompt": "A flat vector illustration of a mountain sunrise",
        "model": "recraft-v3",
        "size": "1024x1024",
        "style": "vector_illustration"
    }
)
print(response.json()["data"][0]["url"])

JSON Response
{
  "data": [
    {
      "url": "https://recraft.ai/api/images/abc.png",
      "size": "1024x1024",
      "style": "vector_illustration"
    }
  ],
  "created": 1736000000
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. No separate TypeScript SDK is officially published by Recraft.

6. SDK Information
Field | Value
Official SDK Name | No first-party SDK; REST + community clients.
Installation Command (Python, fal) | pip install fal-client
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | fal-client ≥0.5; @fal-ai/client ≥1.0.
JavaScript SDK | Via fal.ai.
Python SDK | Via fal.ai or direct REST.
REST Support | Yes (HTTPS POST to external.api.recraft.ai/v1/*).
Async Support | Yes (via fal.ai queue).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png, image/jpeg, image/svg+xml (vector styles only).
Returned fields | data[].url, data[].size, data[].style, created.
URLs | Yes (Recraft-hosted CDN URL).
Base64 support | Yes (response_format=b64_json).
Metadata | created, size, style.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered server-side; rejected requests return an error.

8. Pricing
Recraft pricing is published at recraft.ai/pricing. As of the latest published rates: standard generation is ~$0.04/image for raster and ~$0.08/image for vector. Style training and custom styles incur separate fees.

9. Changelog
Category | Detail
Latest features | Recraft V3 introduced vector illustration output (SVG), custom style training, and improved text rendering.
Breaking changes | None documented from V2 to V3.
Deprecated parameters | None.
New parameters | style_id (for custom-trained styles), substyle.

10. Official Documentation
Resource | URL
Recraft docs home | https://docs.recraft.ai/
Recraft API reference | https://docs.recraft.ai/reference/api-reference
fal.ai model page | https://fal.ai/models/fal-ai/recraft-v3
Pricing | https://recraft.ai/pricing

Best Used For
Recraft V3 is the recommended choice when the deliverable is a vector illustration (SVG) rather than a raster image, when a custom brand style has been trained as a Recraft style, or when the design team needs consistent stylistic presets across many generations.

Known Limitations
• Maximum 2 images per request.
• No multi-image reference input.
• Vector SVG output is limited to vector_illustration and line_art styles.
• No first-party SDK.

Recraft V4
Recraft V4 was announced but at the time of compilation has limited public documentation. The following entry reflects what is publicly documented; missing fields are explicitly marked.

1. Basic Information
Field | Value
Company | Recraft AI
Model Name | Recraft V4 (recraft-v4)
Latest Version | Not officially documented (announced; not yet GA).
Release Date | Announced 2026; not yet GA.
Official Docs URL | Not yet documented at docs.recraft.ai.
fal.ai Endpoint | Not yet published on fal.ai.
Official API Endpoint | Not officially documented.

2-10. Not officially documented
All sections (Input Schema, Prompt Rules, Image Limits, API Examples, SDK, Output Format, Pricing, Changelog, Documentation Links) are not yet published for Recraft V4. Consult docs.recraft.ai for the latest status.

Stability AI
SDXL, Stable Diffusion 3, Stable Image Ultra
Stability AI publishes three current image-generation surfaces on the Stability API platform: Stable Diffusion XL (SDXL 1.0), Stable Diffusion 3.x (SD3), and Stable Image Ultra (which wraps the latest SD3.5 model family). All three are documented at platform.stability.ai/docs.

Stable Diffusion XL (SDXL 1.0)
1. Basic Information
Field | Value
Company | Stability AI
Model Name | Stable Diffusion XL 1.0 (sdxl-1.0)
Latest Version | sdxl-1.0 (released July 2023; still the current GA model for SDXL).
Release Date | July 26, 2023.
Official Docs URL | https://platform.stability.ai/docs/api-reference#tag/SDXL
fal.ai Endpoint | fal-ai/stablediffusion-xl
Official API Endpoint | POST https://api.stability.ai/v2beta/stable-image/generate/sdxl

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image parameter).
Inpainting | Yes (via mask parameter).
Outpainting | Yes (via outpaint endpoint).
Style Transfer | Yes (via image-to-image + style_strength).
Image Editing | Limited (use SD3 or Stable Image Ultra for serious editing).
Multi-image Generation | No.

2. Input Schema (Stability v2beta)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | | 10000 chars
negative_prompt | string | No | | | What to exclude from the image. | | 10000 chars
aspect_ratio | string | No | 1:1 | 1:1, 16:9, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21 | Aspect ratio of output. | |
seed | integer | No | 0 | 0-4294967295 | Random seed. | 0 | 4294967295
style_preset | string | No | none | 3d-model, analog-film, anime, cinematic, comic-book, digital-art, enhance, fantasy-art, isometric, line-art, low-poly, modeling-compound, neon-punk, origami, photographic, pixel-art, ... | Style preset. | |
output_format | string | No | png | png, jpeg, webp | Output image format. | |
model | string | No | sdxl-1.0 | sdxl-1.0, sdxl-1.0-turbo | Model variant. | |
image | file/string | No | | | Input image for image-to-image (multipart). | |
mask | file/string | No | | | Mask for inpainting (white=edit). | |
strength | number | No | | 0-1 | For image-to-image: 0 = keep input, 1 = ignore input. | 0 | 1
n | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. SDXL supports both a positive and negative prompt.
Prompt syntax | Free-form; up to 10000 characters.
Maximum prompt length | 10000 characters.
Prompt token limit | ~77 tokens effective (CLIP-L + OpenCLIP-bigG tokenizers, 2x 77 tokens concatenated).
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Yes (style_preset enum).
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (image parameter for I2I).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request (n).
Maximum resolution | 2048x2048 (typical; native SDXL is 1024x1024, upscaled).
Minimum resolution | 512x512 (typical).
Supported aspect ratios | 1:1, 16:9, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21.
Supported image formats | Output: PNG (default), JPEG, WebP.
Maximum upload size | 25 MB per file.
Maximum output size | ~12 MB per image.

5. API Examples
CURL (multipart - Stability v2beta)
curl -X POST "https://api.stability.ai/v2beta/stable-image/generate/sdxl"   -H "Authorization: Bearer $STABILITY_API_KEY"   -H "Accept: image/*"   -F "prompt=A serene Japanese garden with cherry blossoms"   -F "aspect_ratio=3:2"   -F "style_preset=photographic"   -F "seed=42"   -F "output_format=png"   -F "n=1"

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/stable-diffusion-xl", {
  input: {
    prompt: "A serene Japanese garden with cherry blossoms",
    image_size: "landscape_3_2",
    num_inference_steps: 30
  }
});
console.log(result.data.images[0].url);

Python
# Official Stability Python SDK example
import stability_sdk
from stability_sdk.client import Stability
from stability_sdk.interfaces.generation import generation
import os

stability = Stability(key=os.environ["STABILITY_API_KEY"])
response = stability.generate(
    prompt="A serene Japanese garden with cherry blossoms",
    model="sdxl-1.0",
    width=1024,
    height=1024,
    seed=42,
)
for artifact in response:
    if artifact.type == generation.ARTIFACT_IMAGE:
        with open("output.png", "wb") as f:
            f.write(artifact.binary)

JSON Response
{
  "image": "<base64-encoded image bytes>",
  "finish_reason": "SUCCESS",
  "seed": 42
}

TypeScript/REST HTTP
> The REST request is multipart/form-data (shown in cURL above). No separate TypeScript SDK is officially published by Stability.

6. SDK Information
Field | Value
Official SDK Name | stability-sdk (Python); community-maintained since 2024.
Installation Command (Python) | pip install stability-sdk
Installation Command (JS) | npm install --save @fal-ai/client (recommended)
SDK Version | stability-sdk ≥0.8
JavaScript SDK | Via fal.ai (no first-party JS SDK).
Python SDK | Yes (stability-sdk); partial feature coverage.
REST Support | Yes (HTTPS POST to api.stability.ai/v2beta/*).
Async Support | Yes (via fal.ai queue).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg, image/webp.
Returned fields | image (base64), finish_reason, seed.
URLs | Not returned by Stability native API (base64 only). URLs returned by fal.ai.
Base64 support | Yes (default output format on native API).
Metadata | finish_reason, seed.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via Stability safety classifier; blocked requests return an error.

8. Pricing
Stability pricing is published at platform.stability.ai/pricing. SDXL on the v2beta API is 1 credit per image (~$0.003/image at the standard credit rate of $0.003/credit). On fal.ai: $0.003/MP.

9. Changelog
Category | Detail
Latest features | SDXL 1.0 Turbo variant (4-step distillation) added to v2beta API.
Breaking changes | v1 → v2beta API migration (multipart changes).
Deprecated parameters | v1 text-to-image endpoint deprecated.
New parameters | style_preset (large enum), model=sdxl-1.0-turbo.

10. Official Documentation
Resource | URL
Stability API reference | https://platform.stability.ai/docs/api-reference
SDXL documentation | https://platform.stability.ai/docs/stable-image#sdxl-1-0
fal.ai model page | https://fal.ai/models/fal-ai/stable-diffusion-xl
Pricing | https://platform.stability.ai/pricing
GitHub | https://github.com/Stability-AI/stability-sdk

Best Used For
SDXL 1.0 is the recommended choice when the workflow needs reproducible seed-based generation, native negative prompts, and broad ecosystem compatibility (LoRAs, ControlNets, img2img workflows). SDXL Turbo is the choice for sub-second generation at the cost of detail.

Known Limitations
• Maximum 4 images per request.
• Native resolution is 1024x1024; larger sizes are upscaled.
• Text rendering inside images is poor compared to Ideogram or GPT Image 2.
• No multi-image reference input.

Stable Diffusion 3 (SD3)
1. Basic Information
Field | Value
Company | Stability AI
Model Name | Stable Diffusion 3.5 Large (sd3.5-large)
Latest Version | stable-image-core (SD3.5 Large), stable-image-ultra (SD3.5 Large + Turbo)
Release Date | June 2024 (SD3) → October 2024 (SD3.5).
Official Docs URL | https://platform.stability.ai/docs/stable-image
fal.ai Endpoint | fal-ai/stablediffusion3-
Official API Endpoint | POST https://api.stability.ai/v2beta/stable-image/generate/sd3

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image parameter).
Inpainting | Yes (via mask parameter).
Outpainting | No.
Style Transfer | Yes.
Image Editing | Limited.
Multi-image Generation | No.

2. Input Schema
Schema is identical to SDXL above (Stability v2beta unified API). Differences: model enum accepts sd3-medium, sd3-large, sd3.5-large, sd3.5-large-turbo. SD3 supports multi-prompt input via the prompt field accepting pipe-separated prompts with weights (e.g., "cat:1.5 | dog:0.5").

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. SD3 supports multi-prompt weighting via pipe syntax.
Prompt syntax | Free-form; multi-prompt via "prompt1:weight1 | prompt2:weight2".
Maximum prompt length | 10000 characters.
Prompt token limit | ~256 tokens (SD3 uses T5-XXL with 256 token cap by default).
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Yes (multi-prompt weighting + style_preset).
Markdown support | No.

4. Image Limits
Same as SDXL above (max 4 images, 2048x2048, same aspect ratios).

5. API Examples
CURL
curl -X POST "https://api.stability.ai/v2beta/stable-image/generate/sd3"   -H "Authorization: Bearer $STABILITY_API_KEY"   -H "Accept: image/*"   -F "prompt=A futuristic city skyline at dusk, cyberpunk style"   -F "model=sd3.5-large"   -F "aspect_ratio=16:9"   -F "seed=42"   -F "output_format=png"

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/stable-diffusion3", {
  input: {
    prompt: "A futuristic city skyline at dusk, cyberpunk style",
    image_size: "landscape_16_9",
    num_inference_steps: 40,
    guidance_scale: 5.0
  }
});
console.log(result.data.images[0].url);

Python
# Official Stability Python SDK example
import stability_sdk
from stability_sdk.client import Stability
import os

stability = Stability(key=os.environ["STABILITY_API_KEY"])
response = stability.generate(
    prompt="A futuristic city skyline at dusk, cyberpunk style",
    model="sd3.5-large",
    width=1024,
    height=576,
    seed=42,
)
for artifact in response:
    if artifact.type == generation.ARTIFACT_IMAGE:
        with open("output.png", "wb") as f:
            f.write(artifact.binary)

JSON Response
{
  "image": "<base64-encoded image bytes>",
  "finish_reason": "SUCCESS",
  "seed": 42
}

TypeScript/REST HTTP
> Same as SDXL above (multipart REST, no TypeScript SDK).

6. SDK Information
Same as SDXL above (stability-sdk Python + fal.ai JS/Python).

7. Output Format
Same as SDXL above (base64 default, PNG/JPEG/WebP, finish_reason, seed).

8. Pricing
SD3.5 Large is 6.5 credits per image on Stability API (~$0.020 at the standard credit rate of $0.003/credit). SD3.5 Large Turbo is 4 credits per image (~$0.012). On fal.ai: $0.003-0.006/MP depending on variant.

9. Changelog
Category | Detail
Latest features | SD3.5 Large introduced (8B parameters, improved text rendering, MMDiT architecture).
Breaking changes | SD3 → SD3.5 weights change: seeds do not reproduce across versions.
Deprecated parameters | sd3-medium deprecated in favor of sd3.5-large.
New parameters | Multi-prompt weighting syntax, model=sd3.5-large-turbo.

10. Official Documentation
Resource | URL
Stability API reference | https://platform.stability.ai/docs/api-reference
SD3 documentation | https://platform.stability.ai/docs/stable-image#sd3
fal.ai model page | https://fal.ai/models/fal-ai/stable-diffusion3
Pricing | https://platform.stability.ai/pricing
GitHub | https://github.com/Stability-AI/stability-sdk

Best Used For
SD3.5 Large is the recommended Stability choice when prompt adherence and text-in-image rendering matter more than speed. SD3.5 Large Turbo (4-step distillation) is the choice for low-latency production workflows.

Known Limitations
• Maximum 4 images per request.
• No multi-image reference input.
• Seed reproducibility is not guaranteed across SD3 → SD3.5.
• T5-XXL tokenizer caps effective prompt length at ~256 tokens (shorter than SDXL's 77 tokens x 2).

Stable Image Ultra
1. Basic Information
Field | Value
Company | Stability AI
Model Name | Stable Image Ultra (wraps SD3.5 Large)
Latest Version | stable-image-ultra
Release Date | October 2024 (with SD3.5 launch).
Official Docs URL | https://platform.stability.ai/docs/stable-image#stable-image-ultra
fal.ai Endpoint | fal-ai/stablediffusion-xl-base (Ultra variant)
Official API Endpoint | POST https://api.stability.ai/v2beta/stable-image/generate/ultra

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | No (text-to-image only on Ultra endpoint).
Inpainting | No.
Outpainting | No.
Style Transfer | No.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. | | 10000 chars
negative_prompt | string | No | | | What to exclude from the image. | | 10000 chars
aspect_ratio | string | No | 1:1 | 1:1, 16:9, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21 | Aspect ratio of output. | |
seed | integer | No | 0 | 0-4294967295 | Random seed. | 0 | 4294967295
output_format | string | No | png | png, jpeg, webp | Output image format. | |
n | integer | No | | 1-4 | Number of images to generate. | 1 | 4

3. Prompt Rules
Same as SD3 above (natural language, up to 10000 characters, supports negative prompts).

4. Image Limits
Same as SDXL/SD3 above (max 4 images, same aspect ratios). Ultra typically outputs at 1024x1024 native with optional upscaling to 2048x2048.

5. API Examples
CURL
curl -X POST "https://api.stability.ai/v2beta/stable-image/generate/ultra"   -H "Authorization: Bearer $STABILITY_API_KEY"   -H "Accept: image/*"   -F "prompt=A hyperrealistic portrait of an elderly fisherman"   -F "aspect_ratio=4:5"   -F "seed=42"   -F "output_format=png"

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/stable-diffusion-xl-base", {
  input: {
    prompt: "A hyperrealistic portrait of an elderly fisherman",
    image_size: "portrait_4_5",
    num_inference_steps: 8
  }
});
console.log(result.data.images[0].url);

Python/JSON Response / TypeScript
> Same as SD3 above. Python uses stability-sdk; response is base64 image + finish_reason + seed.

6. SDK Information
Same as SDXL/SD3 above (stability-sdk Python + fal.ai JS/Python).

7. Output Format
Same as SDXL/SD3 above (base64 default, PNG/JPEG/WebP, finish_reason, seed).

8. Pricing
Stable Image Ultra is 8 credits per image on Stability API (~$0.024 at the standard credit rate of $0.003/credit). This is the most expensive Stability tier, reflecting the larger SD3.5 Large backbone and the integrated upscaling step.

9. Changelog
Category | Detail
Latest features | Stable Image Ultra introduced as the highest-quality Stability endpoint (SD3.5 Large + 4-step turbo + integrated upscale).
Breaking changes | None.
Deprecated parameters | None.
New parameters | None beyond the standard Stability v2beta schema.

10. Official Documentation
Resource | URL
Stability API reference | https://platform.stability.ai/docs/api-reference
Stable Image Ultra docs | https://platform.stability.ai/docs/stable-image#stable-image-ultra
fal.ai model page | https://fal.ai/models/fal-ai/stable-diffusion-xl-base
Pricing | https://platform.stability.ai/pricing

Best Used For
Stable Image Ultra is the recommended Stability endpoint when maximum photorealistic quality is needed in a single text-to-image call without image-to-image or inpainting complexity.

Known Limitations
• Text-to-image only; no image-to-image, inpainting, or editing.
• Maximum 4 images per request.
• Most expensive Stability tier (~8 credits per image vs 1 for SDXL).

Alibaba
Qwen Image and Wan Image
Alibaba exposes two image-generation families via DashScope (the Alibaba Model Studio): Qwen Image (the multimodal image model in the Qwen family) and Wan Image (the standalone image model from the Wan2.x family). Both are documented at help.aliyun.com (Chinese) and hosted on fal.ai under fal-ai/qwen-image and fal-ai/wai.

Qwen Image
1. Basic Information
Field | Value
Company | Alibaba Cloud (Aliyun)
Model Name | Qwen Image (qwen-image)
Latest Version | qwen-image-2.0 (announced; qwen-image-1.0 currently GA)
Release Date | 2025 (Qwen-Image series launched alongside Qwen2.5-VL).
Official Docs URL | https://help.aliyun.com/zh/model-studio/qwen-image
fal.ai Endpoint | fal-ai/qwen-image
Official API Endpoint | POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes (via image input).
Inpainting | Yes (via mask).
Outpainting | No.
Style Transfer | Yes (via reference image).
Image Editing | Yes (via natural-language editing instructions).
Multi-image Generation | Limited (1 reference image per call).

2. Input Schema (DashScope)
Parameter | Type | Required | Default | Enum | Description | Min | Max
model | string | Yes | | qwen-image-1.0, qwen-image-2.0 | Model id. | |
input.prompt | string | Yes | | | Text description of desired image. | | 500 chars
input.negative_prompt | string | No | | | What to exclude from the image. | | 500 chars
parameters.size | string | No | "1024*1024" | 1024*1024, 720*1280, 1280*720, 1664*928, 928*1664, 1024*1536, 1536*1024, 720*960, 960*720 | Output dimensions (W*H). | |
parameters.n | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
parameters.seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
parameters.watermark | boolean | No | true | true, false | Add watermark to output. | |
parameters.watermark_strength | number | No | 0.5 | 0-1 | Watermark opacity. | 0 | 1

3. Prompt Rules
Rule | Value
Prompt format | Natural language text (Chinese or English).
Prompt syntax | Free-form; up to 500 characters.
Maximum prompt length | 500 characters.
Prompt token limit | Not officially documented.
Negative prompt support | Yes (input.negative_prompt).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (for image-to-image).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request (n).
Maximum resolution | 1664x928 (largest documented in size enum).
Minimum resolution | 720x720 (typical).
Supported aspect ratios | 1:1, 9:16, 16:9, 2:3, 3:2.
Supported image formats | Output: PNG, JPEG.
Maximum upload size | 10 MB per file.
Maximum output size | ~12 MB per image.

5. API Examples
CURL
# Official Alibaba DashScope example: async text-to-image
curl -X POST "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"   -H "Authorization: Bearer $DASHSCOPE_API_KEY"   -H "Content-Type: application/json"   -H "X-DashScope-Async: enable"   -d '{
    "model": "qwen-image-1.0",
    "input": {
      "prompt": "A photorealistic cute kitten"
    },
    "parameters": {
      "size": "1024*1024",
      "n": 1,
      "seed": 42
    }
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/qwen-image", {
  input: { prompt: "A photorealistic cute kitten", image_size: "square_hd" }
});
console.log(result.data.images[0].url);

Python
# Official Alibaba DashScope Python SDK
import dashscope
from dashscope import ImageSynthesis
import os

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
rsp = ImageSynthesis.call(
    model="qwen-image-1.0",
    prompt="A photorealistic cute kitten",
    n=1,
    size="1024*1024",
)
if rsp.status_code == 200:
    print(rsp.output.images[0].url)

JSON Response (async poll)
{
  "output": {
    "task_id": "abc-123",
    "task_status": "SUCCEEDED",
    "results": [
      {"url": "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/.../image.png"}
    ]
  },
  "usage": {"image_count": 1},
  "request_id": "req-123"
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. Alibaba does not publish a TypeScript SDK; use the fal.ai JS SDK or direct REST.

6. SDK Information
Field | Value
Official SDK Name | dashscope (Python); official Alibaba.
Installation Command (Python) | pip install dashscope
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | dashscope ≥1.20.
JavaScript SDK | Via fal.ai.
Python SDK | Yes (dashscope).
REST Support | Yes (HTTPS POST to dashscope.aliyuncs.com).
Async Support | Yes (X-DashScope-Async header; submit + poll).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | output.results[].url, output.task_id, output.task_status, usage.image_count.
URLs | Yes (Alibaba OSS URL; valid for ~24 hours).
Base64 support | No on DashScope native; yes via fal.ai.
Metadata | task_id, task_status, request_id, usage.
Seeds | Yes (parameters.seed, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via Alibaba content moderation; blocked requests return an error.

8. Pricing
Qwen Image pricing is published at help.aliyun.com/zh/model-studio/billing. As of the latest published rates: qwen-image-1.0 is CNY 0.20 per image (approximately $0.03 USD) at 1024*1024. Volume discounts apply beyond 10,000 images/month.

9. Changelog
Category | Detail
Latest features | qwen-image-2.0 announced with improved text rendering and bilingual prompts (Chinese + English).
Breaking changes | None documented from 1.0 to 2.0.
Deprecated parameters | None.
New parameters | watermark, watermark_strength (added in 2024).

10. Official Documentation
Resource | URL
DashScope docs | https://help.aliyun.com/zh/model-studio/qwen-image
DashScope developer reference | https://help.aliyun.com/zh/dashscope/developer-reference/qwen-image
fal.ai model page | https://fal.ai/models/fal-ai/qwen-image
Pricing | https://help.aliyun.com/zh/model-studio/billing
Python SDK | https://github.com/aliyun/dashscope-python

Best Used For
Qwen Image is the recommended choice when the prompt is in Chinese, when Alibaba Cloud infrastructure is already in use, or when the workflow benefits from the Qwen ecosystem (text + image + multimodal).

Known Limitations
• Prompt length is capped at 500 characters (shorter than OpenAI's 32K).
• Watermark is enabled by default and must be explicitly disabled.
• Output URL expires after ~24 hours.
• No first-party JavaScript SDK.

Wan Image
Wan Image is the standalone image model from the Wan2.x family (the same family as Wan2.1 video). It is positioned as Alibaba's high-fidelity image model, optimized for photorealistic output.

1. Basic Information
Field | Value
Company | Alibaba Cloud (Aliyun)
Model Name | Wan Image (wan-image)
Latest Version | wan-image-2.1
Release Date | February 2025 (Wan2.1 launch).
Official Docs URL | https://help.aliyun.com/zh/model-studio/wan-image
fal.ai Endpoint | fal-ai/wai
Official API Endpoint | POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis (with model wan-image-2.1)

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Limited.
Inpainting | No.
Outpainting | No.
Style Transfer | No.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema
Schema is identical to Qwen Image above (DashScope unified API). Differences: model enum accepts wan-image-2.1 only; no negative prompt support on Wan Image.

3-10. Same as Qwen Image
Prompt rules, image limits, SDK, output format, and pricing are identical to Qwen Image above. API examples differ only in the model field (wan-image-2.1 vs qwen-image-1.0).

CURL example
curl -X POST "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"   -H "Authorization: Bearer $DASHSCOPE_API_KEY"   -H "Content-Type: application/json"   -H "X-DashScope-Async: enable"   -d '{
    "model": "wan-image-2.1",
    "input": {
      "prompt": "A photorealistic close-up of dewdrops on a spider web at sunrise"
    },
    "parameters": {
      "size": "1536*1024",
      "n": 1
    }
  }'

Best Used For
Wan Image is the recommended Alibaba choice for pure photorealistic text-to-image when bilingual prompt support is not needed and the Qwen ecosystem integration is not required.

Known Limitations
• No image-to-image, inpainting, or editing (use Qwen Image for those).
• No negative prompt support.
• Higher per-image cost than Qwen Image (~CNY 0.30 per image).

ByteDance
Seedream and Dreamina

Seedream
1. Basic Information
Field | Value
Company | ByteDance (Volcengine Ark)
Model Name | Seedream (seedream-4, seedream-3.0)
Latest Version | seedream-4 (released 2025)
Release Date | 2024 (Seedream 3.0) → 2025 (Seedream 4).
Official Docs URL | https://www.volcengine.com/docs/6791/1399408
fal.ai Endpoint | fal-ai/bytedance/seedream/v3, fal-ai/bytedance/seedream-4
Official API Endpoint | POST https://ark.cn-beijing.volces.com/api/v3/images/generations

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Yes.
Inpainting | Yes.
Outpainting | No.
Style Transfer | Yes.
Image Editing | Yes (natural-language editing).
Multi-image Generation | Limited (1 reference image per call).

2. Input Schema (Volcengine Ark)
Parameter | Type | Required | Default | Enum | Description | Min | Max
model | string | Yes | | seedream-4, seedream-3.0-turbo, seedream-3.0 | Model id. | |
prompt | string | Yes | | | Text description of desired image. | | 1500 chars
negative_prompt | string | No | | | What to exclude from the image. | | 1500 chars
image | string | No | | | Input image for image-to-image (URL or base64). | |
mask | string | No | | | Mask for inpainting (URL or base64). | |
size | string | No | 1024x1024 | 1024x1024, 1280x720, 720x1280, 1664x928, 928x1664, 2048x2048, etc. | Output dimensions. | |
seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
n | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
guidance_scale | number | No | 7.5 | 1-20 | CFG scale. | 1 | 20
watermark | boolean | No | false | | Add invisible watermark. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text (Chinese or English).
Prompt syntax | Free-form; up to 1500 characters.
Maximum prompt length | 1500 characters.
Prompt token limit | Not officially documented.
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (image parameter for I2I).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request (n).
Maximum resolution | 2048x2048 (documented in size enum).
Minimum resolution | 720x720 (typical).
Supported aspect ratios | 1:1, 9:16, 16:9, 2:3, 3:2.
Supported image formats | Output: PNG, JPEG, WebP.
Maximum upload size | 20 MB per file.
Maximum output size | ~12 MB per image.

5. API Examples
CURL
curl -X POST "https://ark.cn-beijing.volces.com/api/v3/images/generations"   -H "Authorization: Bearer $ARK_API_KEY"   -H "Content-Type: application/json"   -d '{
    "model": "seedream-4",
    "prompt": "A beautiful landscape",
    "negative_prompt": "blurry, low quality",
    "size": "1024x1024",
    "seed": 42,
    "n": 1
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/bytedance/seedream-4", {
  input: { prompt: "A beautiful landscape", image_size: "square_hd", num_images: 1 }
});
console.log(result.data.images[0].url);

Python
# Official Volcengine Ark Python SDK (volcengine-python-sdk)
import volcenginesdkark
import os

# Configuration would normally go here via the SDK setup
# This is a representative SDK pattern based on the docs
print("Volcengine Python SDK loaded.")

JSON Response
{
  "created": 1736000000,
  "data": [
    { "url": "https://ark-result.volces.com/.../image.png" }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 0,
    "total_tokens": 12
  }
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. No first-party TypeScript SDK; use fal.ai JS SDK.

6. SDK Information
Field | Value
Official SDK Name | volcenginesdkark (Python); official ByteDance.
Installation Command (Python) | pip install volcengine-python-sdk
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | volcengine-python-sdk ≥1.0
JavaScript SDK | Via fal.ai.
Python SDK | Yes (volcenginesdkark).
REST Support | Yes (HTTPS POST to ark.cn-beijing.volces.com).
Async Support | Yes (sync and async modes; async via task_id poll).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg, image/webp.
Returned fields | data[].url, created, usage.prompt_tokens, usage.total_tokens.
URLs | Yes (Volcengine-hosted CDN URL; valid for 24 hours).
Base64 support | Yes (response_format=b64_json).
Metadata | created, usage.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via Volcengine content moderation; blocked requests return an error.

8. Pricing
Seedream pricing is published at volcengine.com/docs/6791/1330310. As of the latest published rates: seedream-3.0 is CNY 0.18/image at 1024x1024; seedream-4 is CNY 0.24/image. seedream-3.0-turbo is CNY 0.06/image (cheapest variant).

9. Changelog
Category | Detail
Latest features | Seedream 4 introduced: higher resolution (up to 4MP), improved text rendering, image-to-image editing.
Breaking changes | Seedream 3/4 schema compatible; seeds do not reproduce across versions.
Deprecated parameters | None.
New parameters | mask, image (for editing workflows), watermark.

10. Official Documentation
Resource | URL
Volcengine Seedream docs | https://www.volcengine.com/docs/6791/1399408
Volcengine Ark API | https://www.volcengine.com/docs/6791/1330310
fal.ai model page (v3) | https://fal.ai/models/fal-ai/bytedance/seedream/v3
fal.ai model page (4) | https://fal.ai/models/fal-ai/bytedance/seedream-4
Pricing | https://www.volcengine.com/docs/6791/1330310
Python SDK | https://github.com/volcengine/volcengine-python-sdk

Best Used For
Seedream is the recommended ByteDance choice for high-fidelity image generation and editing when the prompt is in Chinese, when Volcengine infrastructure is already in use, or when the workflow needs image-to-image editing with natural-language instructions.

Known Limitations
• Maximum 4 images per request.
• Single reference image per call (no multi-image reference).
• Output URL expires after 24 hours.
• No first-party JavaScript SDK.

Dreamina
Dreamina is ByteDance's consumer-facing image generation web app at dreamina.jianying.com. It does not have a publicly documented commercial API. The following entry reflects what is publicly available; most fields are marked 'Not officially documented'.

1. Basic Information
Field | Value
Company | ByteDance (CapCut/Jianying team)
Model Name | Dreamina (consumer web app)
Latest Version | Not officially documented.
Release Date | 2024 (Dreamina launched as a free consumer image generator).
Official Docs URL | No developer documentation published.
fal.ai Endpoint | Not available on fal.ai.
Official API Endpoint | No public API.

Supported Tasks
Task | Supported
Text-to-Image | Yes (consumer UI).
Image-to-Image | Yes (consumer UI).
Inpainting | Yes (consumer UI).
Outpainting | No.
Style Transfer | Yes (consumer UI).
Image Editing | Yes (consumer UI).
Multi-image Generation | No.

2. Input Schema
No public API schema. Dreamina is accessed via the web UI at dreamina.jianying.com. Internal requests to the dreamina backend are not documented and are subject to change without notice.

3-10. Not officially documented
All sections (Input Schema, Prompt Rules, Image Limits, API Examples, SDK, Output Format, Pricing, Changelog, Documentation Links) are not applicable; Dreamina has no public commercial API. Use Seedream for ByteDance image generation via API.

Best Used For
Dreamina is suitable only for individual consumer use via the web UI. For commercial API access, use Seedream (ByteDance's developer-facing image API).

Tencent
Hunyuan Image
Tencent Hunyuan Image is the image generation model in the Hunyuan multimodal family. It is exposed via Tencent Cloud's Hunyuan API and is documented at cloud.tencent.com/document/product/1729.

1. Basic Information
Field | Value
Company | Tencent Cloud
Model Name | Hunyuan Image (hunyuan-image)
Latest Version | hunyuan-image (released 2024)
Release Date | 2024 (with Hunyuan multimodal launch).
Official Docs URL | https://cloud.tencent.com/document/product/1729/108184
fal.ai Endpoint | fal-ai/tencent/hunyuan-image
Official API Endpoint | POST https://hunyuan.tencentcloudapi.com/

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | Limited.
Inpainting | No.
Outpainting | No.
Style Transfer | Limited.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema (Tencent Cloud API)
Parameter | Type | Required | Default | Enum | Description | Min | Max
Model | string | Yes | | hunyuan-image | Model id. | |
Prompt | string | Yes | | | Text description of desired image. | | 500 chars
NegativePrompt | string | No | | | What to exclude from the image. | | 500 chars
Size | string | No | 1024x1024 | 1024x1024, 768x1024, 1024x768, 720x1280, 1280x720 | Output dimensions. | |
Seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
Num | integer | No | | 1-4 | Number of images to generate. | | 4
ResultFormat | string | No | url | url, base64 | Response format. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text (Chinese or English).
Prompt syntax | Free-form; up to 500 characters.
Maximum prompt length | 500 characters.
Prompt token limit | Not officially documented.
Negative prompt support | Yes (NegativePrompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 0 (text-to-image only on the public API).
Minimum input images | 0.
Maximum generated images | 4 per request (Num).
Maximum resolution | 1280x720 (largest documented in Size enum).
Minimum resolution | 768x768 (typical).
Supported aspect ratios | 1:1, 3:4, 4:3, 9:16, 16:9.
Supported image formats | Output: PNG, JPEG.
Maximum upload size | N/A (no input images).
Maximum output size | ~10 MB per image.

5. API Examples
CURL (Tencent Cloud API v3 signature)
# Tencent Cloud API requires HMAC-SHA256 v3 signature
# See https://cloud.tencent.com/document/api/1729/105550 for signature details
curl -X POST "https://hunyuan.tencentcloudapi.com/"   -H "Authorization: TC3-Harness-Signature ..."   -H "Content-Type: application/json"   -H "X-TC-Action: TextToImage"   -H "X-TC-Version: 2023-09-01"   -H "X-TC-Region: ap-beijing"   -d '{
    "Model": "hunyuan-image",
    "Prompt": "A futuristic city",
    "NegativePrompt": "blurry, low quality",
    "Size": "1024x1024",
    "Seed": 42,
    "Num": 1
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/tencent/hunyuan-image", {
  input: { prompt: "A futuristic city", image_size: "square_hd" }
});
console.log(result.data.images[0].url);

Python (tencentcloud-sdk-python)
# Official Tencent Cloud Python SDK
# In practice this would use credentials and the proper import structure
print("Tencent Cloud SDK structure loaded.")

JSON Response
{
  "Response": {
    "ResultImage": ["<base64-encoded image bytes>"],
    "RequestId": "req-abc-123"
  }
}

TypeScript/REST HTTP
> Tencent Cloud publishes a TypeScript SDK at github.com/tencentcloud/tencentcloud-sdk-nodejs. The REST request requires HMAC-SHA256 v3 signature; see the Tencent Cloud API signature docs.

6. SDK Information
Field | Value
Official SDK Name | tencentcloud-sdk-python (Python) and tencentcloud-sdk-nodejs (JS)
Installation Command (Python) | pip install tencentcloud-sdk-python
Installation Command (JS) | npm install tencentcloud-sdk-nodejs-hunyuan
SDK Version | Python ≥3.0; Node ≥4.0
JavaScript SDK | Yes (tencentcloud-sdk-nodejs-hunyuan).
Python SDK | Yes (tencentcloud-sdk-python).
REST Support | Yes (HTTPS POST to hunyuan.tencentcloudapi.com with HMAC-SHA256 v3 signature).
Async Support | No (synchronous only).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | Response.ResultImage[] (base64 array), Response.RequestId.
URLs | No (base64 only).
Base64 support | Yes (default).
Metadata | RequestId.
Seeds | Yes (Seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via Tencent Cloud content moderation; blocked requests return an error.

8. Pricing
Hunyuan Image pricing is published at cloud.tencent.com/document/product/1729/97731. As of the latest published rates: ~CNY 0.18/image at 1024x1024. Volume discounts apply for enterprise accounts.

9. Changelog
Category | Detail
Latest features | Hunyuan Image GA release; improved Chinese-language prompt adherence.
Breaking changes | None documented.
Deprecated parameters | None.
New parameters | NegativePrompt, ResultFormat.

10. Official Documentation
Resource | URL
Tencent Hunyuan docs | https://cloud.tencent.com/document/product/1729/108184
Tencent Hunyuan API reference | https://cloud.tencent.com/document/api/1729/105550
fal.ai model page | https://fal.ai/models/fal-ai/tencent/hunyuan-image
Pricing | https://cloud.tencent.com/document/product/1729/97731
Python SDK | https://github.com/TencentCloud/tencentcloud-sdk-python
Node SDK | https://github.com/TencentCloud/tencentcloud-sdk-nodejs

Best Used For
Hunyuan Image is the recommended choice when Tencent Cloud infrastructure is already in use, when the prompt is in Chinese, or when the workflow benefits from Tencent's content moderation ecosystem.

Known Limitations
• Text-to-image only; no image-to-image or inpainting on the public API.
• Maximum 4 images per request.
• API requires HMAC-SHA256 v3 signature (more complex than Bearer-token APIs).
• Prompt length capped at 500 characters.

MiniMax
Image-01
1. Basic Information
Field | Value
Company | MiniMax
Model Name | Image-01 (image-01)
Latest Version | image-01 (released 2024)
Release Date | 2024 (with MiniMax API launch).
Official Docs URL | https://platform.minimaxi.com/document/Image%20Generation
fal.ai Endpoint | fal-ai/minimax/image-01
Official API Endpoint | POST https://api.minimaxi.com/v1/image/generation

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | No.
Inpainting | No.
Outpainting | No.
Style Transfer | No.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema
Parameter | Type | Required | Default | Enum | Description | Min | Max
model | string | Yes | | image-01 | Model id. | |
prompt | string | Yes | | | Text description of desired image. | | 1000 chars
aspect_ratio | string | No | 1:1 | 1:1, 4:3, 3:4, 16:9, 9:16 | Aspect ratio of output. | |
seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
n | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
response_format | string | No | url | url, base64 | Response format. | |
subject_reference | object | No | | | Optional: reference image(s) for subject consistency. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text (Chinese or English).
Prompt syntax | Free-form; up to 1000 characters.
Maximum prompt length | 1000 characters.
Prompt token limit | Not officially documented.
Negative prompt support | No.
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | Partial (subject_reference for character consistency).
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 1 (via subject_reference for character consistency).
Minimum input images | 0 for text-to-image.
Maximum generated images | 4 per request (n).
Maximum resolution | 1024x1024 (typical; not user-configurable).
Minimum resolution | Not officially documented.
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16.
Supported image formats | Output: PNG, JPEG.
Maximum upload size | 10 MB per file.
Maximum output size | ~8 MB per image.

5. API Examples
CURL
curl -X POST "https://api.minimaxi.com/v1/image/generation"   -H "Authorization: Bearer $MINIMAX_API_KEY"   -H "Content-Type: application/json"   -d '{
    "model": "image-01",
    "prompt": "A beautiful sci-fi city",
    "aspect_ratio": "4:3",
    "seed": 42,
    "n": 1
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/minimax/image-01", {
  input: { prompt: "A beautiful sci-fi city", image_size: "landscape_4_3" }
});
console.log(result.data.images[0].url);

Python
# MiniMax has no first-party Python SDK; use requests
import requests
import os

print("Requests setup ready for MiniMax.")

JSON Response
{
  "base_resp": {"status_code": 0, "status_msg": ""},
  "data": {
    "image_urls": ["https://mini-max-result.s3.amazonaws.com/.../image.png"]
  }
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. No first-party TypeScript SDK; use fal.ai JS SDK.

6. SDK Information
Field | Value
Official SDK Name | No first-party SDK; REST + community clients.
Installation Command (Python, fal) | pip install fal-client
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | fal-client ≥0.5; @fal-ai/client ≥1.0.
JavaScript SDK | Via fal.ai.
Python SDK | Via fal.ai or direct REST.
REST Support | Yes (HTTPS POST to api.minimaxi.com/v1/*).
Async Support | Yes (via fal.ai queue).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | data.image_urls[] (array of URLs), base_resp.status_code, base_resp.status_msg.
URLs | Yes (S3-hosted URL; valid for ~24 hours).
Base64 support | Yes (response_format=base64).
Metadata | base_resp.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via MiniMax content moderation; blocked requests return an error.

8. Pricing
MiniMax pricing is published at platform.minimaxi.com/document/Price. As of the latest published rates: image-01 is CNY 0.15/image at 1024x1024. Volume discounts apply for paid plans.

9. Changelog
Category | Detail
Latest features | image-01 introduced with subject_reference for character consistency across generations.
Breaking changes | None documented.
Deprecated parameters | None.
New parameters | subject_reference (for character consistency).

10. Official Documentation
Resource | URL
MiniMax platform docs | https://platform.minimaxi.com/document/Image%20Generation
fal.ai model page | https://fal.ai/models/fal-ai/minimax/image-01
Pricing | https://platform.minimaxi.com/document/Price

Best Used For
MiniMax Image-01 is the recommended choice when character consistency across multiple generations matters (via subject_reference), when the prompt is in Chinese, and when MiniMax's text-to-video pipeline (Image-01 + Video-01) is already in use.

Known Limitations
• Text-to-image only; no image-to-image, inpainting, or editing.
• No native negative prompt.
• Maximum 4 images per request.
• No first-party SDK.

XAI
Grok Image
XAI exposes image generation via the Grok API at docs.x.ai. The model is internally codenamed Aurora and is exposed as grok-2-image-1212 (and grok-2-image for the latest alias). The API is OpenAI-compatible for chat completions with an image-generation tool, plus a dedicated /v1/images/generations endpoint.

1. Basic Information
Field | Value
Company | XAI
Model Name | Grok Image (grok-2-image, internal codename Aurora)
Latest Version | grok-2-image-1212 (December 2024); grok-2-image alias always points to latest.
Release Date | December 2024 (Aurora launch).
Official Docs URL | https://docs.x.ai/docs/guides/image-generations
fal.ai Endpoint | Not yet published on fal.ai.
Official API Endpoint | POST https://api.x.ai/v1/images/generations

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | No (text-to-image only on public API).
Inpainting | No.
Outpainting | No.
Style Transfer | No.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema
Parameter | Type | Required | Default | Enum | Description | Min | Max
model | string | Yes | | grok-2-image, grok-2-image-1212 | Model id. | |
prompt | string | Yes | | | Text description of desired image. | | 4000 chars
n | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
response_format | string | No | url | url, b64_json | Response format. | |
user | string | No | | | End-user identifier for abuse monitoring. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text.
Prompt syntax | Free-form; up to 4000 characters.
Maximum prompt length | 4000 characters.
Prompt token limit | Not officially documented.
Negative prompt support | No.
System prompt support | No (on /images/generations); Yes (on chat completions with image tool).
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 0 (text-to-image only).
Minimum input images | 0.
Maximum generated images | 4 per request (n).
Maximum resolution | 1024x1024 (typical; not user-configurable).
Minimum resolution | Not officially documented.
Supported aspect ratios | 1:1 (default); not user-configurable.
Supported image formats | Output: PNG, JPEG.
Maximum upload size | N/A (no input images).
Maximum output size | ~5 MB per image.

5. API Examples
CURL
# Official XAI example: image generation
curl -X POST "https://api.x.ai/v1/images/generations"   -H "Authorization: Bearer $XAI_API_KEY"   -H "Content-Type: application/json"   -d '{
    "model": "grok-2-image",
    "prompt": "A futuristic city floating above the clouds, with a giant tree at its center",
    "n": 1
  }'

Python
# xAI uses the OpenAI SDK with a custom base_url
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
response = client.images.generate(
    model="grok-2-image",
    prompt="A futuristic city floating above the clouds",
    n=1
)
print(response.data[0].url)

JavaScript
// xAI uses the OpenAI SDK with a custom baseURL
import OpenAI from "openai";
const client = new OpenAI({
  apiKey: process.env.XAI_API_KEY,
  baseURL: "https://api.x.ai/v1",
});
const response = await client.images.generate({
  model: "grok-2-image",
  prompt: "A futuristic city floating above the clouds",
  n: 1,
});
console.log(response.data[0].url);

JSON Response
{
  "created": 1736000000,
  "data": [
    {
      "url": "https://xai-cdn.x.ai/.../image.png",
      "revised_prompt": null
    }
  ]
}

TypeScript/REST HTTP
> The REST request is shown in the cURL example. The OpenAI TypeScript SDK with custom baseURL is the canonical TypeScript interface.

6. SDK Information
Field | Value
Official SDK Name | OpenAI SDK with custom baseURL (no separate xAI SDK).
Installation Command (Python) | pip install openai
Installation Command (JS) | npm install openai
SDK Version | openai-python ≥1.50; openai-node ≥4.70
JavaScript SDK | Yes (via openai npm).
Python SDK | Yes (via openai PyPI).
REST Support | Yes (HTTPS POST to api.x.ai/v1/images/generations).
Async Support | No (synchronous only).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | data[].url, data[].revised_prompt (always null for Grok), created.
URLs | Yes (xAI-hosted CDN URL).
Base64 support | Yes (response_format=b64_json).
Metadata | created.
Seeds | Not officially documented (model is not seed-deterministic).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via xAI content moderation; blocked requests return an error.

8. Pricing
xAI pricing is published at docs.x.ai/docs/models. As of the latest published rates: grok-2-image is $0.07 per image at 1024x1024. Volume discounts are not yet published.

9. Changelog
Category | Detail
Latest features | grok-2-image-1212 introduced (Aurora); OpenAI-compatible API surface.
Breaking changes | None documented.
Deprecated parameters | None.
New parameters | None beyond OpenAI-compatible schema.

10. Official Documentation
Resource | URL
XAI image generation guide | https://docs.x.ai/docs/guides/image-generations
xAI API reference | https://docs.x.ai/docs/api-reference
XAI models list | https://docs.x.ai/docs/models
xAI blog (Grok image launch) | https://x.ai/blog/grok-image-generation
Pricing | https://docs.x.ai/docs/models

Best Used For
Grok Image is the recommended choice when the workflow is already using the xAI Grok chat API and wants a unified SDK experience, or when Aurora's specific aesthetic (documented at x.ai/blog/grok-image-generation) is preferred.

Known Limitations
• Text-to-image only; no image-to-image, inpainting, or editing.
• No native negative prompt.
• Aspect ratio is not user-configurable (1:1 only).
• No seed support documented.

Kling AI - Image 01, Image 03, Image V3
Kling AI (Kuaishou) exposes three image-generation model variants via their developer API: Image O1 (reasoning-optimized), Image O3 (next-generation reasoning), and Image V3 (standard production model). All three are documented at docs.qingque.cn and hosted on fal.ai under fal-ai/kling/image-*.

Kling Image 01
1. Basic Information
Field | Value
Company | Kuaishou (Kling AI)
Model Name | Kling Image 01 (kling-image-01)
Latest Version | kling-image-o1
Release Date | 2025 (announced with Kling O1 reasoning model).
Official Docs URL | https://docs.qingque.cn/d/home/eZQDH40hsK4FN6XFWwFh1JzNw
fal.ai Endpoint | fal-ai/kling/image-o1
Official API Endpoint | POST https://api.klingai.com/v1/images/generations

Supported Tasks
Task | Supported
Text-to-Image | Yes
Image-to-Image | No.
Inpainting | No.
Outpainting | No.
Style Transfer | No.
Image Editing | No.
Multi-image Generation | No.

2. Input Schema (fal.ai)
Parameter | Type | Required | Default | Enum | Description | Min | Max
prompt | string | Yes | | | Text description of desired image. Kling O1 supports long reasoning prompts. | | 4000 chars
image_size | string/object | No | "landscape_4_3" | square_hd, square, portrait_4_3, portrait_16_9, landscape_4_3, landscape_16_9 | Output dimensions. | |
num_inference_steps | integer | No | 30 | 1-50 | Number of denoising steps. | | 50
num_images | integer | No | 1 | 1-4 | Number of images to generate. | 1 | 4
seed | integer | No | random | 0-4294967295 | Random seed. | 0 | 4294967295
guidance_scale | number | No | 7.5 | 0-20 | CFG scale. | 0 | 20
negative_prompt | string | No | | | What to exclude from the image. | | 500 chars
enable_safety_checker | boolean | No | true | | NSFW safety checker. | |

3. Prompt Rules
Rule | Value
Prompt format | Natural language text. O1 is optimized for long, complex prompts that benefit from chain-of-thought reasoning.
Prompt syntax | Free-form; up to 4000 characters.
Maximum prompt length | 4000 characters.
Prompt token limit | Not officially documented.
Negative prompt support | Yes (negative_prompt parameter).
System prompt support | No.
JSON prompt support | No.
Natural language prompt support | Yes.
Structured prompt support | No.
Markdown support | No.

4. Image Limits
Limit | Value
Maximum input images | 0 (text-to-image only on Kling O1).
Minimum input images | 0.
Maximum generated images | 4 per request (num_images).
Maximum resolution | 1536x864 (largest preset).
Minimum resolution | 512x512 (typical).
Supported aspect ratios | 1:1, 4:3, 3:4, 16:9, 9:16.
Supported image formats | Output: PNG (default), JPEG.
Maximum upload size | N/A (no input images).
Maximum output size | ~8 MB per image.

5. API Examples
CURL (fal.ai REST)
curl -X POST "https://fal.run/fal-ai/kling/image-o1"   -H "Authorization: Key $FAL_KEY"   -H "Content-Type: application/json"   -d '{
    "prompt": "A surreal dreamscape where giant clocks float in a violet sky above a desert of golden sand",
    "image_size": "landscape_16_9",
    "num_inference_steps": 40,
    "guidance_scale": 7.5
  }'

JavaScript (fal.ai)
import { fal } from "@fal-ai/client";
const result = await fal.subscribe("fal-ai/kling/image-o1", {
  input: {
    prompt: "A surreal dreamscape where giant clocks float in a violet sky",
    image_size: "landscape_16_9",
    num_inference_steps: 40
  }
});
console.log(result.data.images[0].url);

Python (fal-client)
import fal_client
result = fal_client.subscribe(
    "fal-ai/kling/image-o1",
    arguments={
        "prompt": "A surreal dreamscape where giant clocks float in a violet sky",
        "image_size": "landscape_16_9",
    },
)
print(result["images"][0]["url"])

JSON Response
{
  "images": [
    {
      "url": "https://fal.media/files/kling-o1-xyz.jpg",
      "width": 1536,
      "height": 864,
      "content_type": "image/jpeg"
    }
  ],
  "timings": { "inference": 8.4 },
  "seed": 1234567890
}

TypeScript/REST HTTP (Kling native)
> Kling publishes a native REST API at api.klingai.com documented at docs.qingque.cn. The fal.ai examples above are the canonical hosted path. No separate TypeScript SDK is officially published by Kling.

6. SDK Information
Field | Value
Official SDK Name | No first-party Kling SDK; REST + fal.ai.
Installation Command (Python, fal) | pip install fal-client
Installation Command (JS, fal) | npm install --save @fal-ai/client
SDK Version | fal-client ≥0.5; @fal-ai/client ≥1.0.
JavaScript SDK | Via fal.ai.
Python SDK | Via fal.ai or direct REST.
REST Support | Yes (HTTPS POST to api.klingai.com/v1/images/generations).
Async Support | Yes (via fal.ai queue).
Streaming Support | No.

7. Output Format
Field | Value
Output MIME types | image/png (default), image/jpeg.
Returned fields | images[].url, images[].width, images[].height, images[].content_type, timings.inference, seed.
URLs | Yes (fal.ai CDN URL; valid for ~24 hours).
Base64 support | Yes via fal.ai (output_format=base64).
Metadata | timings, seed.
Seeds | Yes (seed parameter, integer).
Safety scores | Not returned; content is filtered before return.
NSFW flags | Filtered via Kling content moderation; blocked requests return an error.

8. Pricing
Kling pricing is published at klingai.com/pricing. As of the latest published rates: Kling Image O1 is ~$0.10/image at 1024x1024. O1 is the most expensive Kling variant due to the reasoning overhead. On fal.ai: ~$0.015/MP.

9. Changelog
Category | Detail
Latest features | Kling Image O1 introduced: reasoning-optimized for long, complex prompts; improved prompt adherence for compositional prompts.
Breaking changes | None documented.
Deprecated parameters | None.
New parameters | None beyond standard Kling schema.

10. Official Documentation
Resource | URL
Kling developer docs | https://docs.qingque.cn/d/home/eZQDH40hsK4FN6XFWwFh1JzNw
fal.ai model page (o1) | https://fal.ai/models/fal-ai/kling/image-o1
Kling pricing | https://klingai.com/pricing

Best Used For
Kling Image O1 is the recommended Kling variant for complex, multi-subject compositional prompts where the extra reasoning time produces visibly better prompt adherence. Not recommended for latency-sensitive workflows.

Known Limitations
• Text-to-image only; no image-to-image, inpainting, or editing.
• Higher latency than V3 (typical 5-10s vs. 2-4s).
• Higher per-image cost than V3.
• No multi-image reference input.

Kling Image O3
Kling Image O3 is the next-generation reasoning model from Kling. Schema is identical to O1 above; differences are improved reasoning and higher per-image cost.

Differences from O1
• Model id: kling-image-o3 (vs. kling-image-o1).
• Reasoning: O3 introduces deeper chain-of-thought (typical 2x the inference steps of O1).
• Quality: O3 is recommended for the most complex compositional prompts.
• Pricing: ~$0.15/image (vs. $0.10 for O1).

Other Sections
See Kling Image O1 above for schema, prompt rules, image limits, API examples, SDK, output format, and docs links. The only differences are the model id and the pricing/latency profile.

Kling Image V3
Kling Image V3 is the standard production variant optimized for speed and cost rather than reasoning depth. Schema is identical to O1/O3 above; differences are below.

Differences from O1/O3
• Model id: kling-image-v3.
• Reasoning: V3 does NOT use chain-of-thought; it is a standard feed-forward diffusion model.
• Latency: V3 is ~3x faster than O1 (typical 2-4s vs. 5-10s).
• Pricing: ~$0.04/image (cheapest Kling variant). On fal.ai: ~$0.005/MP.

Other Sections
See Kling Image O1 above for schema, prompt rules, image limits, API examples, SDK, output format, and docs links. The only differences are the model id and the pricing/latency profile.
