from __future__ import annotations

import io
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2
import fitz
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageTk


MAX_DIMENSION = 16000
PDF_DPI = 600
SVG_MIN_DIMENSION = 12000
COMPARISON_THRESHOLD = 220
TOLERANCE_PIXELS = 2

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".tif",
    ".tiff",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
}


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def resize_if_needed(
    image: np.ndarray,
    max_dimension: int = MAX_DIMENSION,
) -> np.ndarray:
    height, width = image.shape[:2]
    largest_dimension = max(width, height)

    if largest_dimension <= max_dimension:
        return image

    scale = max_dimension / largest_dimension

    return cv2.resize(
        image,
        (
            max(1, round(width * scale)),
            max(1, round(height * scale)),
        ),
        interpolation=cv2.INTER_LANCZOS4,
    )


def pixmap_to_bgr(
    pixmap: fitz.Pixmap,
) -> np.ndarray:
    image = np.frombuffer(
        pixmap.samples,
        dtype=np.uint8,
    ).reshape(
        pixmap.height,
        pixmap.width,
        pixmap.n,
    )

    if pixmap.n == 4:
        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGBA2BGR,
        )

    elif pixmap.n == 3:
        image = cv2.cvtColor(
            image,
            cv2.COLOR_RGB2BGR,
        )

    elif pixmap.n == 1:
        image = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGR,
        )

    else:
        raise ValueError(
            f"Quantidade inesperada de canais: {pixmap.n}"
        )

    return image.copy()


def load_pdf(
    path: Path,
    page_number: int = 0,
    dpi: int = PDF_DPI,
    max_dimension: int = MAX_DIMENSION,
) -> np.ndarray:
    document = fitz.open(path)

    try:
        if not 0 <= page_number < len(document):
            raise ValueError(
                f"PDF possui {len(document)} página(s)."
            )

        page = document[page_number]
        scale = dpi / 72.0

        expected_width = page.rect.width * scale
        expected_height = page.rect.height * scale

        if max(expected_width, expected_height) > max_dimension:
            scale *= (
                max_dimension
                / max(expected_width, expected_height)
            )

        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            alpha=False,
            colorspace=fitz.csRGB,
        )

        return pixmap_to_bgr(pixmap)

    finally:
        document.close()


def load_tiff(
    path: Path,
    page_number: int = 0,
    max_dimension: int = MAX_DIMENSION,
) -> np.ndarray:
    document = fitz.open(path)

    try:
        if not 0 <= page_number < len(document):
            raise ValueError(
                f"TIFF possui {len(document)} página(s)."
            )

        page = document[page_number]

        if page.rect.width <= 0 or page.rect.height <= 0:
            raise ValueError(
                "TIFF possui dimensões inválidas."
            )

        scale = max_dimension / max(
            page.rect.width,
            page.rect.height,
        )

        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            alpha=False,
            colorspace=fitz.csRGB,
        )

        return pixmap_to_bgr(pixmap)

    finally:
        document.close()


def render_svg(
    svg_text: str,
    target_width: int | None = None,
    target_height: int | None = None,
) -> bytes:
    try:
        import resvg_py
    except ImportError as error:
        raise RuntimeError(
            "Instale resvg-py:\n"
            "py -m pip install resvg-py"
        ) from error

    arguments: dict[str, object] = {
        "svg_string": svg_text,
    }

    if target_width is not None:
        arguments["width"] = target_width

    if target_height is not None:
        arguments["height"] = target_height

    return resvg_py.svg_to_bytes(**arguments)


def load_svg(
    path: Path,
    max_dimension: int = MAX_DIMENSION,
    minimum_dimension: int = SVG_MIN_DIMENSION,
) -> np.ndarray:
    svg_text = path.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    initial_png = render_svg(svg_text)

    initial_image = Image.open(
        io.BytesIO(initial_png)
    ).convert("RGBA")

    initial_width, initial_height = initial_image.size

    if initial_width <= 0 or initial_height <= 0:
        raise ValueError(
            "SVG possui dimensões inválidas."
        )

    largest_dimension = max(
        initial_width,
        initial_height,
    )

    target_largest_dimension = min(
        max(
            largest_dimension,
            minimum_dimension,
        ),
        max_dimension,
    )

    scale = target_largest_dimension / largest_dimension

    target_width = max(
        1,
        round(initial_width * scale),
    )

    target_height = max(
        1,
        round(initial_height * scale),
    )

    try:
        if initial_width >= initial_height:
            png_data = render_svg(
                svg_text,
                target_width=target_width,
            )
        else:
            png_data = render_svg(
                svg_text,
                target_height=target_height,
            )

        svg_image = Image.open(
            io.BytesIO(png_data)
        ).convert("RGBA")

    except (TypeError, ValueError):
        svg_image = initial_image.resize(
            (
                target_width,
                target_height,
            ),
            Image.Resampling.LANCZOS,
        )

    background = Image.new(
        "RGB",
        svg_image.size,
        (255, 255, 255),
    )

    background.paste(
        svg_image,
        mask=svg_image.getchannel("A"),
    )

    return pil_to_bgr(background)


def load_raster(
    path: Path,
    max_dimension: int = MAX_DIMENSION,
) -> np.ndarray:
    image = cv2.imread(
        str(path),
        cv2.IMREAD_COLOR,
    )

    if image is None:
        raise ValueError(
            f"Não foi possível abrir: {path}"
        )

    return resize_if_needed(
        image,
        max_dimension,
    )


def load_drawing(
    file_path: str,
    page_number: int = 0,
) -> np.ndarray:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {path}"
        )

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato não suportado: {extension}"
        )

    print(f"Carregando: {path.name}")

    if extension == ".pdf":
        image = load_pdf(
            path,
            page_number,
        )

    elif extension in {".tif", ".tiff"}:
        image = load_tiff(
            path,
            page_number,
        )

    elif extension == ".svg":
        image = load_svg(path)

    else:
        image = load_raster(path)

    height, width = image.shape[:2]

    print(
        f"Resolução: {width} × {height} pixels"
    )

    return image


def select_reference_points(
    image: np.ndarray,
    title: str,
    number_of_points: int = 2,
) -> np.ndarray:
    rgb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB,
    )

    figure, axis = plt.subplots(
        figsize=(16, 10),
        dpi=120,
    )

    figure.canvas.manager.set_window_title(title)

    axis.imshow(
        rgb,
        interpolation="nearest",
        resample=False,
    )

    axis.set_title(title)

    axis.set_xlabel(
        "Zoom/pan: barra de ferramentas | "
        "Ctrl + clique esquerdo: selecionar | "
        "Botão direito: desfazer | "
        "Enter: confirmar | Esc: limpar"
    )

    axis.axis("off")

    selected_points: list[
        tuple[float, float]
    ] = []

    marker_artists = []
    text_artists = []

    confirmed = {
        "value": False,
    }

    def toolbar_is_active() -> bool:
        toolbar = figure.canvas.toolbar

        if toolbar is None:
            return False

        return bool(
            getattr(toolbar, "mode", "")
        )

    def redraw_markers() -> None:
        for artist in marker_artists:
            artist.remove()

        for artist in text_artists:
            artist.remove()

        marker_artists.clear()
        text_artists.clear()

        for index, point in enumerate(
            selected_points,
            start=1,
        ):
            marker = axis.plot(
                point[0],
                point[1],
                marker="x",
                markersize=14,
                markeredgewidth=2.5,
                linestyle="None",
            )[0]

            text = axis.text(
                point[0],
                point[1],
                f"  P{index}",
                fontsize=12,
                fontweight="bold",
            )

            marker_artists.append(marker)
            text_artists.append(text)

        figure.canvas.draw_idle()

    def on_click(event) -> None:
        if event.inaxes != axis:
            return

        if event.xdata is None or event.ydata is None:
            return

        if toolbar_is_active():
            return

        control_pressed = event.key in {
            "control",
            "ctrl",
        }

        if (
            event.button == 1
            and control_pressed
        ):
            if len(selected_points) >= number_of_points:
                return

            selected_points.append(
                (
                    float(event.xdata),
                    float(event.ydata),
                )
            )

            redraw_markers()

        elif (
            event.button == 3
            and selected_points
        ):
            selected_points.pop()
            redraw_markers()

    def on_key(event) -> None:
        if event.key == "enter":
            if len(selected_points) == number_of_points:
                confirmed["value"] = True
                plt.close(figure)

        elif event.key == "escape":
            selected_points.clear()
            redraw_markers()

    figure.canvas.mpl_connect(
        "button_press_event",
        on_click,
    )

    figure.canvas.mpl_connect(
        "key_press_event",
        on_key,
    )

    plt.tight_layout()
    plt.show()

    if not confirmed["value"]:
        raise RuntimeError(
            "Seleção cancelada."
        )

    return np.array(
        selected_points,
        dtype=np.float64,
    )


def calculate_similarity_transform(
    source_points: np.ndarray,
    target_points: np.ndarray,
) -> tuple[np.ndarray, float, float]:
    source_vector = (
        source_points[1]
        - source_points[0]
    )

    target_vector = (
        target_points[1]
        - target_points[0]
    )

    source_length = float(
        np.linalg.norm(source_vector)
    )

    target_length = float(
        np.linalg.norm(target_vector)
    )

    if source_length < 1e-9:
        raise ValueError(
            "Pontos do desenho novo são iguais."
        )

    if target_length < 1e-9:
        raise ValueError(
            "Pontos do desenho antigo são iguais."
        )

    scale = target_length / source_length

    source_angle = np.arctan2(
        source_vector[1],
        source_vector[0],
    )

    target_angle = np.arctan2(
        target_vector[1],
        target_vector[0],
    )

    angle_radians = (
        target_angle
        - source_angle
    )

    angle_degrees = float(
        np.degrees(angle_radians)
    )

    cosine = np.cos(angle_radians) * scale
    sine = np.sin(angle_radians) * scale

    matrix = np.array(
        [
            [
                cosine,
                -sine,
                0.0,
            ],
            [
                sine,
                cosine,
                0.0,
            ],
        ],
        dtype=np.float64,
    )

    transformed_first_point = (
        matrix[:, :2]
        @ source_points[0]
    )

    matrix[:, 2] = (
        target_points[0]
        - transformed_first_point
    )

    return (
        matrix,
        scale,
        angle_degrees,
    )


def calculate_output_canvas(
    reference: np.ndarray,
    revised: np.ndarray,
    transform_matrix: np.ndarray,
) -> tuple[
    tuple[int, int],
    np.ndarray,
    np.ndarray,
]:
    revised_height, revised_width = revised.shape[:2]
    reference_height, reference_width = reference.shape[:2]

    revised_corners = np.array(
        [
            [0, 0],
            [revised_width, 0],
            [revised_width, revised_height],
            [0, revised_height],
        ],
        dtype=np.float64,
    ).reshape(-1, 1, 2)

    transformed_corners = cv2.transform(
        revised_corners,
        transform_matrix,
    ).reshape(-1, 2)

    reference_corners = np.array(
        [
            [0, 0],
            [reference_width, 0],
            [reference_width, reference_height],
            [0, reference_height],
        ],
        dtype=np.float64,
    )

    all_corners = np.vstack(
        [
            transformed_corners,
            reference_corners,
        ]
    )

    minimum_x = float(
        np.floor(all_corners[:, 0].min())
    )

    minimum_y = float(
        np.floor(all_corners[:, 1].min())
    )

    maximum_x = float(
        np.ceil(all_corners[:, 0].max())
    )

    maximum_y = float(
        np.ceil(all_corners[:, 1].max())
    )

    offset_x = -minimum_x
    offset_y = -minimum_y

    output_width = max(
        1,
        int(maximum_x - minimum_x),
    )

    output_height = max(
        1,
        int(maximum_y - minimum_y),
    )

    adjusted_matrix = transform_matrix.copy()

    adjusted_matrix[0, 2] += offset_x
    adjusted_matrix[1, 2] += offset_y

    reference_offset = np.array(
        [
            round(offset_x),
            round(offset_y),
        ],
        dtype=np.int64,
    )

    return (
        (
            output_width,
            output_height,
        ),
        adjusted_matrix,
        reference_offset,
    )


def place_reference_on_canvas(
    reference: np.ndarray,
    output_size: tuple[int, int],
    offset: np.ndarray,
) -> np.ndarray:
    output_width, output_height = output_size

    canvas = np.full(
        (
            output_height,
            output_width,
            3,
        ),
        255,
        dtype=np.uint8,
    )

    x = int(offset[0])
    y = int(offset[1])

    height, width = reference.shape[:2]

    canvas[
        y:y + height,
        x:x + width,
    ] = reference

    return canvas


def align_drawing(
    reference: np.ndarray,
    revised: np.ndarray,
    reference_points: np.ndarray,
    revised_points: np.ndarray,
) -> tuple[
    np.ndarray,
    np.ndarray,
    float,
    float,
]:
    (
        transform_matrix,
        scale,
        angle,
    ) = calculate_similarity_transform(
        revised_points,
        reference_points,
    )

    (
        output_size,
        adjusted_matrix,
        reference_offset,
    ) = calculate_output_canvas(
        reference,
        revised,
        transform_matrix,
    )

    output_width, output_height = output_size

    if output_width * output_height > 400_000_000:
        raise MemoryError(
            "Canvas final grande demais."
        )

    revised_aligned = cv2.warpAffine(
        revised,
        adjusted_matrix,
        output_size,
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )

    reference_canvas = place_reference_on_canvas(
        reference,
        output_size,
        reference_offset,
    )

    return (
        reference_canvas,
        revised_aligned,
        scale,
        angle,
    )


def preprocess_drawing(
    image: np.ndarray,
    threshold: int = COMPARISON_THRESHOLD,
) -> np.ndarray:
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY,
    )

    gray = cv2.GaussianBlur(
        gray,
        (3, 3),
        0,
    )

    _, binary = cv2.threshold(
        gray,
        threshold,
        255,
        cv2.THRESH_BINARY_INV,
    )

    return binary


def create_comparison(
    reference: np.ndarray,
    revised: np.ndarray,
    threshold: int = COMPARISON_THRESHOLD,
    tolerance_pixels: int = TOLERANCE_PIXELS,
) -> tuple[np.ndarray, np.ndarray]:
    reference_binary = preprocess_drawing(
        reference,
        threshold,
    )

    revised_binary = preprocess_drawing(
        revised,
        threshold,
    )

    kernel_size = (
        tolerance_pixels * 2 + 1
    )

    kernel = np.ones(
        (
            kernel_size,
            kernel_size,
        ),
        dtype=np.uint8,
    )

    reference_dilated = cv2.dilate(
        reference_binary,
        kernel,
    )

    revised_dilated = cv2.dilate(
        revised_binary,
        kernel,
    )

    common_reference = cv2.bitwise_and(
        reference_binary,
        revised_dilated,
    )

    common_revised = cv2.bitwise_and(
        revised_binary,
        reference_dilated,
    )

    removed = cv2.bitwise_and(
        reference_binary,
        cv2.bitwise_not(
            revised_dilated
        ),
    )

    added = cv2.bitwise_and(
        revised_binary,
        cv2.bitwise_not(
            reference_dilated
        ),
    )

    common = cv2.bitwise_or(
        common_reference,
        common_revised,
    )

    comparison = np.full(
        reference.shape,
        255,
        dtype=np.uint8,
    )

    comparison[common > 0] = (
        0,
        0,
        0,
    )

    comparison[removed > 0] = (
        255,
        0,
        0,
    )

    comparison[added > 0] = (
        0,
        0,
        255,
    )

    difference = cv2.bitwise_or(
        removed,
        added,
    )

    return (
        comparison,
        difference,
    )


def create_overlay(
    reference: np.ndarray,
    revised: np.ndarray,
) -> np.ndarray:
    reference_gray = cv2.cvtColor(
        reference,
        cv2.COLOR_BGR2GRAY,
    )

    revised_gray = cv2.cvtColor(
        revised,
        cv2.COLOR_BGR2GRAY,
    )

    reference_lines = (
        reference_gray
        < COMPARISON_THRESHOLD
    )

    revised_lines = (
        revised_gray
        < COMPARISON_THRESHOLD
    )

    overlay = np.full(
        reference.shape,
        255,
        dtype=np.uint8,
    )

    overlay[reference_lines] = (
        255,
        0,
        0,
    )

    overlay[revised_lines] = (
        0,
        0,
        255,
    )

    common = (
        reference_lines
        & revised_lines
    )

    overlay[common] = (
        0,
        0,
        0,
    )

    return overlay


def save_image(
    filename: str,
    image: np.ndarray,
) -> None:
    success = cv2.imwrite(
        filename,
        image,
        [
            cv2.IMWRITE_PNG_COMPRESSION,
            3,
        ],
    )

    if not success:
        raise RuntimeError(
            f"Falha ao salvar: {filename}"
        )


class CompareViewer:
    def __init__(
        self,
        images: dict[str, np.ndarray],
    ) -> None:
        self.images = images
        self.current_name = next(iter(images))
        self.current_image = images[self.current_name]

        self.zoom = 1.0
        self.fit_zoom = 1.0

        self.offset_x = 0.0
        self.offset_y = 0.0

        self.drag_start_x = 0
        self.drag_start_y = 0

        self.image_start_x = 0.0
        self.image_start_y = 0.0

        self.photo_image: ImageTk.PhotoImage | None = None
        self.canvas_image_id: int | None = None

        self.root = tk.Tk()
        self.root.title("2D Compare")
        self.root.geometry("1400x850")
        self.root.minsize(900, 600)

        self.create_interface()
        self.bind_events()

        self.root.after(
            100,
            self.fit_image,
        )

    def create_interface(self) -> None:
        self.main_frame = ttk.Frame(
            self.root
        )

        self.main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        self.sidebar = ttk.Frame(
            self.main_frame,
            width=220,
            padding=12,
        )

        self.sidebar.pack(
            side=tk.LEFT,
            fill=tk.Y,
        )

        self.sidebar.pack_propagate(False)

        self.viewer_frame = ttk.Frame(
            self.main_frame
        )

        self.viewer_frame.pack(
            side=tk.RIGHT,
            fill=tk.BOTH,
            expand=True,
        )

        title = ttk.Label(
            self.sidebar,
            text="Visualização",
            font=(
                "Segoe UI",
                14,
                "bold",
            ),
        )

        title.pack(
            anchor=tk.W,
            pady=(0, 14),
        )

        self.buttons: dict[
            str,
            ttk.Button
        ] = {}

        for name in self.images:
            button = ttk.Button(
                self.sidebar,
                text=name,
                command=lambda selected=name: (
                    self.select_image(selected)
                ),
            )

            button.pack(
                fill=tk.X,
                pady=4,
            )

            self.buttons[name] = button

        ttk.Separator(
            self.sidebar,
            orient=tk.HORIZONTAL,
        ).pack(
            fill=tk.X,
            pady=16,
        )

        ttk.Button(
            self.sidebar,
            text="Ajustar à janela",
            command=self.fit_image,
        ).pack(
            fill=tk.X,
            pady=4,
        )

        ttk.Button(
            self.sidebar,
            text="Zoom 100%",
            command=self.actual_size,
        ).pack(
            fill=tk.X,
            pady=4,
        )

        ttk.Button(
            self.sidebar,
            text="Zoom +",
            command=lambda: self.change_zoom(
                1.25
            ),
        ).pack(
            fill=tk.X,
            pady=4,
        )

        ttk.Button(
            self.sidebar,
            text="Zoom −",
            command=lambda: self.change_zoom(
                0.8
            ),
        ).pack(
            fill=tk.X,
            pady=4,
        )

        ttk.Separator(
            self.sidebar,
            orient=tk.HORIZONTAL,
        ).pack(
            fill=tk.X,
            pady=16,
        )

        ttk.Label(
            self.sidebar,
            text=(
                "Controles\n\n"
                "Scroll: zoom\n"
                "Arrastar: mover\n"
                "Teclas 1–5: alternar\n"
                "F: ajustar à janela\n"
                "R: zoom 100%"
            ),
            justify=tk.LEFT,
        ).pack(
            anchor=tk.W,
        )

        self.status_text = tk.StringVar()

        ttk.Label(
            self.sidebar,
            textvariable=self.status_text,
            wraplength=190,
        ).pack(
            side=tk.BOTTOM,
            anchor=tk.W,
            fill=tk.X,
            pady=8,
        )

        self.canvas = tk.Canvas(
            self.viewer_frame,
            background="#303030",
            highlightthickness=0,
        )

        self.canvas.pack(
            fill=tk.BOTH,
            expand=True,
        )

    def bind_events(self) -> None:
        self.canvas.bind(
            "<Configure>",
            self.on_resize,
        )

        self.canvas.bind(
            "<MouseWheel>",
            self.on_mouse_wheel,
        )

        self.canvas.bind(
            "<Button-4>",
            lambda event: self.zoom_at(
                event.x,
                event.y,
                1.15,
            ),
        )

        self.canvas.bind(
            "<Button-5>",
            lambda event: self.zoom_at(
                event.x,
                event.y,
                0.87,
            ),
        )

        self.canvas.bind(
            "<ButtonPress-1>",
            self.start_drag,
        )

        self.canvas.bind(
            "<B1-Motion>",
            self.drag_image,
        )

        self.root.bind(
            "<KeyPress-f>",
            lambda event: self.fit_image(),
        )

        self.root.bind(
            "<KeyPress-r>",
            lambda event: self.actual_size(),
        )

        names = list(self.images.keys())

        for index, name in enumerate(
            names[:9],
            start=1,
        ):
            self.root.bind(
                str(index),
                lambda event, selected=name: (
                    self.select_image(selected)
                ),
            )

    def select_image(
        self,
        name: str,
    ) -> None:
        if name not in self.images:
            return

        self.current_name = name
        self.current_image = self.images[name]

        self.fit_image()

    def fit_image(self) -> None:
        canvas_width = max(
            1,
            self.canvas.winfo_width(),
        )

        canvas_height = max(
            1,
            self.canvas.winfo_height(),
        )

        image_height, image_width = (
            self.current_image.shape[:2]
        )

        self.fit_zoom = min(
            canvas_width / image_width,
            canvas_height / image_height,
        )

        self.zoom = self.fit_zoom

        self.offset_x = (
            canvas_width
            - image_width * self.zoom
        ) / 2

        self.offset_y = (
            canvas_height
            - image_height * self.zoom
        ) / 2

        self.render()

    def actual_size(self) -> None:
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        image_height, image_width = (
            self.current_image.shape[:2]
        )

        self.zoom = 1.0

        self.offset_x = (
            canvas_width
            - image_width
        ) / 2

        self.offset_y = (
            canvas_height
            - image_height
        ) / 2

        self.render()

    def change_zoom(
        self,
        factor: float,
    ) -> None:
        center_x = (
            self.canvas.winfo_width()
            / 2
        )

        center_y = (
            self.canvas.winfo_height()
            / 2
        )

        self.zoom_at(
            center_x,
            center_y,
            factor,
        )

    def on_mouse_wheel(
        self,
        event,
    ) -> None:
        factor = (
            1.15
            if event.delta > 0
            else 0.87
        )

        self.zoom_at(
            event.x,
            event.y,
            factor,
        )

    def zoom_at(
        self,
        mouse_x: float,
        mouse_y: float,
        factor: float,
    ) -> None:
        old_zoom = self.zoom

        new_zoom = max(
            0.01,
            min(
                20.0,
                old_zoom * factor,
            ),
        )

        if abs(new_zoom - old_zoom) < 1e-10:
            return

        image_x = (
            mouse_x
            - self.offset_x
        ) / old_zoom

        image_y = (
            mouse_y
            - self.offset_y
        ) / old_zoom

        self.zoom = new_zoom

        self.offset_x = (
            mouse_x
            - image_x * new_zoom
        )

        self.offset_y = (
            mouse_y
            - image_y * new_zoom
        )

        self.render()

    def start_drag(
        self,
        event,
    ) -> None:
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        self.image_start_x = self.offset_x
        self.image_start_y = self.offset_y

    def drag_image(
        self,
        event,
    ) -> None:
        self.offset_x = (
            self.image_start_x
            + event.x
            - self.drag_start_x
        )

        self.offset_y = (
            self.image_start_y
            + event.y
            - self.drag_start_y
        )

        self.render()

    def on_resize(
        self,
        event,
    ) -> None:
        if self.zoom <= self.fit_zoom * 1.01:
            self.fit_image()
        else:
            self.render()

    def get_visible_region(
        self,
    ) -> tuple[
        np.ndarray,
        float,
        float,
        float,
    ]:
        canvas_width = max(
            1,
            self.canvas.winfo_width(),
        )

        canvas_height = max(
            1,
            self.canvas.winfo_height(),
        )

        image_height, image_width = (
            self.current_image.shape[:2]
        )

        left = max(
            0,
            int(
                np.floor(
                    -self.offset_x
                    / self.zoom
                )
            ),
        )

        top = max(
            0,
            int(
                np.floor(
                    -self.offset_y
                    / self.zoom
                )
            ),
        )

        right = min(
            image_width,
            int(
                np.ceil(
                    (
                        canvas_width
                        - self.offset_x
                    )
                    / self.zoom
                )
            ),
        )

        bottom = min(
            image_height,
            int(
                np.ceil(
                    (
                        canvas_height
                        - self.offset_y
                    )
                    / self.zoom
                )
            ),
        )

        if right <= left or bottom <= top:
            return (
                np.full(
                    (1, 1, 3),
                    255,
                    dtype=np.uint8,
                ),
                0,
                0,
                1,
            )

        region = self.current_image[
            top:bottom,
            left:right,
        ]

        screen_x = (
            self.offset_x
            + left * self.zoom
        )

        screen_y = (
            self.offset_y
            + top * self.zoom
        )

        return (
            region,
            screen_x,
            screen_y,
            self.zoom,
        )

    def render(self) -> None:
        self.canvas.delete("all")

        (
            region,
            screen_x,
            screen_y,
            zoom,
        ) = self.get_visible_region()

        region_height, region_width = (
            region.shape[:2]
        )

        display_width = max(
            1,
            round(region_width * zoom),
        )

        display_height = max(
            1,
            round(region_height * zoom),
        )

        interpolation = (
            cv2.INTER_AREA
            if zoom < 1
            else cv2.INTER_NEAREST
        )

        display_image = cv2.resize(
            region,
            (
                display_width,
                display_height,
            ),
            interpolation=interpolation,
        )

        display_rgb = cv2.cvtColor(
            display_image,
            cv2.COLOR_BGR2RGB,
        )

        pil_image = Image.fromarray(
            display_rgb
        )

        self.photo_image = ImageTk.PhotoImage(
            pil_image
        )

        self.canvas_image_id = (
            self.canvas.create_image(
                screen_x,
                screen_y,
                anchor=tk.NW,
                image=self.photo_image,
            )
        )

        image_height, image_width = (
            self.current_image.shape[:2]
        )

        zoom_percentage = self.zoom * 100

        self.status_text.set(
            f"{self.current_name}\n"
            f"{image_width} × {image_height} px\n"
            f"Zoom: {zoom_percentage:.1f}%"
        )

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Uso:\n"
            "py compare_2d.py "
            "desenho_antigo.tif "
            "desenho_novo.svg"
        )

        raise SystemExit(1)

    reference_path = sys.argv[1]
    revised_path = sys.argv[2]

    reference = load_drawing(
        reference_path
    )

    revised = load_drawing(
        revised_path
    )

    reference_points = select_reference_points(
        reference,
        "Desenho antigo: selecione dois pontos",
    )

    revised_points = select_reference_points(
        revised,
        "Desenho novo: selecione os mesmos dois pontos",
    )

    (
        reference_canvas,
        revised_aligned,
        scale,
        angle,
    ) = align_drawing(
        reference,
        revised,
        reference_points,
        revised_points,
    )

    (
        comparison,
        difference,
    ) = create_comparison(
        reference_canvas,
        revised_aligned,
    )

    overlay = create_overlay(
        reference_canvas,
        revised_aligned,
    )

    save_image(
        "01_desenho_antigo.png",
        reference_canvas,
    )

    save_image(
        "02_desenho_novo_alinhado.png",
        revised_aligned,
    )

    save_image(
        "03_sobreposicao.png",
        overlay,
    )

    save_image(
        "04_comparacao_colorida.png",
        comparison,
    )

    save_image(
        "05_diferencas.png",
        difference,
    )

    print(
        f"Escala aplicada: {scale:.8f}"
    )

    print(
        f"Rotação aplicada: "
        f"{angle:.6f} graus"
    )

    viewer = CompareViewer(
        {
            "1 — Desenho antigo": reference_canvas,
            "2 — Desenho novo": revised_aligned,
            "3 — Compare": comparison,
            "4 — Sobreposição": overlay,
            "5 — Diferenças": cv2.cvtColor(
                difference,
                cv2.COLOR_GRAY2BGR,
            ),
        }
    )

    viewer.run()


if __name__ == "__main__":
    main()