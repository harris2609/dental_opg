<template>
	<div class="rounded border bg-white p-4">
		<h2 class="mb-2 text-sm font-semibold text-gray-800">{{ section }}</h2>

		<FindingPicker class="mb-3" :items="standardFindings" label-field="finding_label" @pick="addFinding" />

		<div v-if="rows.length" class="space-y-2">
			<div v-for="(row, idx) in rows" :key="idx" class="rounded bg-gray-50 p-2 text-xs">
				<div class="flex flex-wrap items-center gap-2">
					<span class="min-w-[10rem] flex-1">
						{{ row.is_custom ? row.custom_text : labelFor(row.finding) }}
					</span>
					<select v-if="!row.is_custom && master(row)?.allow_side" v-model="row.side" class="rounded border px-1 py-0.5" @change="emitUpdate">
						<option value="">side...</option>
						<option>Left</option>
						<option>Right</option>
						<option>Bilateral</option>
					</select>
					<input
						v-if="!row.is_custom && master(row)?.allow_tooth"
						v-model="row.tooth_number"
						placeholder="tooth #"
						class="w-24 rounded border px-1 py-0.5"
						@input="emitUpdate"
					/>
					<select v-if="!row.is_custom && master(row)?.allow_level" v-model="row.level" class="rounded border px-1 py-0.5" @change="emitUpdate">
						<option value="">level...</option>
						<option>Cervical Third</option>
						<option>Middle Third</option>
						<option>Apical Third</option>
					</select>
					<button v-if="!row.is_custom" class="text-gray-700 underline" @click="toggleEdit(row)">
						{{ editing.has(row) ? 'done' : 'edit' }}
					</button>
					<button class="text-red-600" @click="removeRow(idx)">remove</button>
				</div>
				<div v-if="!row.is_custom && editing.has(row)" class="mt-2">
					<textarea
						v-model="row.edited_text"
						rows="5"
						class="w-full resize-y rounded border px-2 py-1 text-sm"
						@input="emitUpdate"
					></textarea>
					<button class="text-gray-600 underline" @click="resetEdit(row)">reset to standard text</button>
				</div>
				<p v-else-if="!row.is_custom && row.edited_text" class="mt-1 whitespace-pre-line text-gray-600">
					{{ row.edited_text }}
				</p>
			</div>
		</div>

		<div class="mt-3 flex gap-2">
			<input
				v-model="customText"
				placeholder="Add custom finding for this section"
				class="flex-1 rounded border px-2 py-1 text-xs"
				@keyup.enter="addCustom"
			/>
			<button class="rounded bg-gray-900 px-2 py-1 text-xs text-white" @click="addCustom">Add</button>
		</div>
		<p class="mt-1 text-[11px] text-gray-500">Custom findings are saved to the list for future reports.</p>
	</div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import FindingPicker from './FindingPicker.vue'
import { renderTemplate } from '../findingText'

const props = defineProps({
	section: { type: String, required: true },
	standardFindings: { type: Array, default: () => [] },
	rows: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:rows'])

const customText = ref('')
const editing = reactive(new Set())

function master(row) {
	return props.standardFindings.find((f) => f.name === row.finding)
}
function labelFor(findingName) {
	return props.standardFindings.find((f) => f.name === findingName)?.finding_label || findingName
}

function emitUpdate() {
	emit('update:rows', [...props.rows])
}

function toggleEdit(row) {
	if (editing.has(row)) {
		editing.delete(row)
		return
	}
	if (!row.edited_text) row.edited_text = renderTemplate(master(row)?.finding_template, row) || labelFor(row.finding)
	editing.add(row)
	emitUpdate()
}

function resetEdit(row) {
	row.edited_text = ''
	editing.delete(row)
	emitUpdate()
}

function addFinding(sf) {
	emit('update:rows', [
		...props.rows,
		{ section: props.section, finding: sf.name, is_custom: 0, side: '', tooth_number: '', level: '', edited_text: '' },
	])
}

function addCustom() {
	if (!customText.value.trim()) return
	emit('update:rows', [...props.rows, { section: props.section, is_custom: 1, custom_text: customText.value.trim() }])
	customText.value = ''
}

function removeRow(idx) {
	const next = [...props.rows]
	const [removed] = next.splice(idx, 1)
	editing.delete(removed)
	emit('update:rows', next)
}
</script>
