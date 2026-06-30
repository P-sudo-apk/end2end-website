import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


APP_TITLE = "StencilForge v1.0"


class StencilForgeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1200x850")
        self.root.configure(bg="#1e1e1e")

        self.base_dir = Path(__file__).resolve().parent
        self.exports_dir = self.base_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)

        self.original_bgr = None
        self.gray = None
        self.blurred = None

        self.base_mask = None
        self.shadow_mask = None
        self.light_mask = None
        self.combined_preview = None

        self.current_view = "combined"
        self.preview_photo = None
        self.current_image_path = None

        self.build_ui()
        self.load_default_image_if_available()

    def build_ui(self):
        # Main layout
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        left_panel = tk.Frame(main_frame, bg="#2a2a2a", width=320)
        left_panel.pack(side="left", fill="y", padx=(0, 12))
        left_panel.pack_propagate(False)

        right_panel = tk.Frame(main_frame, bg="#111111")
        right_panel.pack(side="right", fill="both", expand=True)

        # Header
        header = tk.Label(
            left_panel,
            text="StencilForge",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#2a2a2a"
        )
        header.pack(pady=(14, 4))

        subheader = tk.Label(
            left_panel,
            text="Turn images into printable stencil layers",
            font=("Arial", 10),
            fg="#bbbbbb",
            bg="#2a2a2a"
        )
        subheader.pack(pady=(0, 14))

        # Upload button
        upload_btn = tk.Button(
            left_panel,
            text="Upload Image",
            command=self.load_image,
            font=("Arial", 11, "bold"),
            bg="#4c8bf5",
            fg="white",
            activebackground="#3b73d1",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=8
        )
        upload_btn.pack(fill="x", padx=14, pady=(0, 14))

        # Current file label
        self.file_label = tk.Label(
            left_panel,
            text="No image loaded",
            font=("Arial", 9),
            fg="#cccccc",
            bg="#2a2a2a",
            wraplength=280,
            justify="left"
        )
        self.file_label.pack(fill="x", padx=14, pady=(0, 14))

        # Sliders
        self.base_var = tk.IntVar(value=55)
        self.shadow_var = tk.IntVar(value=40)
        self.light_var = tk.IntVar(value=40)
        self.cleanup_var = tk.IntVar(value=5)

        self.make_slider(left_panel, "Base Threshold", self.base_var, 0, 255)
        self.make_slider(left_panel, "Shadow Offset", self.shadow_var, 0, 255)
        self.make_slider(left_panel, "Light Offset", self.light_var, 0, 255)
        self.make_slider(left_panel, "Cleanup", self.cleanup_var, 1, 15)

        # View buttons
        view_label = tk.Label(
            left_panel,
            text="Preview View",
            font=("Arial", 12, "bold"),
            fg="white",
            bg="#2a2a2a"
        )
        view_label.pack(anchor="w", padx=14, pady=(16, 8))

        btn_frame = tk.Frame(left_panel, bg="#2a2a2a")
        btn_frame.pack(fill="x", padx=14)

        self.make_view_button(btn_frame, "Base", "base", 0, 0)
        self.make_view_button(btn_frame, "Shadow", "shadow", 0, 1)
        self.make_view_button(btn_frame, "Light", "light", 1, 0)
        self.make_view_button(btn_frame, "Combined", "combined", 1, 1)

        # Export button
        export_btn = tk.Button(
            left_panel,
            text="Export Layers",
            command=self.export_layers,
            font=("Arial", 11, "bold"),
            bg="#2ea043",
            fg="white",
            activebackground="#248636",
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=10
        )
        export_btn.pack(fill="x", padx=14, pady=(20, 10))

        # Info area
        self.info_label = tk.Label(
            left_panel,
            text="Load an image to begin.",
            font=("Arial", 9),
            fg="#dddddd",
            bg="#2a2a2a",
            justify="left",
            anchor="nw"
        )
        self.info_label.pack(fill="x", padx=14, pady=(6, 10))

        # Preview area
        preview_header = tk.Label(
            right_panel,
            text="Preview",
            font=("Arial", 16, "bold"),
            fg="white",
            bg="#111111"
        )
        preview_header.pack(anchor="w", padx=14, pady=(14, 8))

        self.preview_label = tk.Label(
            right_panel,
            bg="#000000",
            text="Upload an image to preview",
            fg="#888888",
            font=("Arial", 14),
            width=80,
            height=35
        )
        self.preview_label.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Trace slider changes
        for var in (self.base_var, self.shadow_var, self.light_var, self.cleanup_var):
            var.trace_add("write", self.on_slider_change)

    def make_slider(self, parent, text, variable, min_val, max_val):
        label = tk.Label(
            parent,
            text=text,
            font=("Arial", 11, "bold"),
            fg="white",
            bg="#2a2a2a"
        )
        label.pack(anchor="w", padx=14, pady=(8, 2))

        value_label = tk.Label(
            parent,
            textvariable=variable,
            font=("Arial", 9),
            fg="#bbbbbb",
            bg="#2a2a2a"
        )
        value_label.pack(anchor="w", padx=14, pady=(0, 2))

        scale = tk.Scale(
            parent,
            from_=min_val,
            to=max_val,
            orient="horizontal",
            variable=variable,
            bg="#2a2a2a",
            fg="white",
            troughcolor="#444444",
            highlightthickness=0,
            length=280
        )
        scale.pack(padx=14, pady=(0, 4))

    def make_view_button(self, parent, text, view_name, row, col):
        btn = tk.Button(
            parent,
            text=text,
            command=lambda: self.set_view(view_name),
            font=("Arial", 10, "bold"),
            bg="#444444",
            fg="white",
            activebackground="#666666",
            activeforeground="white",
            relief="flat",
            width=12,
            pady=6
        )
        btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)

    def load_default_image_if_available(self):
        default_path = self.base_dir / "test.png"
        if default_path.exists():
            self.open_image(default_path)

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.open_image(Path(file_path))

    def open_image(self, image_path: Path):
        image = cv2.imread(str(image_path))
        if image is None:
            messagebox.showerror("Error", f"Could not open image:\n{image_path}")
            return

        self.current_image_path = image_path
        self.original_bgr = image
        self.gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        self.blurred = cv2.GaussianBlur(self.gray, (7, 7), 0)

        self.file_label.config(text=f"Loaded:\n{image_path.name}")
        self.process_image()

    def on_slider_change(self, *args):
        if self.blurred is not None:
            self.process_image()

    def process_image(self):
        base_val = self.base_var.get()
        shadow_offset = self.shadow_var.get()
        light_offset = self.light_var.get()
        cleanup_val = self.cleanup_var.get()

        base_cutoff = base_val
        shadow_cutoff = min(base_cutoff + shadow_offset + 1, 255)
        light_cutoff = min(shadow_cutoff + light_offset + 1, 255)

        self.base_mask = np.where(self.blurred < base_cutoff, 0, 255).astype(np.uint8)

        self.shadow_mask = np.where(
            (self.blurred >= base_cutoff) & (self.blurred < shadow_cutoff),
            0,
            255
        ).astype(np.uint8)

        self.light_mask = np.where(
            (self.blurred >= shadow_cutoff) & (self.blurred < light_cutoff),
            0,
            255
        ).astype(np.uint8)

        kernel_size = max(1, cleanup_val)
        kernel = np.ones((kernel_size, kernel_size), np.uint8)

        self.base_mask = cv2.morphologyEx(self.base_mask, cv2.MORPH_CLOSE, kernel)
        self.shadow_mask = cv2.morphologyEx(self.shadow_mask, cv2.MORPH_CLOSE, kernel)
        self.light_mask = cv2.morphologyEx(self.light_mask, cv2.MORPH_CLOSE, kernel)

        self.combined_preview = self.build_combined_preview(
            self.base_mask,
            self.shadow_mask,
            self.light_mask
        )

        self.info_label.config(
            text=(
                f"Base cutoff: {base_cutoff}\n"
                f"Shadow offset: {shadow_offset}  |  cutoff: {shadow_cutoff}\n"
                f"Light offset: {light_offset}  |  cutoff: {light_cutoff}\n"
                f"Cleanup: {cleanup_val}\n"
                f"View: {self.current_view.title()}"
            )
        )

        self.update_preview()

    def set_view(self, view_name: str):
        self.current_view = view_name
        if self.blurred is not None:
            self.update_preview()

    def update_preview(self):
        if self.base_mask is None:
            return

        if self.current_view == "base":
            preview = self.base_mask
        elif self.current_view == "shadow":
            preview = self.shadow_mask
        elif self.current_view == "light":
            preview = self.light_mask
        else:
            preview = self.combined_preview

        preview_bgr = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)

        # draw green preview registration marks so they are always visible on screen
        preview_bgr = self.draw_preview_marks(preview_bgr)

        preview_rgb = cv2.cvtColor(preview_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(preview_rgb)

        max_w = 820
        max_h = 720
        pil_image.thumbnail((max_w, max_h))

        self.preview_photo = ImageTk.PhotoImage(pil_image)
        self.preview_label.config(image=self.preview_photo, text="")

    def export_layers(self):
        if self.base_mask is None:
            messagebox.showwarning("No image", "Load an image first.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_set_dir = self.exports_dir / f"stencil_set_{timestamp}"
        export_set_dir.mkdir(parents=True, exist_ok=True)

        base_cutoff = self.base_var.get()
        shadow_offset = self.shadow_var.get()
        light_offset = self.light_var.get()

        shadow_cutoff = min(base_cutoff + shadow_offset + 1, 255)
        light_cutoff = min(shadow_cutoff + light_offset + 1, 255)

        base_name = f"02_base_b{base_cutoff}.png"
        shadow_name = f"03_shadow_b{base_cutoff}_s{shadow_offset}_c{shadow_cutoff}.png"
        light_name = f"04_light_s{shadow_offset}_l{light_offset}_c{light_cutoff}.png"
        combined_name = f"01_combined_b{base_cutoff}_s{shadow_offset}_l{light_offset}.png"

        self.save_image(export_set_dir / base_name, self.add_padding_and_marks(self.base_mask))
        self.save_image(export_set_dir / shadow_name, self.add_padding_and_marks(self.shadow_mask))
        self.save_image(export_set_dir / light_name, self.add_padding_and_marks(self.light_mask))
        self.save_image(export_set_dir / combined_name, self.add_padding_and_marks(self.combined_preview))

        messagebox.showinfo(
            "Export complete",
            f"Saved stencil set to:\n{export_set_dir}"
        )

    @staticmethod
    def save_image(path: Path, image: np.ndarray) -> None:
        ok = cv2.imwrite(str(path), image)
        if not ok:
            raise RuntimeError(f"Failed to save image: {path}")

    @staticmethod
    def build_combined_preview(base_mask, shadow_mask, light_mask) -> np.ndarray:
        combined = np.full(base_mask.shape, 255, dtype=np.uint8)
        combined[base_mask == 0] = 0
        combined[shadow_mask == 0] = 90
        combined[light_mask == 0] = 180
        return combined

    @staticmethod
    def add_padding_and_marks(mask: np.ndarray) -> np.ndarray:
        pad = 50
        h, w = mask.shape

        canvas = np.ones((h + pad * 2, w + pad * 2), dtype=np.uint8) * 255
        canvas[pad:pad + h, pad:pad + w] = mask

        mark_size = 20
        thickness = 2
        margin = 15

        # top left
        cv2.line(canvas, (margin, margin), (margin + mark_size, margin), 0, thickness)
        cv2.line(canvas, (margin, margin), (margin, margin + mark_size), 0, thickness)

        # top right
        cv2.line(
            canvas,
            (canvas.shape[1] - margin, margin),
            (canvas.shape[1] - margin - mark_size, margin),
            0,
            thickness
        )
        cv2.line(
            canvas,
            (canvas.shape[1] - margin, margin),
            (canvas.shape[1] - margin, margin + mark_size),
            0,
            thickness
        )

        # bottom left
        cv2.line(
            canvas,
            (margin, canvas.shape[0] - margin),
            (margin + mark_size, canvas.shape[0] - margin),
            0,
            thickness
        )
        cv2.line(
            canvas,
            (margin, canvas.shape[0] - margin),
            (margin, canvas.shape[0] - margin - mark_size),
            0,
            thickness
        )

        # bottom right
        cv2.line(
            canvas,
            (canvas.shape[1] - margin, canvas.shape[0] - margin),
            (canvas.shape[1] - margin - mark_size, canvas.shape[0] - margin),
            0,
            thickness
        )
        cv2.line(
            canvas,
            (canvas.shape[1] - margin, canvas.shape[0] - margin),
            (canvas.shape[1] - margin, canvas.shape[0] - margin - mark_size),
            0,
            thickness
        )

        return canvas

    @staticmethod
    def draw_preview_marks(img: np.ndarray) -> np.ndarray:
        marked = img.copy()
        h, w = marked.shape[:2]
        mark_size = 18
        thickness = 2
        color = (0, 255, 0)
        margin = 10

        # top left
        cv2.line(marked, (margin, margin), (margin + mark_size, margin), color, thickness)
        cv2.line(marked, (margin, margin), (margin, margin + mark_size), color, thickness)

        # top right
        cv2.line(marked, (w - margin, margin), (w - margin - mark_size, margin), color, thickness)
        cv2.line(marked, (w - margin, margin), (w - margin, margin + mark_size), color, thickness)

        # bottom left
        cv2.line(marked, (margin, h - margin), (margin + mark_size, h - margin), color, thickness)
        cv2.line(marked, (margin, h - margin), (margin, h - margin - mark_size), color, thickness)

        # bottom right
        cv2.line(marked, (w - margin, h - margin), (w - margin - mark_size, h - margin), color, thickness)
        cv2.line(marked, (w - margin, h - margin), (w - margin, h - margin - mark_size), color, thickness)

        return marked


if __name__ == "__main__":
    root = tk.Tk()
    app = StencilForgeApp(root)
    root.mainloop()