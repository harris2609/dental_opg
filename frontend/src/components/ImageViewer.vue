<template>
	<div class="flex h-full flex-col">
		<div class="flex flex-wrap items-center gap-1 border-b bg-white p-1.5 text-xs">
			<button class="toolbtn" @click="zoomOut">-</button>
			<span class="w-12 text-center text-gray-600">{{ Math.round(zoom * 100) }}%</span>
			<button class="toolbtn" @click="zoomIn">+</button>
			<button class="toolbtn" @click="fitToScreen">Fit</button>
			<span class="mx-1 h-4 border-l"></span>
			<button
				v-for="t in tools"
				:key="t.value"
				class="toolbtn"
				:class="mode === t.value ? 'bg-gray-900 text-white' : ''"
				@click="selectTool(t.value)"
			>
				{{ t.label }}
			</button>
			<span v-if="PATH_TOOLS.includes(mode)" class="text-gray-500">Click points, double-click or Enter to finish, Esc to cancel</span>
			<button class="toolbtn ml-auto text-red-600" @click="clearAnnotations">Clear annotations</button>
		</div>

		<div
			ref="viewport"
			class="relative flex-1 select-none overflow-hidden bg-gray-100 outline-none"
			:class="mode === 'pan' ? 'cursor-grab' : 'cursor-crosshair'"
			tabindex="0"
			@dblclick="finishPath"
			@keydown.enter.prevent="finishPath"
			@keydown.esc="cancelPath"
			@mousedown="onMouseDown"
			@mousemove="onMouseMove"
			@mouseup="onMouseUp"
			@mouseleave="onMouseUp"
			@wheel.prevent="onWheel"
		>
			<div v-if="!imageUrl" class="flex h-full items-center justify-center text-sm text-gray-400">
				No OPG image uploaded yet
			</div>
			<div class="absolute left-0 top-0 origin-top-left" :style="transformStyle">
				<img
					v-if="imageUrl"
					ref="imgEl"
					:src="imageUrl"
					class="pointer-events-none max-w-none"
					@load="onImageLoad"
				/>
				<svg
					v-if="imgSize.w"
					:width="imgSize.w"
					:height="imgSize.h"
					viewBox="0 0 1 1"
					preserveAspectRatio="none"
					class="absolute left-0 top-0"
				>
					<defs>
						<marker id="arrowhead" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto">
							<path d="M0,0 L4,2 L0,4 Z" fill="#ff0000" />
						</marker>
					</defs>
					<template v-for="(a, i) in annotations" :key="i">
						<circle v-if="a.annotation_type === 'Point'" :cx="a.x" :cy="a.y" r="0.007" fill="#ff0000" />
						<line
							v-else-if="a.annotation_type === 'Arrow'"
							:x1="a.x"
							:y1="a.y"
							:x2="a.x2"
							:y2="a.y2"
							stroke="#ff0000"
							stroke-width="0.003"
							marker-end="url(#arrowhead)"
						/>
						<polyline
							v-else-if="a.annotation_type === 'Freehand'"
							:points="pathPoints(a)"
							fill="none"
							stroke="#ff0000"
							stroke-width="0.003"
						/>
						<polyline
							v-else-if="a.annotation_type === 'Polyline'"
							:points="pathPoints(a)"
							fill="none"
							stroke="#ff0000"
							stroke-width="0.003"
						/>
						<path
							v-else-if="a.annotation_type === 'Curve'"
							:d="curvePath(parsePath(a))"
							fill="none"
							stroke="#ff0000"
							stroke-width="0.003"
						/>
						<g v-else-if="a.annotation_type === 'Landmark'">
							<line :x1="a.x - 0.012" :y1="a.y" :x2="a.x + 0.012" :y2="a.y" stroke="#ff0000" stroke-width="0.003" />
							<line :x1="a.x" :y1="a.y - 0.012" :x2="a.x" :y2="a.y + 0.012" stroke="#ff0000" stroke-width="0.003" />
							<text :x="a.x + 0.015" :y="a.y - 0.008" font-size="0.024" fill="#ff0000">{{ a.label_text }}</text>
						</g>
						<text v-else-if="a.annotation_type === 'Text'" :x="a.x" :y="a.y" font-size="0.028" fill="#ff0000">
							{{ a.label_text }}
						</text>
					</template>
					<polyline
						v-if="drawingPath.length"
						:points="drawingPath.map((p) => `${p.x},${p.y}`).join(' ')"
						fill="none"
						stroke="#ff0000"
						stroke-width="0.003"
					/>
					<polyline
						v-if="pendingPath.length && mode === 'Polyline'"
						:points="pendingPath.map((p) => `${p.x},${p.y}`).join(' ')"
						fill="none"
						stroke="#ff0000"
						stroke-width="0.003"
						stroke-dasharray="0.01 0.006"
					/>
					<path
						v-if="pendingPath.length && mode === 'Curve'"
						:d="curvePath(pendingPath)"
						fill="none"
						stroke="#ff0000"
						stroke-width="0.003"
						stroke-dasharray="0.01 0.006"
					/>
					<circle v-for="(p, k) in pendingPath" :key="`v${k}`" :cx="p.x" :cy="p.y" r="0.004" fill="#ff0000" />
				</svg>
			</div>
		</div>

		<div v-if="pendingText" class="flex gap-2 border-t bg-white p-2">
			<input
				ref="textInput"
				v-model="pendingText.label_text"
				:placeholder="pendingText.annotation_type === 'Landmark' ? 'Landmark name (optional), press Enter to place' : 'Annotation label, press Enter to place'"
				class="flex-1 rounded border px-2 py-1 text-sm"
				@keyup.enter="commitText"
				@keyup.esc="pendingText = null"
			/>
			<button class="toolbtn" @click="commitText">Add</button>
		</div>

		<div class="border-t p-2">
			<label class="toolbtn inline-block cursor-pointer">
				{{ imageUrl ? 'Replace OPG Image' : 'Upload OPG Image' }}
				<input type="file" accept="image/png,image/jpeg" class="hidden" @change="onFileChange" />
			</label>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'

const props = defineProps({
	imageUrl: { type: String, default: '' },
	annotations: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:annotations', 'upload'])

const tools = [
	{ value: 'pan', label: 'Pan' },
	{ value: 'Point', label: 'Point' },
	{ value: 'Landmark', label: 'Landmark' },
	{ value: 'Arrow', label: 'Arrow' },
	{ value: 'Text', label: 'Text' },
	{ value: 'Freehand', label: 'Freehand' },
	{ value: 'Polyline', label: 'Polyline' },
	{ value: 'Curve', label: 'Curve' },
]
const PATH_TOOLS = ['Polyline', 'Curve']
const LABEL_TOOLS = ['Text', 'Landmark']
const mode = ref('pan')

const viewport = ref(null)
const imgEl = ref(null)
const textInput = ref(null)
const imgSize = reactive({ w: 0, h: 0 })
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)

const transformStyle = computed(() => ({
	transform: `translate(${panX.value}px, ${panY.value}px) scale(${zoom.value})`,
	width: imgSize.w + 'px',
	height: imgSize.h + 'px',
}))

function onImageLoad() {
	imgSize.w = imgEl.value.naturalWidth
	imgSize.h = imgEl.value.naturalHeight
	fitToScreen()
}

function fitToScreen() {
	if (!imgSize.w || !viewport.value) return
	const vw = viewport.value.clientWidth
	const vh = viewport.value.clientHeight
	zoom.value = Math.min(vw / imgSize.w, vh / imgSize.h, 1) * 0.98
	panX.value = Math.max(0, (vw - imgSize.w * zoom.value) / 2)
	panY.value = Math.max(0, (vh - imgSize.h * zoom.value) / 2)
}

function zoomIn() {
	zoom.value = Math.min(zoom.value * 1.25, 8)
}
function zoomOut() {
	zoom.value = Math.max(zoom.value / 1.25, 0.1)
}
function onWheel(e) {
	if (e.deltaY < 0) zoomIn()
	else zoomOut()
}

function getNormalizedPoint(e) {
	const rect = viewport.value.getBoundingClientRect()
	const mx = e.clientX - rect.left
	const my = e.clientY - rect.top
	const cx = (mx - panX.value) / zoom.value
	const cy = (my - panY.value) / zoom.value
	return {
		x: Math.min(1, Math.max(0, cx / imgSize.w)),
		y: Math.min(1, Math.max(0, cy / imgSize.h)),
	}
}

function addAnnotation(annotation) {
	emit('update:annotations', [...props.annotations, annotation])
}
function clearAnnotations() {
	emit('update:annotations', [])
}

const panning = ref(false)
const panStart = ref({ x: 0, y: 0, panX: 0, panY: 0 })
const arrowStart = ref(null)
const drawingPath = ref([])
const pendingText = ref(null)
const pendingPath = ref([])

function selectTool(value) {
	finishPath()
	mode.value = value
}

function onMouseDown(e) {
	if (!imgSize.w) return
	if (mode.value === 'pan') {
		panning.value = true
		panStart.value = { x: e.clientX, y: e.clientY, panX: panX.value, panY: panY.value }
		return
	}
	const point = getNormalizedPoint(e)
	if (mode.value === 'Point') {
		addAnnotation({ annotation_type: 'Point', x: point.x, y: point.y })
	} else if (mode.value === 'Arrow') {
		arrowStart.value = point
	} else if (LABEL_TOOLS.includes(mode.value)) {
		// The viewport is focusable (for Enter/Esc on paths); without this the
		// mousedown's default focus would steal focus back from the label input.
		e.preventDefault()
		pendingText.value = { annotation_type: mode.value, x: point.x, y: point.y, label_text: '' }
		nextTick(() => textInput.value?.focus())
	} else if (mode.value === 'Freehand') {
		drawingPath.value = [point]
	} else if (PATH_TOOLS.includes(mode.value)) {
		viewport.value.focus()
		pendingPath.value = [...pendingPath.value, point]
	}
}

function onMouseMove(e) {
	if (panning.value) {
		panX.value = panStart.value.panX + (e.clientX - panStart.value.x)
		panY.value = panStart.value.panY + (e.clientY - panStart.value.y)
		return
	}
	if (mode.value === 'Freehand' && drawingPath.value.length) {
		drawingPath.value.push(getNormalizedPoint(e))
	}
}

function onMouseUp(e) {
	panning.value = false
	if (mode.value === 'Arrow' && arrowStart.value) {
		const end = getNormalizedPoint(e)
		addAnnotation({ annotation_type: 'Arrow', x: arrowStart.value.x, y: arrowStart.value.y, x2: end.x, y2: end.y })
		arrowStart.value = null
	}
	if (mode.value === 'Freehand' && drawingPath.value.length > 1) {
		addAnnotation({ annotation_type: 'Freehand', path_data: JSON.stringify(drawingPath.value) })
	}
	drawingPath.value = []
}

function commitText() {
	const pending = pendingText.value
	// A Landmark's crosshair marks the spot on its own; Text is nothing without a label.
	if (pending && (pending.label_text.trim() || pending.annotation_type === 'Landmark')) {
		addAnnotation({ ...pending, label_text: pending.label_text.trim() })
	}
	pendingText.value = null
}

// In screen pixels, so it means the same thing at every zoom level and
// image size - an image-relative threshold could be under 2px on screen
// and let the hand jitter between the two clicks through as a kink.
const SAME_POINT_PX = 5

function screenDistance(a, b) {
	return Math.hypot((a.x - b.x) * imgSize.w * zoom.value, (a.y - b.y) * imgSize.h * zoom.value)
}

function distinctPoints(points) {
	// dblclick is preceded by two mousedowns on the same spot - collapse them.
	return points.filter((p, i) => {
		const prev = points[i - 1]
		return !prev || screenDistance(p, prev) > SAME_POINT_PX
	})
}

function finishPath() {
	if (!PATH_TOOLS.includes(mode.value)) return
	const points = distinctPoints(pendingPath.value)
	if (points.length > 1) addAnnotation({ annotation_type: mode.value, path_data: JSON.stringify(points) })
	pendingPath.value = []
}

function cancelPath() {
	pendingPath.value = []
}

function parsePath(a) {
	try {
		return JSON.parse(a.path_data)
	} catch {
		return []
	}
}

function pathPoints(a) {
	return parsePath(a)
		.map((p) => `${p.x},${p.y}`)
		.join(' ')
}

// Same control-point math as image_utils.catmull_rom_points.
function curvePath(points) {
	if (points.length < 2) return ''
	let d = `M${points[0].x},${points[0].y}`
	for (let i = 0; i < points.length - 1; i++) {
		const p0 = points[i - 1] || points[i]
		const p1 = points[i]
		const p2 = points[i + 1]
		const p3 = points[i + 2] || p2
		const c1x = p1.x + (p2.x - p0.x) / 6
		const c1y = p1.y + (p2.y - p0.y) / 6
		const c2x = p2.x - (p3.x - p1.x) / 6
		const c2y = p2.y - (p3.y - p1.y) / 6
		d += ` C${c1x},${c1y} ${c2x},${c2y} ${p2.x},${p2.y}`
	}
	return d
}

function onFileChange(e) {
	const file = e.target.files[0]
	if (file) emit('upload', file)
	e.target.value = ''
}

// finishPath is exposed so Save/Generate keep a path the dentist has not
// double-clicked to finish yet.
defineExpose({ fitToScreen, finishPath })
</script>

<style scoped>
.toolbtn {
	@apply rounded bg-gray-100 px-2 py-1 hover:bg-gray-200;
}
</style>
