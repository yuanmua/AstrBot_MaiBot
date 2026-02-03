<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-emoticon</v-icon>
      {{ tm("configSections.emoji.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.emoji_chance"
            :label="tm('configSections.emoji.emoji_chance')"
            type="number"
            step="0.1"
            min="0"
            max="1"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.max_reg_num"
            :label="tm('configSections.emoji.max_reg_num')"
            type="number"
            min="1"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.do_replace"
            :label="tm('configSections.emoji.do_replace')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.check_interval"
            :label="tm('configSections.emoji.check_interval')"
            type="number"
            min="1"
            variant="outlined"
            density="compact"
            hint="单位：分钟"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.steal_emoji"
            :label="tm('configSections.emoji.steal_emoji')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.content_filtration"
            :label="tm('configSections.emoji.content_filtration')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" v-if="localConfig.content_filtration">
          <v-text-field
            v-model="localConfig.filtration_prompt"
            :label="tm('configSections.emoji.filtration_prompt')"
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

const localConfig = ref({
  emoji_chance: props.config?.emoji_chance ?? 0.4,
  max_reg_num: props.config?.max_reg_num ?? 100,
  do_replace: props.config?.do_replace ?? true,
  check_interval: props.config?.check_interval ?? 10,
  steal_emoji: props.config?.steal_emoji ?? true,
  content_filtration: props.config?.content_filtration ?? false,
  filtration_prompt: props.config?.filtration_prompt || "符合公序良俗",
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);
</script>
