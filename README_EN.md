# crop_tool

**A batch cropping and perspective-correction tool designed for one specific pain point: a large folder of photos where every image needs a different crop region.**

You have hundreds of recaptured photos — certificates, award plaques, ID cards, whiteboards, projector slides, invoices, exam papers — each taken at a different angle and position, and you need to extract and straighten a specific region from every single one. Generic tools either cannot do this at all, or they make the process painfully slow. crop_tool is built for exactly this workflow: **per-image precise framing, human-in-the-loop guidance, machine-assisted precision, and a keyboard-driven workflow that stays smooth even for hundreds of images.**

---

## The Problem It Solves

Real-world scenario: you need to crop, straighten, and archive a large batch of recaptured photos, but each image requires a **different, manually specified region**. Existing tools fall short:

| Tool Type | Typical Examples | Limitation |
|-----------|------------------|------------|
| Scanning Apps | **CamScanner**, Microsoft Lens, Adobe Scan | Fully automatic edge detection often fails on arbitrary user-defined regions and struggles with large batches |
| General Photo Editors | Meitu, WPS Image Tools | Only uniform cropping or one-by-one manual cropping; extremely tedious for hundreds of images |
| Batch Cropping Scripts | Various CLI tools | Only work with **fixed camera position**; useless when every image has a different region |

crop_tool takes a deliberate stance: **we do not chase full automation**, because fully automatic tools are inherently unreliable for "user-defined regions". Instead, we maximize the efficiency of **manual per-image framing** — you stay in control, and the tool makes every click fast and accurate.

## Use Cases

- **Certificates / Awards / ID Cards**: each photo is shot from a different angle and needs individual correction
- **Conference / Event Photos**: projector slides, whiteboards, and presentation screens
- **Documents / Exams / Invoices**: remove backgrounds, straighten, and compile into collections
- Any task where a **batch of photos each needs its own manually specified crop region**

## Key Advantages

1. **Per-image precise framing, not one-box-fits-all** — every image can have its own independent crop region, which batch tools cannot do.
2. **Semi-automatic helpers reduce manual effort** (all togglable, they only suggest a starting point):
   - **Snap-to-edge (Magnet)**: automatically snap clicks to nearby real corners, even if your click is slightly off
   - **Auto-quad (D key)**: one-click border detection to place four corners, then fine-tune by dragging
   - **Carry over last region**: when enabled, the next image automatically inherits the previous region as a starting point
   - **Apply to folder (A key)**: after marking one image, apply the same region to other same-position images in the folder
3. **Keyboard-driven zero-friction workflow**: pressing `Enter` saves and jumps to the next unprocessed image; reopening the app **restores progress** automatically (processed images are marked).
4. **True-ratio perspective correction**: output preserves the real aspect ratio of the selected quadrilateral instead of forcing it to a fixed size.
5. **Smooth even with hundreds of images**: on-demand loading and background thumbnails keep navigation fast.
6. **All-in-one**: cropping + leveling + export to PPT / PDF / Word in one tool.
7. **Portable**: Windows users can download the zip, extract, and run — no Python installation required.

---

## Download (Portable)

No Python installation is required for end users:

1. Go to the [Releases page](https://github.com/Naraku215/crop_tool/releases)
2. Download the latest `crop_tool-v2.6.zip`
3. Extract to any directory
4. Double-click `crop_tool.exe`
5. Click **Select Image Folder** and choose the folder containing your images

## Workflow

1. Click **Select Image Folder** to load images (thumbnail list on the left)
2. Click a thumbnail to select the image to process
3. Choose a mode: **Crop [1]** (four-point perspective) or **Level [2]** (two-point leveling)
4. Mark points on the canvas following the top instruction bar (crop: top-left → top-right → bottom-right → bottom-left)
5. Press `Enter` to save; the app automatically jumps to the next unprocessed image, and the result appears in the **Processed Result** panel
6. After finishing, export to **PPT / PDF / Word** with one click

Processed images are saved in a `crop_tool_已处理/` subdirectory under the selected folder, preserving the original folder structure. Files are written as soon as you press `Enter`. On exit, you can choose **Save and Exit** or **Discard and Exit** (deletes only the files produced in this session).

### Helper Toggles

| Toggle | Default | Function |
|--------|---------|----------|
| Snap-to-edge | On | Automatically snap crop points to nearby real edges |
| Carry over last region | Off | Automatically inherit the previous image's region when switching images |

### Shortcuts

| Key | Function | Key | Function |
|-----|----------|-----|----------|
| `Enter` | Save and jump to next unprocessed | `S` | Skip current |
| `B` | Previous image | `N` | Skip entire folder |
| `R` | Redraw (clear markers) | `A` | Apply to remaining images in folder |
| `P` | Paste last markers | `D` | Auto-detect border |
| `1` / `2` | Crop / Level mode | `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| Arrow keys | Fine-tune selected point (Shift = 10 px) | Scroll / `+` / `-` / `0` | Zoom / reset |
| Space + drag / middle-drag | Pan canvas | `Esc` / `Q` | Return to original / Quit |

---

## Developer Setup

```bash
git clone https://github.com/Naraku215/crop_tool.git
cd crop_tool

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
python gui.py                 # Launch GUI (recommended)
```

CLI helper tools (format conversion, folder reconciliation, export):

```bash
python main.py
```

## Directory Structure

```
crop_tool/
├── gui.py             # GUI entry point (main)
├── main.py            # CLI entry point
├── crop_tool.py       # Four-point perspective cropping + snap + auto-quad
├── level.py           # Two-point leveling
├── export.py          # Unified PPT / PDF / Word export
├── trans_png.py       # Format conversion (any format -> PNG)
├── check_folders.py   # Folder reconciliation
├── utils.py           # Shared utilities
├── config.py          # Central configuration
├── build.bat          # PyInstaller build script
├── requirements.txt   # Python dependencies
├── LICENSE            # MIT License
└── README.md
```

## Module Descriptions

### Perspective Crop (`crop_tool.py`)

Click four corners (top-left → top-right → bottom-right → bottom-left) to perform perspective correction. By default, output size is computed from the real side lengths of the selected quadrilateral, preserving the original ratio without stretching. Includes `snap_corner()` (magnetic snap) and `detect_quad()` (automatic quadrilateral detection as a starting point).

### Level (`level.py`)

Click two points on a line that should be horizontal. The image is automatically rotated to straighten that line and crop away the resulting black borders, with real-time preview.

### Export (`export.py`)

| Format | Description |
|--------|-------------|
| PPT | 16:9 widescreen, each image placed centered and letterboxed by its own aspect ratio (no stretching/cropping), one `.pptx` per subfolder |
| PDF | Generated natively via Pillow, one `.pdf` per subfolder |
| Word | Landscape layout, one image per page, one `.docx` per subfolder |

Standalone usage:

```bash
python export.py <input_dir> <output_dir> [ppt|pdf|word|all]
```

## Configuration (`config.py`)

| Parameter | Description | Default |
|-----------|-------------|---------|
| `TARGET_SIZE` | Fixed target crop size (used only when explicitly requested) | `(1920, 1080)` |
| `SLIDE_WIDTH_INCH` / `SLIDE_HEIGHT_INCH` | PPT slide size (16:9) | `13.333` / `7.5` |
| `THUMBNAIL_SIZE` | Thumbnail size | `(120, 90)` |
| `IMAGE_EXTS` | Supported image formats | `.png .jpg .jpeg .bmp .tiff .tif .heic .heif` |

## Build & Release

```bat
build.bat
```

After building, `dist/` contains:
- `crop_tool/` — executable folder (`crop_tool.exe`)
- `crop_tool-v2.6.zip` — release archive for GitHub Releases

## Tech Stack

- **OpenCV** — image processing, perspective transform, rotation
- **Pillow + pillow-heif** — image I/O, HEIC/HEIF support, PDF generation
- **python-pptx** — PPT generation
- **python-docx** — Word generation
- **NumPy** — numerical computation
- **tkinter** — GUI

## License

[MIT License](LICENSE)
