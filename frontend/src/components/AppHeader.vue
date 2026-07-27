<template>
	<div class="flex items-center justify-between border-b bg-white px-6 py-3">
		<router-link to="/dental_opg" class="text-sm font-semibold text-gray-900">
			Yenepoya Dental College &middot; OPG Reporting
		</router-link>
		<button
			@click="handleLogout"
			:disabled="loggingOut"
			class="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 disabled:opacity-50"
		>
			{{ loggingOut ? 'Logging out...' : 'Logout' }}
		</button>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { logout } from '../api'

const loggingOut = ref(false)

async function handleLogout() {
	loggingOut.value = true
	try {
		await logout()
	} finally {
		window.location.href = '/dental_opg/login'
	}
}
</script>
