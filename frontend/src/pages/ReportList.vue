<template>
	<div class="mx-auto max-w-3xl p-6">
		<div class="mb-4 flex items-center justify-between">
			<h1 class="text-xl font-semibold">OPG Reports</h1>
			<router-link
				to="/dental_opg/new"
				class="rounded bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
			>
				+ New Report
			</router-link>
		</div>

		<div v-if="loading" class="text-sm text-gray-500">Loading...</div>
		<div v-else-if="!reports.length" class="text-sm text-gray-500">No reports yet.</div>
		<div v-else class="divide-y rounded border">
			<router-link
				v-for="r in reports"
				:key="r.name"
				:to="`/dental_opg/${r.name}`"
				class="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
			>
				<div>
					<div class="font-medium">{{ r.name }}</div>
					<div class="text-xs text-gray-500">{{ r.patient }} &middot; {{ r.report_date }}</div>
				</div>
				<span
					class="rounded px-2 py-0.5 text-xs"
					:class="r.status === 'Final' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
				>
					{{ r.status }}
				</span>
			</router-link>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listReports } from '../api'

const reports = ref([])
const loading = ref(true)

onMounted(async () => {
	reports.value = await listReports()
	loading.value = false
})
</script>
