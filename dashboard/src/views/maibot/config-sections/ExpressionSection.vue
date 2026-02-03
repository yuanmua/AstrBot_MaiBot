<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-school</v-icon>
      {{ tm("configSections.expression.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <!-- 黑话设置 -->
      <v-row>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.all_global_jargon"
            :label="tm('configSections.expression.all_global_jargon')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.enable_jargon_explanation"
            :label="tm('configSections.expression.enable_jargon_explanation')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.jargon_mode"
            :items="jargonModes"
            :label="tm('configSections.expression.jargon_mode')"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.expression_checked_only"
            :label="tm('configSections.expression.expression_checked_only')"
            color="primary"
          />
        </v-col>
      </v-row>

      <v-divider class="my-4" />

      <!-- 表达学习配置 -->
      <div class="text-subtitle-1 mb-3">
        {{ tm("configSections.expression.learning_list") }}
      </div>

      <v-card
        v-for="(rule, index) in localConfig.learning_list || []"
        :key="index"
        variant="outlined"
        class="mb-3 pa-3"
      >
        <div class="d-flex justify-space-between align-center mb-2">
          <span class="text-subtitle-2"
            >{{ tm("configSections.expression.rule") }} #{{ index + 1 }}</span
          >
          <v-btn
            icon="mdi-delete"
            size="small"
            variant="text"
            color="error"
            @click="removeRule(index)"
          />
        </div>
        <v-row dense>
          <v-col cols="12">
            <v-text-field
              v-model="rule[0]"
              :label="tm('configSections.expression.chat_stream_id')"
              variant="outlined"
              density="compact"
              :placeholder="
                tm('configSections.expression.chat_stream_id_placeholder')
              "
              hint="空字符串表示全局配置"
            />
          </v-col>
          <v-col cols="4">
            <v-select
              v-model="rule[1]"
              :items="enableOptions"
              :label="tm('configSections.expression.use_expression')"
              variant="outlined"
              density="compact"
            />
          </v-col>
          <v-col cols="4">
            <v-select
              v-model="rule[2]"
              :items="enableOptions"
              :label="tm('configSections.expression.learn_expression')"
              variant="outlined"
              density="compact"
            />
          </v-col>
          <v-col cols="4">
            <v-select
              v-model="rule[3]"
              :items="enableOptions"
              :label="tm('configSections.expression.learn_jargon')"
              variant="outlined"
              density="compact"
            />
          </v-col>
        </v-row>
      </v-card>

      <v-btn variant="outlined" size="small" @click="addRule" class="mb-4">
        <v-icon start>mdi-plus</v-icon>
        {{ tm("configSections.expression.add_rule") }}
      </v-btn>

      <v-divider class="my-4" />

      <!-- 表达优化配置 -->
      <div class="text-subtitle-1 mb-3">
        {{ tm("configSections.expression.self_reflect") }}
      </div>

      <v-row>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.expression_self_reflect"
            :label="tm('configSections.expression.auto_reflect')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.expression_manual_reflect"
            :label="tm('configSections.expression.manual_reflect')"
            color="primary"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.expression_auto_check_interval"
            :label="tm('configSections.expression.auto_check_interval')"
            type="number"
            min="60"
            variant="outlined"
            density="compact"
          />
        </v-col>
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.expression_auto_check_count"
            :label="tm('configSections.expression.auto_check_count')"
            type="number"
            min="1"
            max="100"
            variant="outlined"
            density="compact"
          />
        </v-col>
      </v-row>

      <!-- 手动反思操作员 -->
      <v-expand-transition>
        <div v-if="localConfig.expression_manual_reflect" class="mt-4">
          <v-divider class="mb-4" />
          <v-text-field
            v-model="localConfig.manual_reflect_operator_id"
            :label="tm('configSections.expression.operator_id')"
            variant="outlined"
            density="compact"
            placeholder="qq:123456:private"
          />
        </div>
      </v-expand-transition>
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

const enableOptions = [
  { title: tm("common.enable"), value: "enable" },
  { title: tm("common.disable"), value: "disable" },
];

const jargonModes = [
  { title: "上下文模式 (context)", value: "context" },
  { title: "Planner模式 (planner)", value: "planner" },
];

const localConfig = ref({
  all_global_jargon: props.config?.all_global_jargon ?? true,
  enable_jargon_explanation: props.config?.enable_jargon_explanation ?? true,
  jargon_mode: props.config?.jargon_mode || "planner",
  expression_checked_only: props.config?.expression_checked_only ?? true,
  expression_self_reflect: props.config?.expression_self_reflect ?? true,
  expression_manual_reflect: props.config?.expression_manual_reflect ?? false,
  expression_auto_check_interval:
    props.config?.expression_auto_check_interval ?? 600,
  expression_auto_check_count: props.config?.expression_auto_check_count ?? 20,
  manual_reflect_operator_id: props.config?.manual_reflect_operator_id || "",
  learning_list: props.config?.learning_list || [
    ["", "enable", "enable", "enable"],
  ],
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

const addRule = () => {
  localConfig.value.learning_list = [
    ...(localConfig.value.learning_list || []),
    ["", "enable", "enable", "enable"],
  ];
};

const removeRule = (index: number) => {
  localConfig.value.learning_list = localConfig.value.learning_list.filter(
    (_: any, i: number) => i !== index,
  );
};
</script>
