<template>
	<div class="flex min-h-screen items-center justify-center bg-gray-50">
		<div class="w-full max-w-sm rounded border bg-white p-6 shadow-sm">
			<h1 class="text-lg font-semibold text-gray-900">Yenepoya Dental College</h1>
			<p class="mb-6 text-sm text-gray-500">OPG Reporting</p>

			<form @submit.prevent="submit">
				<div class="mb-3">
					<label class="mb-1 block text-xs font-medium text-gray-700">Email</label>
					<input
						v-model="usr"
						type="text"
						autocomplete="username"
						required
						class="w-full rounded border px-3 py-2 text-sm"
					/>
				</div>
				<div class="mb-4">
					<label class="mb-1 block text-xs font-medium text-gray-700">Password</label>
					<input
						v-model="pwd"
						type="password"
						autocomplete="current-password"
						required
						class="w-full rounded border px-3 py-2 text-sm"
					/>
				</div>

				<div v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</div>

				<button
					type="submit"
					:disabled="submitting"
					class="w-full rounded bg-gray-900 px-3 py-2 text-sm text-white hover:bg-gray-700 disabled:opacity-50"
				>
					{{ submitting ? 'Logging in...' : 'Login' }}
				</button>
			</form>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { login } from '../api'

const route = useRoute()
const usr = ref('')
const pwd = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
	error.value = ''
	submitting.value = true
	try {
		await login(usr.value, pwd.value)
		const redirectTo = route.query['redirect-to']
		const target = typeof redirectTo === 'string' && redirectTo.startsWith('/dental_opg') ? redirectTo : '/dental_opg'
		window.location.href = target
	} catch (e) {
		error.value = e.messages?.[0] || 'Login failed'
		submitting.value = false
	}
}
</script>
