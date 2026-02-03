<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-web</v-icon>
      {{ tm("configSections.webui.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.enabled"
            :label="tm('configSections.webui.enabled')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.mode"
            :items="modeOptions"
            :label="tm('configSections.webui.mode')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.anti_crawler_mode"
            :items="antiCrawlerModes"
            :label="tm('configSections.webui.anti_crawler_mode')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model="localConfig.allowed_ips"
            :label="tm('configSections.webui.allowed_ips')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.trust_xff"
            :label="tm('configSections.webui.trust_xff')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.secure_cookie"
            :label="tm('configSections.webui.secure_cookie')"
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

const modeOptions = [
  { title: "development", value: "development" },
  { title: "production", value: "production" },
];

const antiCrawlerModes = [
  { title: "禁用 (false)", value: "false" },
  { title: "严格 (strict)", value: "strict" },
  { title: "宽松 (loose)", value: "loose" },
  { title: "基础 (basic)", value: "basic" },
];

const localConfig = ref({
  enabled: props.config?.enabled ?? true,
  mode: props.config?.mode || "production",
  anti_crawler_mode: props.config?.anti_crawler_mode || "loose",
  allowed_ips: props.config?.allowed_ips || "127.0.0.1",
  trust_xff: props.config?.trust_xff ?? false,
  secure_cookie: props.config?.secure_cookie ?? false,
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);
</script>
