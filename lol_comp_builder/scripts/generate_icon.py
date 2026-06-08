from pathlib import Path

from PIL import Image


def build_square_icon(source: Path, target: Path) -> None:
    """Genera un icono cuadrado sin deformar el logo original."""
    image = Image.open(source).convert("RGBA")
    base_size = 256
    canvas = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))

    # Ajuste tipo contain: conserva proporcion y deja un margen pequeno para que Windows no lo recorte.
    image.thumbnail((240, 240), Image.Resampling.LANCZOS)
    offset_x = (base_size - image.width) // 2
    offset_y = (base_size - image.height) // 2
    canvas.paste(image, (offset_x, offset_y), image)
    canvas.save(target, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    source = project_root.parent / "logo.png"
    if not source.exists():
        source = project_root / "assets" / "logo.png"
    target = project_root / "assets" / "icon.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"No se encontro el logo en {source}")
    build_square_icon(source, target)


if __name__ == "__main__":
    main()
