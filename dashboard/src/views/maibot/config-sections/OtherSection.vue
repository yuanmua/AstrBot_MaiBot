<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-tune</v-icon>
      {{ tm("configSections.other.title") }}
    </v-card-title>
    <v-divider />
    <v-card-text>
      <v-expansion-panels variant="accordion">
        <!-- 消息接收过滤 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-message-filter</v-icon>
            {{ tm("configSections.other.message_receive") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-row>
              <v-col cols="12">
                <v-combobox
                  v-model="localConfig.message_receive.ban_words"
                  :label="tm('configSections.other.ban_words')"
                  variant="outlined"
                  density="compact"
                  multiple
                  chips
                  closable-chips
                />
              </v-col>
              <v-col cols="12">
                <v-combobox
                  v-model="localConfig.message_receive.ban_msgs_regex"
                  :label="tm('configSections.other.ban_msgs_regex')"
                  variant="outlined"
                  density="compact"
                  multiple
                  chips
                  closable-chips
                />
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 关键词回复 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-keyword</v-icon>
            {{ tm("configSections.other.keyword_reaction") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="text-subtitle-2 mb-2">
              {{ tm("configSections.other.keyword_rules") }}
            </div>
            <v-card
              v-for="(rule, index) in localConfig.keyword_reaction
                .keyword_rules || []"
              :key="index"
              variant="outlined"
              class="mb-3 pa-3"
            >
              <v-row dense>
                <v-col cols="12">
                  <v-combobox
                    v-model="rule.keywords"
                    :label="tm('configSections.other.keywords')"
                    variant="outlined"
                    density="compact"
                    multiple
                    chips
                    closable-chips
                  />
                </v-col>
                <v-col cols="12">
                  <v-textarea
                    v-model="rule.reaction"
                    :label="tm('configSections.other.reaction')"
                    variant="outlined"
                    density="compact"
                    rows="2"
                  />
                </v-col>
                <v-col cols="12" class="text-right">
                  <v-btn
                    size="small"
                    color="error"
                    variant="text"
                    @click="removeKeywordRule(index)"
                  >
                    {{ tm("common.delete") }}
                  </v-btn>
                </v-col>
              </v-row>
            </v-card>
            <v-btn variant="outlined" size="small" @click="addKeywordRule">
              <v-icon start>mdi-plus</v-icon>
              {{ tm("common.add") }}
            </v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 回复后处理 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-post</v-icon>
            {{ tm("configSections.other.response_post_process") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-switch
              v-model="
                localConfig.response_post_process.enable_response_post_process
              "
              :label="tm('configSections.other.enable')"
              color="primary"
            />

            <!-- 中文错别字 -->
            <div class="text-subtitle-2 mt-3 mb-2">
              {{ tm("configSections.other.chinese_typo") }}
            </div>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="localConfig.chinese_typo.enable"
                  :label="tm('configSections.other.enable')"
                  color="primary"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="localConfig.chinese_typo.error_rate"
                  :label="tm('configSections.other.error_rate')"
                  type="number"
                  step="0.001"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
            </v-row>

            <!-- 回复分割器 -->
            <div class="text-subtitle-2 mt-3 mb-2">
              {{ tm("configSections.other.response_splitter") }}
            </div>
            <v-row>
              <v-col cols="12" md="6">
                <v-switch
                  v-model="localConfig.response_splitter.enable"
                  :label="tm('configSections.other.enable')"
                  color="primary"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-text-field
                  v-model.number="localConfig.response_splitter.max_length"
                  :label="tm('configSections.other.max_length')"
                  type="number"
                  variant="outlined"
                  density="compact"
                />
              </v-col>
            </v-row>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 工具 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-toolbox</v-icon>
            {{ tm("configSections.other.tool") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-switch
              v-model="localConfig.tool.enable_tool"
              :label="tm('configSections.other.enable_tool')"
              color="primary"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 语音识别 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-microphone</v-icon>
            {{ tm("configSections.other.voice") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-switch
              v-model="localConfig.voice.enable_asr"
              :label="tm('configSections.other.enable_asr')"
              color="primary"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 遥测 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-chart-bar</v-icon>
            {{ tm("configSections.other.telemetry") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-switch
              v-model="localConfig.telemetry.enable"
              :label="tm('configSections.other.enable')"
              color="primary"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>

        <!-- 关系系统 -->
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-account-group</v-icon>
            {{ tm("configSections.other.relationship") }}
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <v-switch
              v-model="localConfig.relationship.enable_relationship"
              :label="tm('configSections.other.enable_relationship')"
              color="primary"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
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
  message_receive: {
    ban_words: props.config?.message_receive?.ban_words || [],
    ban_msgs_regex: props.config?.message_receive?.ban_msgs_regex || [],
  },
  keyword_reaction: {
    keyword_rules: props.config?.keyword_reaction?.keyword_rules || [],
    regex_rules: props.config?.keyword_reaction?.regex_rules || [],
  },
  response_post_process: {
    enable_response_post_process:
      props.config?.response_post_process?.enable_response_post_process ?? true,
  },
  chinese_typo: {
    enable: props.config?.chinese_typo?.enable ?? true,
    error_rate: props.config?.chinese_typo?.error_rate ?? 0.01,
  },
  response_splitter: {
    enable: props.config?.response_splitter?.enable ?? true,
    max_length: props.config?.response_splitter?.max_length ?? 512,
  },
  tool: {
    enable_tool: props.config?.tool?.enable_tool ?? true,
  },
  voice: {
    enable_asr: props.config?.voice?.enable_asr ?? false,
  },
  telemetry: {
    enable: props.config?.telemetry?.enable ?? true,
  },
  relationship: {
    enable_relationship:
      props.config?.relationship?.enable_relationship ?? true,
  },
});

watch(
  localConfig,
  (newConfig) => {
    emit("update:config", newConfig);
  },
  { deep: true },
);

const addKeywordRule = () => {
  localConfig.value.keyword_reaction.keyword_rules = [
    ...(localConfig.value.keyword_reaction.keyword_rules || []),
    { keywords: [], reaction: "" },
  ];
};

const removeKeywordRule = (index: number) => {
  localConfig.value.keyword_reaction.keyword_rules =
    localConfig.value.keyword_reaction.keyword_rules.filter(
      (_: any, i: number) => i !== index,
    );
};
</script>
