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


def _load_font(width, height):
	font_size = max(14, int(min(width, height) * 0.03))
	try:
		return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
	except OSError:
		return ImageFont.load_default()


def _line_width(width, height):
	return max(2, int(min(width, height) * 0.003))


def _path_coords(ann, width, height):
	if not ann.path_data:
		return []
	return [_denormalize(p["x"], p["y"], width, height) for p in json.loads(ann.path_data)]


def catmull_rom_points(points, samples_per_segment=16):
	"""Sample a smooth curve passing through every control point (uniform
	Catmull-Rom expressed as cubic Beziers - same math as curvePath() in
	ImageViewer.vue, so the baked image matches what the dentist drew)."""
	if len(points) < 2:
		return list(points)
	out = [points[0]]
	for i in range(len(points) - 1):
		p0 = points[i - 1] if i > 0 else points[i]
		p1, p2 = points[i], points[i + 1]
		p3 = points[i + 2] if i + 2 < len(points) else p2
		c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
		c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
		for step in range(1, samples_per_segment + 1):
			t = step / samples_per_segment
			mt = 1 - t
			out.append(
				tuple(
					mt**3 * p1[k] + 3 * mt**2 * t * c1[k] + 3 * mt * t**2 * c2[k] + t**3 * p2[k]
					for k in (0, 1)
				)
			)
	return out


def _draw_text(draw, ann, width, height):
	x1, y1 = _denormalize(ann.x or 0, ann.y or 0, width, height)
	color = ann.color or "#ff0000"
	draw.text((x1, y1), ann.label_text or "", fill=color, font=_load_font(width, height))


def _draw_freehand(draw, ann, width, height):
	coords = _path_coords(ann, width, height)
	if len(coords) > 1:
		draw.line(coords, fill=ann.color or "#ff0000", width=_line_width(width, height))


def _draw_curve(draw, ann, width, height):
	coords = _path_coords(ann, width, height)
	if len(coords) > 1:
		draw.line(catmull_rom_points(coords), fill=ann.color or "#ff0000", width=_line_width(width, height))


def _draw_landmark(draw, ann, width, height):
	cx, cy = _denormalize(ann.x or 0, ann.y or 0, width, height)
	color = ann.color or "#ff0000"
	arm = max(6, int(min(width, height) * 0.015))
	line_width = _line_width(width, height)
	draw.line([cx - arm, cy, cx + arm, cy], fill=color, width=line_width)
	draw.line([cx, cy - arm, cx, cy + arm], fill=color, width=line_width)
	if ann.label_text:
		draw.text((cx + arm + 2, cy - arm), ann.label_text, fill=color, font=_load_font(width, height))


_DRAW_FUNCS = {
	"Point": _draw_point,
	"Arrow": _draw_arrow,
	"Text": _draw_text,
	"Freehand": _draw_freehand,
	"Polyline": _draw_freehand,  # straight segments between vertices, same as freehand
	"Curve": _draw_curve,
	"Landmark": _draw_landmark,
}


def get_annotated_image_bytes(report):
	"""Return the report's opg_image with all its annotations baked in as
	actual pixels, so both the PDF print format and the docx export can embed
	one flattened image instead of relying on an HTML/SVG overlay that
	wkhtmltopdf has no reliable way to align against a static render.

	Returns None if there's no image at all. Always returns JPEG bytes,
	even with no annotations to draw - the source image may be a PNG
	upload, and callers (the print format, wkhtmltopdf) rely on the
	content-type they set matching the actual bytes.
	"""
	if not report.opg_image:
		return None

	_, content = get_file(report.opg_image)

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
