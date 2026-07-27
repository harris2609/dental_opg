<template>
	<div class="mx-auto max-w-4xl p-6">
		<div class="mb-4 flex items-center justify-between">
			<h1 class="text-xl font-semibold">Incidental Findings</h1>
			<a
				href="/api/method/dental_opg.api.export_incidental_findings_xlsx"
				class="rounded bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
			>
				Export to Excel
			</a>
		</div>

		<div v-if="loading" class="text-sm text-gray-500">Loading...</div>
		<div v-else-if="!findings.length" class="text-sm text-gray-500">No incidental findings yet.</div>
		<table v-else class="w-full divide-y rounded border text-sm">
			<thead>
				<tr class="bg-gray-50 text-left text-xs text-gray-500">
					<th class="px-3 py-2">Report</th>
					<th class="px-3 py-2">Patient</th>
					<th class="px-3 py-2">Finding Type</th>
					<th class="px-3 py-2">Side</th>
					<th class="px-3 py-2">Severity</th>
					<th class="px-3 py-2">Date</th>
					<th class="px-3 py-2">Reported By</th>
				</tr>
			</thead>
			<tbody class="divide-y">
				<tr v-for="row in findings" :key="row.name">
					<td class="px-3 py-2">
						<router-link :to="`/dental_opg/${row.report}`" class="text-gray-900 hover:underline">{{ row.report }}</router-link>
					</td>
					<td class="px-3 py-2">{{ row.patient }}</td>
					<td class="px-3 py-2">{{ row.finding_type }}</td>
					<td class="px-3 py-2 text-gray-600">{{ row.side }}</td>
					<td class="px-3 py-2 text-gray-600">{{ row.severity }}</td>
					<td class="px-3 py-2 text-gray-500">{{ row.finding_date }}</td>
					<td class="px-3 py-2 text-gray-500">{{ row.reported_by }}</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listAllIncidentalFindings } from '../api'

const findings = ref([])
const loading = ref(true)

onMounted(async () => {
	findings.value = await listAllIncidentalFindings()
	loading.value = false
})
</script>
