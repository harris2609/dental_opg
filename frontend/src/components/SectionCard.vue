<template>
	<div class="rounded border bg-white p-4">
		<h2 class="mb-2 text-sm font-semibold text-gray-800">{{ section }}</h2>

		<div class="mb-3 flex flex-wrap gap-1.5">
			<button
				v-for="sf in standardFindings"
				:key="sf.name"
				class="rounded-full border border-gray-300 px-2.5 py-1 text-xs hover:bg-gray-100"
				@click="addFinding(sf)"
			>
				+ {{ sf.finding_label }}
			</button>
		</div>

		<div v-if="rows.length" class="space-y-2">
			<div v-for="(row, idx) in rows" :key="idx" class="flex flex-wrap items-center gap-2 rounded bg-gray-50 p-2 text-xs">
				<span class="min-w-[10rem] flex-1">
					{{ row.is_custom ? row.custom_text : labelFor(row.finding) }}
				</span>
				<select v-if="!row.is_custom && allowSide(row.finding)" v-model="row.side" class="rounded border px-1 py-0.5" @change="emitUpdate">
					<option value="">side...</option>
					<option>Left</option>
					<option>Right</option>
					<option>Bilateral</option>
				</select>
				<input
					v-if="!row.is_custom && allowTooth(row.finding)"
					v-model="row.tooth_number"
					placeholder="tooth #"
					class="w-20 rounded border px-1 py-0.5"
					@input="emitUpdate"
				/>
				<select v-if="!row.is_custom && allowLevel(row.finding)" v-model="row.level" class="rounded border px-1 py-0.5" @change="emitUpdate">
					<option value="">level...</option>
					<option>Cervical Third</option>
					<option>Middle Third</option>
					<option>Apical Third</option>
				</select>
				<button class="text-red-600" @click="removeRow(idx)">remove</button>
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
	</div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
	section: { type: String, required: true },
	standardFindings: { type: Array, default: () => [] },
	rows: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:rows'])

const customText = ref('')

function labelFor(findingName) {
	return props.standardFindings.find((f) => f.name === findingName)?.finding_label || findingName
}
function allowSide(findingName) {
	return !!props.standardFindings.find((f) => f.name === findingName)?.allow_side
}
function allowTooth(findingName) {
	return !!props.standardFindings.find((f) => f.name === findingName)?.allow_tooth
}
function allowLevel(findingName) {
	return !!props.standardFindings.find((f) => f.name === findingName)?.allow_level
}

function emitUpdate() {
	emit('update:rows', [...props.rows])
}

function addFinding(sf) {
	emit('update:rows', [
		...props.rows,
		{ section: props.section, finding: sf.name, is_custom: 0, side: '', tooth_number: '', level: '' },
	])
}

function addCustom() {
	if (!customText.value.trim()) return
	emit('update:rows', [...props.rows, { section: props.section, is_custom: 1, custom_text: customText.value.trim() }])
	customText.value = ''
}

function removeRow(idx) {
	const next = [...props.rows]
	next.splice(idx, 1)
	emit('update:rows', next)
}
</script>
