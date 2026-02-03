<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-chat</v-icon>
      {{ tm("configSections.chat.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-row>
        <!-- 聊天频率 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.talk_value"
            :label="tm('configSections.chat.talk_value')"
            type="number"
            step="0.1"
            min="0"
            max="1"
            variant="outlined"
            density="compact"
            hint="越小越沉默，范围 0-1"
          />
        </v-col>

        <!-- 提及必回复 -->
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.mentioned_bot_reply"
            :label="tm('configSections.chat.mentioned_bot_reply')"
            color="primary"
          />
        </v-col>

        <!-- 上下文长度 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.max_context_size"
            :label="tm('configSections.chat.max_context_size')"
            type="number"
            min="1"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- 规划器平滑 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.planner_smooth"
            :label="tm('configSections.chat.planner_smooth')"
            type="number"
            min="0"
            variant="outlined"
            density="compact"
            hint="推荐 1-5，0 为关闭"
          />
        </v-col>

        <!-- 思考模式 -->
        <v-col cols="12" md="6">
          <v-select
            v-model="localConfig.think_mode"
            :items="thinkModes"
            :label="tm('configSections.chat.think_mode')"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- 最大日志数量 -->
        <v-col cols="12" md="6">
          <v-text-field
            v-model.number="localConfig.plan_reply_log_max_per_chat"
            :label="tm('configSections.chat.plan_reply_log_max_per_chat')"
            type="number"
            min="100"
            variant="outlined"
            density="compact"
          />
        </v-col>

        <!-- LLM引用 -->
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.llm_quote"
            :label="tm('configSections.chat.llm_quote')"
            color="primary"
          />
        </v-col>

        <!-- 动态发言频率规则开关 -->
        <v-col cols="12" md="6">
          <v-switch
            v-model="localConfig.enable_talk_value_rules"
            :label="tm('configSections.chat.enable_talk_value_rules')"
            color="primary"
          />
        </v-col>
      </v-row>

      <!-- 动态发言频率规则 -->
      <v-expand-transition>
        <div v-if="localConfig.enable_talk_value_rules" class="mt-4">
          <v-divider class="mb-4" />
          <div class="text-subtitle-1 mb-2">
            {{ tm("configSections.chat.talk_value_rules") }}
          </div>

          <v-card
            v-for="(rule, index) in localConfig.talk_value_rules || []"
            :key="index"
            variant="outlined"
            class="mb-3 pa-3"
          >
            <v-row dense>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="rule.target"
                  :label="tm('configSections.chat.rule_target')"
                  variant="outlined"
                  density="compact"
                  :placeholder="
                    tm('configSections.chat.rule_target_placeholder')
                  "
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model="rule.time"
                  :label="tm('configSections.chat.rule_time')"
                  variant="outlined"
                  density="compact"
                  placeholder="00:00-23:59"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-text-field
                  v-model.number="rule.value"
                  :label="tm('configSections.chat.rule_value')"
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
              <v-col cols="12" md="3" class="d-flex align-center">
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  @click="removeRule(index)"
                />
              </v-col>
            </v-row>
          </v-card>

          <v-btn variant="outlined" size="small" @click="addRule">
            <v-icon start>mdi-plus</v-icon>
            {{ tm("configSections.chat.add_rule") }}
          </v-btn>
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

const thinkModes = [
  { title: "经典模式 (classic)", value: "classic" },
  { title: "深度模式 (deep)", value: "deep" },
  { title: "动态模式 (dynamic)", value: "dynamic" },
];

const localConfig = ref({
  talk_value: props.config?.talk_value ?? 1,
  mentioned_bot_reply: props.config?.mentioned_bot_reply ?? true,
  max_context_size: props.config?.max_context_size ?? 30,
  planner_smooth: props.config?.planner_smooth ?? 3,
  think_mode: props.config?.think_mode || "dynamic",
  plan_reply_log_max_per_chat:
    props.config?.plan_reply_log_max_per_chat ?? 1024,
  llm_quote: props.config?.llm_quote ?? false,
  enable_talk_value_rules: props.config?.enable_talk_value_rules ?? true,
  talk_value_rules: props.config?.talk_value_rules || [],
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

const addRule = () => {
  localConfig.value.talk_value_rules = [
    ...(localConfig.value.talk_value_rules || []),
    { target: "", time: "00:00-23:59", value: 1.0 },
  ];
};

const removeRule = (index: number) => {
  localConfig.value.talk_value_rules =
    localConfig.value.talk_value_rules.filter(
      (_: any, i: number) => i !== index,
    );
};
</script>
