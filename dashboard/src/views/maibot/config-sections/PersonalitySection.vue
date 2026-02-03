<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-account-heart</v-icon>
      {{ tm("configSections.personality.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <!-- 人格特质 -->
        <v-col cols="12">
          <v-textarea
            v-model="localConfig.personality"
            :label="tm('configSections.personality.personality')"
            variant="outlined"
            rows="3"
            counter
          />
        </v-col>

        <!-- 回复风格 -->
        <v-col cols="12">
          <v-textarea
            v-model="localConfig.reply_style"
            :label="tm('configSections.personality.reply_style')"
            variant="outlined"
            rows="3"
          />
        </v-col>

        <!-- 说话规则 -->
        <v-col cols="12">
          <v-textarea
            v-model="localConfig.plan_style"
            :label="tm('configSections.personality.plan_style')"
            variant="outlined"
            rows="4"
          />
        </v-col>

        <!-- 识图规则 -->
        <v-col cols="12">
          <v-textarea
            v-model="localConfig.visual_style"
            :label="tm('configSections.personality.visual_style')"
            variant="outlined"
            rows="2"
          />
        </v-col>

        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.state_probability"
            :label="tm('configSections.personality.state_probability')"
            type="number"
            step="0.1"
            min="0"
            max="1"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- 多重人格 -->
        <v-col cols="12">
          <div class="text-subtitle-2 mb-2">
            {{ tm("configSections.personality.states") }}
          </div>
          <div
            v-for="(state, index) in localConfig.states || []"
            :key="index"
            class="mb-2"
          >
            <v-textarea
              v-model="localConfig.states[index]"
              variant="outlined"
              density="compact"
              rows="2"
              hide-details
              class="mb-1"
            />
            <v-btn
              size="x-small"
              color="error"
              variant="text"
              @click="removeState(index)"
            >
              {{ tm("configSections.personality.delete_state") }}
            </v-btn>
          </div>
          <v-btn variant="outlined" size="small" @click="addState">
            <v-icon start>mdi-plus</v-icon>
            {{ tm("configSections.personality.add_state") }}
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
  personality: props.config?.personality || "",
  reply_style: props.config?.reply_style || "",
  plan_style: props.config?.plan_style || "",
  visual_style: props.config?.visual_style || "",
  state_probability: props.config?.state_probability || 0.3,
  states: props.config?.states || [],
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

const addState = () => {
  localConfig.value.states = [...(localConfig.value.states || []), ""];
};

const removeState = (index: number) => {
  localConfig.value.states = localConfig.value.states.filter(
    (_: any, i: number) => i !== index,
  );
};
</script>
