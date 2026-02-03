<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-brain</v-icon>
      {{ tm("configSections.memory.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.max_agent_iterations"
            :label="tm('configSections.memory.max_agent_iterations')"
            type="number"
            min="1"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.agent_timeout_seconds"
            :label="tm('configSections.memory.agent_timeout_seconds')"
            type="number"
            step="1"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.global_memory"
            :label="tm('configSections.memory.global_memory')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.planner_question"
            :label="tm('configSections.memory.planner_question')"
            color="primary"
          />
        </v-col>

        <!-- 全局记忆黑名单 -->
        <v-col cols="12">
          <div class="text-subtitle-2 mb-2">
            {{ tm("configSections.memory.global_memory_blacklist") }}
          </div>
          <div
            v-for="(item, index) in localConfig.global_memory_blacklist || []"
            :key="index"
            class="d-flex align-center mb-2"
          >
            <v-text-field
              v-model="localConfig.global_memory_blacklist[index]"
              variant="outlined"
              density="compact"
              hide-details
              class="flex-grow-1 mr-2"
              placeholder="qq:123456:group"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="removeBlacklist(index)"
            />
          </div>
          <v-btn variant="outlined" size="small" @click="addBlacklist">
            <v-icon start>mdi-plus</v-icon>
            {{ tm("common.add") }}
          </v-btn>
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
  max_agent_iterations: props.config?.max_agent_iterations ?? 5,
  agent_timeout_seconds: props.config?.agent_timeout_seconds ?? 180.0,
  global_memory: props.config?.global_memory ?? false,
  planner_question: props.config?.planner_question ?? true,
  global_memory_blacklist: props.config?.global_memory_blacklist || [],
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

const addBlacklist = () => {
  localConfig.value.global_memory_blacklist = [
    ...(localConfig.value.global_memory_blacklist || []),
    "",
  ];
};

const removeBlacklist = (index: number) => {
  localConfig.value.global_memory_blacklist =
    localConfig.value.global_memory_blacklist.filter(
      (_: any, i: number) => i !== index,
    );
};
</script>
