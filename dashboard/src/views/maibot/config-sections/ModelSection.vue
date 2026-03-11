<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-brain</v-icon>
      {{ tm("configSections.model.title") }}
    </v-card-title>
    <v-divider />

    <v-card-text>
      <!-- 加载状态 -->
      <v-progress-linear v-if="loading" indeterminate class="mb-4"></v-progress-linear>

      <!-- 错误提示 -->
      <v-alert v-if="error" type="error" class="mb-4" closable @click:close="error = null">
        {{ error }}
      </v-alert>

      <template v-if="!loading">
        <!-- API 服务商配置 -->
        <div class="mb-6">
          <div class="d-flex align-center mb-3">
            <div class="text-h6">API 服务商</div>
            <v-spacer></v-spacer>
            <v-btn color="primary" size="small" @click="addApiProvider">
              <v-icon start>mdi-plus</v-icon>
              添加服务商
            </v-btn>
          </div>

          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel
              v-for="(provider, index) in localConfig.api_providers || []"
              :key="'provider-' + index"
            >
              <v-expansion-panel-title>
                <div class="d-flex align-center flex-grow-1">
                  <v-icon start color="primary">mdi-cloud</v-icon>
                  <span class="font-weight-bold">{{ provider.name }}</span>
                  <v-chip size="x-small" class="ml-2" color="grey">
                    {{ provider.client_type }}
                  </v-chip>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="provider.name"
                      label="服务商名称"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="provider.client_type"
                      label="客户端类型"
                      :items="['openai', 'gemini', 'anthropic']"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12">
                    <v-text-field
                      v-model="provider.base_url"
                      label="Base URL"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12">
                    <v-text-field
                      v-model="provider.api_key"
                      label="API Key"
                      variant="outlined"
                      density="compact"
                      :type="showApiKeys[index] ? 'text' : 'password'"
                      :append-inner-icon="showApiKeys[index] ? 'mdi-eye-off' : 'mdi-eye'"
                      @click:append-inner="toggleApiKey(index)"
                    />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field
                      v-model.number="provider.max_retry"
                      label="最大重试次数"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field
                      v-model.number="provider.timeout"
                      label="超时时间(秒)"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field
                      v-model.number="provider.retry_interval"
                      label="重试间隔(秒)"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" md="3" class="d-flex align-center">
                    <v-btn
                      color="error"
                      variant="text"
                      @click="removeApiProvider(index)"
                    >
                      <v-icon start>mdi-delete</v-icon>
                      删除
                    </v-btn>
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <div v-if="!localConfig.api_providers?.length" class="text-grey text-center py-4">
            暂无 API 服务商配置
          </div>
        </div>

        <!-- 模型配置 -->
        <div class="mb-6">
          <div class="d-flex align-center mb-3">
            <div class="text-h6">模型配置</div>
            <v-spacer></v-spacer>
            <v-btn color="primary" size="small" @click="addModel">
              <v-icon start>mdi-plus</v-icon>
              添加模型
            </v-btn>
          </div>

          <v-expansion-panels variant="accordion">
            <v-expansion-panel
              v-for="(model, index) in localConfig.models || []"
              :key="'model-' + index"
            >
              <v-expansion-panel-title>
                <div class="d-flex align-center flex-grow-1">
                  <v-icon start color="success">mdi-robot</v-icon>
                  <span class="font-weight-bold">{{ model.name }}</span>
                  <v-chip size="x-small" class="ml-2" color="blue">
                    {{ model.api_provider }}
                  </v-chip>
                </div>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="model.model_identifier"
                      label="模型标识符"
                      variant="outlined"
                      density="compact"
                      hint="API 服务商提供的模型标识符"
                      persistent-hint
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="model.name"
                      label="模型名称"
                      variant="outlined"
                      density="compact"
                      hint="在麦麦中使用的名称"
                      persistent-hint
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-select
                      v-model="model.api_provider"
                      label="API 服务商"
                      :items="providerNames"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field
                      v-model.number="model.price_in"
                      label="输入价格(元/M)"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6" md="3">
                    <v-text-field
                      v-model.number="model.price_out"
                      label="输出价格(元/M)"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-switch
                      v-model="model.force_stream_mode"
                      label="强制流式输出"
                      color="primary"
                      density="compact"
                      hide-details
                    />
                  </v-col>
                  <v-col cols="12">
                    <div class="text-subtitle-2 mb-2">额外参数</div>
                    <v-row dense>
                      <v-col cols="6" md="3">
                        <v-switch
                          v-model="model.extra_params.enable_thinking"
                          label="启用思考"
                          color="primary"
                          density="compact"
                          hide-details
                        />
                      </v-col>
                    </v-row>
                  </v-col>
                  <v-col cols="12" class="d-flex justify-end">
                    <v-btn color="error" variant="text" @click="removeModel(index)">
                      <v-icon start>mdi-delete</v-icon>
                      删除模型
                    </v-btn>
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>

          <div v-if="!localConfig.models?.length" class="text-grey text-center py-4">
            暂无模型配置
          </div>
        </div>

        <!-- 任务模型配置 -->
        <div>
          <div class="text-h6 mb-3">任务模型配置</div>

          <v-row>
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <div class="text-subtitle-1 font-weight-bold mb-2">工具调用模型</div>
                <v-select
                  v-model="localConfig.model_task_config.tool_use.model_list"
                  label="使用的模型"
                  :items="modelNames"
                  multiple
                  chips
                  variant="outlined"
                  density="compact"
                />
                <v-row dense>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.tool_use.temperature"
                      label="温度"
                      type="number"
                      step="0.1"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.tool_use.max_tokens"
                      label="最大Token"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-card>
            </v-col>

            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <div class="text-subtitle-1 font-weight-bold mb-2">回复模型</div>
                <v-select
                  v-model="localConfig.model_task_config.replyer.model_list"
                  label="使用的模型"
                  :items="modelNames"
                  multiple
                  chips
                  variant="outlined"
                  density="compact"
                />
                <v-row dense>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.replyer.temperature"
                      label="温度"
                      type="number"
                      step="0.1"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.replyer.max_tokens"
                      label="最大Token"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-card>
            </v-col>

            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <div class="text-subtitle-1 font-weight-bold mb-2">决策模型</div>
                <v-select
                  v-model="localConfig.model_task_config.planner.model_list"
                  label="使用的模型"
                  :items="modelNames"
                  multiple
                  chips
                  variant="outlined"
                  density="compact"
                />
                <v-row dense>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.planner.temperature"
                      label="温度"
                      type="number"
                      step="0.1"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.planner.max_tokens"
                      label="最大Token"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-card>
            </v-col>

            <v-col cols="12" md="6">
              <v-card variant="outlined" class="pa-3">
                <div class="text-subtitle-1 font-weight-bold mb-2">图像识别模型</div>
                <v-select
                  v-model="localConfig.model_task_config.vlm.model_list"
                  label="使用的模型"
                  :items="modelNames"
                  multiple
                  chips
                  variant="outlined"
                  density="compact"
                />
                <v-row dense>
                  <v-col cols="6">
                    <v-text-field
                      v-model.number="localConfig.model_task_config.vlm.max_tokens"
                      label="最大Token"
                      type="number"
                      variant="outlined"
                      density="compact"
                    />
                  </v-col>
                </v-row>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </template>
    </v-card-text>

    <v-divider v-if="hasChanges" />

    <v-card-actions v-if="hasChanges" class="pa-4">
      <v-chip color="warning" variant="outlined" size="small">
        <v-icon start size="small">mdi-alert</v-icon>
        {{ tm("instanceDetail.unsaved") }}
      </v-chip>
      <v-spacer />
      <v-btn @click="resetConfig">
        {{ tm("dialog.cancel") }}
      </v-btn>
      <v-btn color="primary" @click="saveConfig" :loading="saving">
        {{ tm("dialog.save") }}
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useToast } from "@/utils/toast";
import { useModuleI18n } from "@/i18n/composables";
import { getModelConfig, saveModelConfig } from "@/utils/maibotApi";

const { tm } = useModuleI18n("features/maibot");
const { success, error: showError } = useToast();

// 状态
const loading = ref(false);
const saving = ref(false);
const error = ref<string | null>(null);
const showApiKeys = ref<Record<number, boolean>>({});

// 配置数据
const localConfig = ref<Record<string, any>>({
  api_providers: [],
  models: [],
  model_task_config: {
    utils: { model_list: [], temperature: 0.2, max_tokens: 4096 },
    tool_use: { model_list: [], temperature: 0.7, max_tokens: 1024 },
    replyer: { model_list: [], temperature: 0.3, max_tokens: 2048 },
    planner: { model_list: [], temperature: 0.3, max_tokens: 800 },
    vlm: { model_list: [], max_tokens: 256 },
    voice: { model_list: [] },
    embedding: { model_list: [] },
    lpmm_entity_extract: { model_list: [], temperature: 0.2, max_tokens: 800 },
    lpmm_rdf_build: { model_list: [], temperature: 0.2, max_tokens: 800 },
  },
});

const originalConfig = ref<Record<string, any>>({});

// 计算属性
const hasChanges = computed(() => {
  return JSON.stringify(localConfig.value) !== JSON.stringify(originalConfig.value);
});

const providerNames = computed(() => {
  return (localConfig.value.api_providers || []).map((p: any) => p.name);
});

const modelNames = computed(() => {
  return (localConfig.value.models || []).map((m: any) => m.name);
});

// 方法
const toggleApiKey = (index: number) => {
  showApiKeys.value[index] = !showApiKeys.value[index];
};

const addApiProvider = () => {
  if (!localConfig.value.api_providers) {
    localConfig.value.api_providers = [];
  }
  localConfig.value.api_providers.push({
    name: "新服务商",
    base_url: "https://api.example.com/v1",
    api_key: "",
    client_type: "openai",
    max_retry: 2,
    timeout: 120,
    retry_interval: 5,
  });
};

const removeApiProvider = (index: number) => {
  localConfig.value.api_providers.splice(index, 1);
};

const addModel = () => {
  if (!localConfig.value.models) {
    localConfig.value.models = [];
  }
  localConfig.value.models.push({
    model_identifier: "",
    name: "新模型",
    api_provider: providerNames.value[0] || "",
    price_in: 0,
    price_out: 0,
    extra_params: {
      enable_thinking: false,
    },
  });
};

const removeModel = (index: number) => {
  localConfig.value.models.splice(index, 1);
};

const resetConfig = () => {
  localConfig.value = JSON.parse(JSON.stringify(originalConfig.value));
};

const saveConfig = async () => {
  saving.value = true;
  error.value = null;

  try {
    // 转换为 TOML 格式
    const tomlContent = configToToml(localConfig.value);
    await saveModelConfig(tomlContent);
    success("模型配置已保存", { type: "success" });
    originalConfig.value = JSON.parse(JSON.stringify(localConfig.value));
  } catch (err: any) {
    error.value = err.message || "保存配置失败";
  } finally {
    saving.value = false;
  }
};

// 将配置对象转换为 TOML 字符串
const configToToml = (config: Record<string, any>): string => {
  let toml = `[inner]
version = "${config.inner?.version || '1.11.0'}"

`;

  // API 服务商
  if (config.api_providers?.length) {
    for (const provider of config.api_providers) {
      toml += `[[api_providers]]
name = "${escapeTomlString(provider.name)}"
base_url = "${escapeTomlString(provider.base_url)}"
api_key = "${escapeTomlString(provider.api_key)}"
client_type = "${provider.client_type || 'openai'}"
max_retry = ${provider.max_retry || 2}
timeout = ${provider.timeout || 120}
retry_interval = ${provider.retry_interval || 5}

`;
    }
  }

  // 模型
  if (config.models?.length) {
    for (const model of config.models) {
      toml += `[[models]]
model_identifier = "${escapeTomlString(model.model_identifier)}"
name = "${escapeTomlString(model.name)}"
api_provider = "${escapeTomlString(model.api_provider)}"
price_in = ${model.price_in || 0}
price_out = ${model.price_out || 0}
`;
      if (model.force_stream_mode) {
        toml += `force_stream_mode = true
`;
      }
      if (model.extra_params?.enable_thinking) {
        toml += `[models.extra_params]
enable_thinking = true
`;
      }
      toml += "\n";
    }
  }

  // 任务配置
  const taskConfig = config.model_task_config;
  if (taskConfig) {
    // Utils
    if (taskConfig.utils) {
      toml += `[model_task_config.utils]
model_list = [${taskConfig.utils.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.utils.temperature || 0.2}
max_tokens = ${taskConfig.utils.max_tokens || 4096}
slow_threshold = ${taskConfig.utils.slow_threshold || 15.0}
selection_strategy = "${taskConfig.utils.selection_strategy || 'random'}"

`;
    }

    // Tool use
    if (taskConfig.tool_use) {
      toml += `[model_task_config.tool_use]
model_list = [${taskConfig.tool_use.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.tool_use.temperature || 0.7}
max_tokens = ${taskConfig.tool_use.max_tokens || 1024}
slow_threshold = ${taskConfig.tool_use.slow_threshold || 10.0}
selection_strategy = "${taskConfig.tool_use.selection_strategy || 'random'}"

`;
    }

    // Replyer
    if (taskConfig.replyer) {
      toml += `[model_task_config.replyer]
model_list = [${taskConfig.replyer.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.replyer.temperature || 0.3}
max_tokens = ${taskConfig.replyer.max_tokens || 2048}
slow_threshold = ${taskConfig.replyer.slow_threshold || 25.0}
selection_strategy = "${taskConfig.replyer.selection_strategy || 'random'}"

`;
    }

    // Planner
    if (taskConfig.planner) {
      toml += `[model_task_config.planner]
model_list = [${taskConfig.planner.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.planner.temperature || 0.3}
max_tokens = ${taskConfig.planner.max_tokens || 800}
slow_threshold = ${taskConfig.planner.slow_threshold || 12.0}
selection_strategy = "${taskConfig.planner.selection_strategy || 'random'}"

`;
    }

    // VLM
    if (taskConfig.vlm) {
      toml += `[model_task_config.vlm]
model_list = [${taskConfig.vlm.model_list.map((m: string) => `"${m}"`).join(", ")}]
max_tokens = ${taskConfig.vlm.max_tokens || 256}
slow_threshold = ${taskConfig.vlm.slow_threshold || 15.0}
selection_strategy = "${taskConfig.vlm.selection_strategy || 'random'}"

`;
    }

    // Voice
    if (taskConfig.voice) {
      toml += `[model_task_config.voice]
model_list = [${taskConfig.voice.model_list.map((m: string) => `"${m}"`).join(", ")}]
slow_threshold = ${taskConfig.voice.slow_threshold || 12.0}
selection_strategy = "${taskConfig.voice.selection_strategy || 'random'}"

`;
    }

    // Embedding
    if (taskConfig.embedding) {
      toml += `[model_task_config.embedding]
model_list = [${taskConfig.embedding.model_list.map((m: string) => `"${m}"`).join(", ")}]
slow_threshold = ${taskConfig.embedding.slow_threshold || 5.0}
selection_strategy = "${taskConfig.embedding.selection_strategy || 'random'}"

`;
    }

    // LPMM 模型
    if (taskConfig.lpmm_entity_extract) {
      toml += `[model_task_config.lpmm_entity_extract]
model_list = [${taskConfig.lpmm_entity_extract.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.lpmm_entity_extract.temperature || 0.2}
max_tokens = ${taskConfig.lpmm_entity_extract.max_tokens || 800}
slow_threshold = ${taskConfig.lpmm_entity_extract.slow_threshold || 20.0}
selection_strategy = "${taskConfig.lpmm_entity_extract.selection_strategy || 'random'}"

`;
    }

    if (taskConfig.lpmm_rdf_build) {
      toml += `[model_task_config.lpmm_rdf_build]
model_list = [${taskConfig.lpmm_rdf_build.model_list.map((m: string) => `"${m}"`).join(", ")}]
temperature = ${taskConfig.lpmm_rdf_build.temperature || 0.2}
max_tokens = ${taskConfig.lpmm_rdf_build.max_tokens || 800}
slow_threshold = ${taskConfig.lpmm_rdf_build.slow_threshold || 20.0}
selection_strategy = "${taskConfig.lpmm_rdf_build.selection_strategy || 'random'}"
`;
    }
  }

  return toml;
};

const escapeTomlString = (str: string): string => {
  if (!str) return "";
  return str
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r");
};

// 加载配置
const loadConfig = async () => {
  loading.value = true;
  error.value = null;

  try {
    const result = await getModelConfig();
    if (result.config && Object.keys(result.config).length > 0) {
      localConfig.value = result.config;
      originalConfig.value = JSON.parse(JSON.stringify(result.config));
    }
  } catch (err: any) {
    error.value = err.message || "加载配置失败";
  } finally {
    loading.value = false;
  }
};

// 初始化
onMounted(() => {
  loadConfig();
});

// 暴露给父组件
defineExpose({
  loadConfig,
});
</script>
