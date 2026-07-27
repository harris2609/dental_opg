import io
import json
import math

from PIL import Image, ImageDraw, ImageFont
from frappe.utils.file_manager import get_file


def _denormalize(x, y, width, height):
	return x * width, y * height


def _draw_point(draw, ann, width, height):
	cx, cy = _denormalize(ann.x or 0, ann.y or 0, width, height)
	radius = max(4, int(min(width, height) * 0.007))
	color = ann.color or "#ff0000"
	draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color)


def _draw_arrow(draw, ann, width, height):
	x1, y1 = _denormalize(ann.x or 0, ann.y or 0, width, height)
	x2, y2 = _denormalize(ann.x2 or 0, ann.y2 or 0, width, height)
	color = ann.color or "#ff0000"
	line_width = max(2, int(min(width, height) * 0.003))
	draw.line([x1, y1, x2, y2], fill=color, width=line_width)

	angle = math.atan2(y2 - y1, x2 - x1)
	arrow_len = max(10, int(min(width, height) * 0.02))
	for delta in (0.4, -0.4):
		ax = x2 - arrow_len * math.cos(angle + delta)
		ay = y2 - arrow_len * math.sin(angle + delta)
		draw.line([x2, y2, ax, ay], fill=color, width=line_width)


def _draw_text(draw, ann, width, height):
	x1, y1 = _denormalize(ann.x or 0, ann.y or 0, width, height)
	color = ann.color or "#ff0000"
	font_size = max(14, int(min(width, height) * 0.03))
	try:
		font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
	except OSError:
		font = ImageFont.load_default()
	draw.text((x1, y1), ann.label_text or "", fill=color, font=font)


def _draw_freehand(draw, ann, width, height):
	if not ann.path_data:
		return
	points = json.loads(ann.path_data)
	coords = [_denormalize(p["x"], p["y"], width, height) for p in points]
	if len(coords) > 1:
		color = ann.color or "#ff0000"
		line_width = max(2, int(min(width, height) * 0.003))
		draw.line(coords, fill=color, width=line_width)


_DRAW_FUNCS = {
	"Point": _draw_point,
	"Arrow": _draw_arrow,
	"Text": _draw_text,
	"Freehand": _draw_freehand,
}


def get_annotated_image_bytes(report):
	"""Return the report's opg_image with all its annotations baked in as
	actual pixels, so both the PDF print format and the docx export can embed
	one flattened image instead of relying on an HTML/SVG overlay that
	wkhtmltopdf has no reliable way to align against a static render.

	Returns None if there's no image at all. Returns the original bytes
	unchanged if there's an image but no annotations.
	"""
	if not report.opg_image:
		return None

	_, content = get_file(report.opg_image)

	if not report.annotations:
		return content

	image = Image.open(io.BytesIO(content)).convert("RGB")
	draw = ImageDraw.Draw(image)
	width, height = image.size

	for ann in report.annotations:
		draw_func = _DRAW_FUNCS.get(ann.annotation_type)
		if draw_func:
			draw_func(draw, ann, width, height)

	buffer = io.BytesIO()
	image.save(buffer, format="JPEG", quality=90)
	return buffer.getvalue()
