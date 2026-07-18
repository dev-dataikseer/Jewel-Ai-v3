/** Cross-session theme + logo brand kit (localStorage). */

export type BrandKit = {
  themeAssetId?: string | null;
  themeUrl?: string | null;
  themeName?: string | null;
  themePreview?: string | null;
  logoAssetId?: string | null;
  logoUrl?: string | null;
  logoName?: string | null;
  logoPreview?: string | null;
  updatedAt?: string;
};

const KEY = "jewel:brand-kit:v1";

export function loadBrandKit(): BrandKit | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as BrandKit;
  } catch {
    return null;
  }
}

export function saveBrandKit(kit: BrandKit) {
  try {
    localStorage.setItem(
      KEY,
      JSON.stringify({ ...kit, updatedAt: new Date().toISOString() }),
    );
  } catch {
    /* quota / private mode */
  }
}

export function clearBrandKit() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export function patchBrandKit(partial: Partial<BrandKit>) {
  const prev = loadBrandKit() || {};
  saveBrandKit({ ...prev, ...partial });
}
