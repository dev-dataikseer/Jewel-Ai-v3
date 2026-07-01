# Database-Driven Prompt Management

This plan completely decouples the prompt system from the `.txt` files during normal operation, ensuring the database is the sole source of truth and allowing users to edit the raw `.txt` prompt block directly in the UI.

## Proposed Changes

### 1. Remove Auto-Sync and File Watching
- **[MODIFY] `backend/seeds/run_seeds.py`**: Completely remove the call to `import_prompt_txt_library`. The application will no longer read `.txt` files on startup or watch them for changes.

### 2. Update Import Logic for "Fetch As Is"
- **[MODIFY] `backend/seeds/prompt_txt_parser.py`**: Rewrite the parser so it no longer splits the `MASTER PROMPT` or `CHILD PROMPTS` into segmented JSON fields (like `system_role`, `camera_settings`). Instead, it will fetch the entire text block *as it is* (preserving headers like `ROLE:`).
- **[MODIFY] `backend/seeds/prompt_txt_import.py`**: Update the import logic to perform a **one-time migration only**. It will check if the database already contains prompts; if so, it skips inserting to prevent overwriting. It will save the raw text into `prompt_text` and map it to a simplified layer structure for the composer.

### 3. Update API to Save UI Edits
- **[MODIFY] `backend/app/api/routers/prompts.py`**: When the Admin UI sends an updated `prompt_text`, the API will save it in the database and automatically structure the internal JSON `layers` as a single `text` block followed by the `subject_insert` and `variant_insert` points. This keeps the backend `composer.py` working perfectly while allowing the UI to edit a single text block.

### 4. Update Frontend UI
- **[MODIFY] `frontend/src/lib/promptUtils.ts`**: Update `masterToSingleText` to simply use `template.prompt_text` directly instead of re-assembling legacy fields, ensuring the UI always displays the raw, un-split text.

## User Review Required

> [!IMPORTANT]
> Since we are moving to a DB-only system, the `.txt` files will only be used **once** for the initial migration. Any future changes to prompts must be done through the Admin UI. If you manually edit the `.txt` files later, the system will ignore them.

> [!TIP]
> The text you edit in the UI will now exactly match the raw `.txt` file contents, including the `ROLE:`, `CAMERA:`, etc. markers inside the text box. The backend will use this exact block of text.

## Verification Plan
1. Delete the existing DB records (or reset the DB) to test the one-time migration.
2. Run the migration script and verify that the UI shows the full text block exactly as it appears in the `.txt` files.
3. Edit the prompt in the UI, save it, and verify a new version is created in the DB without overwriting.
4. Restart the server and verify that the `.txt` files do not overwrite the DB.
5. Generate a test prompt to ensure the composer correctly appends the Subject and Variant text to the raw Master Prompt.
