# Uellow Importer — Chrome Extension

Import AliExpress products into **Uellow World** with one click, straight from
aliexpress.com. Works on product pages, search results, category and store
pages. **Import** (as a source listing) or **Import & Publish** (live in the app).

## Install (unpacked)
1. In Uellow: **Uellow World ▸ Settings ▸ Orders ▸ Chrome Extension API Key** →
   click **Generate Key** and copy it.
2. Download & unzip this extension (or use the folder as-is).
3. Chrome → `chrome://extensions` → enable **Developer mode** →
   **Load unpacked** → select this folder.
4. Click the Uellow icon in the toolbar → set:
   - **Server URL**: `https://world.uellow.com`
   - **API Key**: the key you generated
   - optionally tick **Publish immediately**
   - click **Test** → should say *Connected ✓*.

## Use
- **On a product page**: a panel bottom-right shows **Import** / **Import & Publish**.
- **On search / category / store pages**: every product tile gets a small
  **＋ Import** / **⇪ Publish** button, plus a panel to **Import (whole) page**.
- A green **✓** marks products already imported; a **★** marks published ones.

Large scrapes are capped per click (Settings ▸ *Extension Max Products / Import*)
and every safety rule (dedup, flash-deal skip, auto-category) still applies.
