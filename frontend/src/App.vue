<template>
	<AppHeader v-if="route.name !== 'Login'" />
	<router-view />
</template>

<script setup>
import { useRoute } from 'vue-router'
import AppHeader from './components/AppHeader.vue'

const route = useRoute()
</script>
