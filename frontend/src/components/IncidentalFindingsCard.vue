<template>
	<div class="rounded border bg-white p-4">
		<h2 class="mb-2 text-sm font-semibold text-gray-800">Incidental Findings</h2>

		<div v-if="findings.length" class="mb-3 space-y-1">
			<div
				v-for="row in findings"
				:key="row.name"
				class="flex items-center gap-2 rounded bg-gray-50 p-2 text-xs"
			>
				<span class="min-w-[8rem] flex-1">{{ row.finding_type }}</span>
				<span class="w-20 text-gray-600">{{ row.side }}</span>
				<span class="w-20 text-gray-600">{{ row.severity }}</span>
				<span class="w-24 text-gray-500">{{ row.finding_date }}</span>
				<button class="text-red-600" @click="remove(row)">remove</button>
			</div>
		</div>

		<div class="flex flex-wrap items-center gap-2">
			<input
				v-model="form.finding_type"
				placeholder="Finding type"
				class="flex-1 rounded border px-2 py-1 text-xs"
			/>
			<select v-model="form.side" class="rounded border px-2 py-1 text-xs">
				<option value="">side...</option>
				<option>Left</option>
				<option>Right</option>
				<option>Bilateral</option>
			</select>
			<select v-model="form.severity" class="rounded border px-2 py-1 text-xs">
				<option value="">severity...</option>
				<option>Mild</option>
				<option>Moderate</option>
				<option>Severe</option>
			</select>
			<button
				class="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
				:disabled="adding || !canAdd"
				@click="add"
			>
				{{ adding ? 'Adding...' : 'Add' }}
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getIncidentalFindings, addIncidentalFinding, deleteIncidentalFinding } from '../api'

const props = defineProps({ reportName: { type: String, required: true } })

const findings = ref([])
const adding = ref(false)
const form = reactive({ finding_type: '', side: '', severity: '' })

const canAdd = computed(() => form.finding_type.trim() && form.side && form.severity)

onMounted(async () => {
	findings.value = await getIncidentalFindings(props.reportName)
})

async function add() {
	if (!canAdd.value) return
	adding.value = true
	try {
		const name = await addIncidentalFinding(props.reportName, {
			finding_type: form.finding_type.trim(),
			side: form.side,
			severity: form.severity,
		})
		findings.value = [...findings.value, { name, ...form, finding_date: new Date().toISOString().slice(0, 10) }]
		form.finding_type = ''
		form.side = ''
		form.severity = ''
	} finally {
		adding.value = false
	}
}

async function remove(row) {
	await deleteIncidentalFinding(row.name)
	findings.value = findings.value.filter((r) => r.name !== row.name)
}
</script>
