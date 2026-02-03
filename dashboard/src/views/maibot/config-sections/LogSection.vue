<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-log</v-icon>
      {{ tm("configSections.log.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localConfig.date_style"
            :label="tm('configSections.log.date_style')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.log_level_style"
            :items="logLevelStyles"
            :label="tm('configSections.log.log_level_style')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.color_text"
            :items="colorTextOptions"
            :label="tm('configSections.log.color_text')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.log_level"
            :items="logLevels"
            :label="tm('configSections.log.log_level')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.console_log_level"
            :items="logLevels"
            :label="tm('configSections.log.console_log_level')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.file_log_level"
            :items="logLevels"
            :label="tm('configSections.log.file_log_level')"
            variant="outlined"
            density="compact"
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

const logLevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];
const logLevelStyles = [
  { title: "FULL", value: "FULL" },
  { title: "compact", value: "compact" },
  { title: "lite", value: "lite" },
];
const colorTextOptions = [
  { title: "none", value: "none" },
  { title: "title", value: "title" },
  { title: "full", value: "full" },
];

const localConfig = ref({
  date_style: props.config?.date_style || "m-d H:i:s",
  log_level_style: props.config?.log_level_style || "lite",
  color_text: props.config?.color_text || "full",
  log_level: props.config?.log_level || "INFO",
  console_log_level: props.config?.console_log_level || "INFO",
  file_log_level: props.config?.file_log_level || "DEBUG",
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);
</script>
