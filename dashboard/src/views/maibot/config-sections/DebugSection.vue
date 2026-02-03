<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-bug</v-icon>
      {{ tm("configSections.debug.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_prompt"
            :label="tm('configSections.debug.show_prompt')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_replyer_prompt"
            :label="tm('configSections.debug.show_replyer_prompt')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_replyer_reasoning"
            :label="tm('configSections.debug.show_replyer_reasoning')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_jargon_prompt"
            :label="tm('configSections.debug.show_jargon_prompt')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_memory_prompt"
            :label="tm('configSections.debug.show_memory_prompt')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_planner_prompt"
            :label="tm('configSections.debug.show_planner_prompt')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.show_lpmm_paragraph"
            :label="tm('configSections.debug.show_lpmm_paragraph')"
            color="primary"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useModuleI18n } from "@/i18n/composables";

const { tm } = useModuleI18n("features/maibot");

interface Props {
  config: Record<string, any>;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:config", config: Record<string, any>): void;
}>();

const localConfig = ref({
  show_prompt: props.config?.show_prompt ?? false,
  show_replyer_prompt: props.config?.show_replyer_prompt ?? false,
  show_replyer_reasoning: props.config?.show_replyer_reasoning ?? false,
  show_jargon_prompt: props.config?.show_jargon_prompt ?? false,
  show_memory_prompt: props.config?.show_memory_prompt ?? false,
  show_planner_prompt: props.config?.show_planner_prompt ?? false,
  show_lpmm_paragraph: props.config?.show_lpmm_paragraph ?? false,
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);
</script>
