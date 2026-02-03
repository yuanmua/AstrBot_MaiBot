<template>
  <v-container fluid class="py-6">
    <!-- 返回按钮和标题 -->
    <div class="d-flex align-center mb-4">
      <v-btn prepend-icon="mdi-arrow-left" @click="$router.back()" class="mr-4">
        {{ tm("dialog.create") }}
      </v-btn>
      <div>
        <h1 class="text-h5">{{ tm("dialog.create") }}</h1>
        <p class="text-grey text-caption">创建新实例并配置</p>
      </div>
    </div>

    <!-- 加载状态 -->
    <v-progress-linear
      v-if="loading"
      indeterminate
      class="mb-4"
    ></v-progress-linear>

    <!-- 错误提示 -->
    <v-alert
      v-if="error"
      type="error"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <v-row v-if="!loading">
      <!-- 左侧：基本信息表单 -->
      <v-col cols="12" md="3">
        <v-card class="mb-4">
          <v-card-title>{{ tm("instanceDetail.basicInfo") }}</v-card-title>
          <v-divider />
          <v-card-text>
            <v-form ref="formRef" @submit.prevent="handleCreate">
              <!-- 实例ID -->
              <v-text-field
                v-model="formData.instance_id"
                label="Instance ID"
                placeholder="e.g., my_bot"
                required
                :error-messages="formErrors.instance_id"
                class="mb-4"
                @blur="validateInstanceId"
              ></v-text-field>

              <!-- 实例名称 -->
              <v-text-field
                v-model="formData.name"
                :label="tm('instanceDetail.instanceName')"
                required
                :error-messages="formErrors.name"
                class="mb-4"
              ></v-text-field>

              <!-- 描述 -->
              <v-textarea
                v-model="formData.description"
                :label="tm('instanceDetail.description')"
                rows="2"
                class="mb-4"
              ></v-textarea>

              <!-- 端口 -->
              <v-text-field
                v-model.number="formData.port"
                :label="tm('instanceDetail.port')"
                type="number"
                min="1000"
                max="65535"
                class="mb-4"
              ></v-text-field>

              <!-- 功能开关 -->
              <v-checkbox
                v-model="formData.enable_webui"
                :label="tm('instanceDetail.enableWebui')"
              ></v-checkbox>

              <v-checkbox
                v-model="formData.enable_socket"
                :label="tm('instanceDetail.enableSocket')"
              ></v-checkbox>
            </v-form>
          </v-card-text>
        </v-card>

        <!-- 端口占用提示 -->
        <v-card>
          <v-card-title class="text-body-1">端口信息</v-card-title>
          <v-card-text>
            <div class="text-caption text-grey mb-2">已使用的端口：</div>
            <div v-if="usedPorts.length > 0" class="d-flex flex-wrap gap-1">
              <v-chip
                v-for="port in usedPorts"
                :key="port"
                size="small"
                :color="port === formData.port ? 'error' : 'default'"
                variant="outlined"
              >
                {{ port }}
              </v-chip>
            </div>
            <div v-else class="text-caption text-grey">暂无实例运行</div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：配置编辑区 -->
      <v-col cols="12" md="9">
        <!-- 配置区块导航 -->
        <v-card class="mb-4">
          <v-tabs v-model="activeSection" color="primary" show-arrows>
            <v-tab value="bot">
              <v-icon start size="small">mdi-robot</v-icon>
              {{ tm("configSections.bot.title") }}
            </v-tab>
            <v-tab value="personality">
              <v-icon start size="small">mdi-account-heart</v-icon>
              {{ tm("configSections.personality.title") }}
            </v-tab>
            <v-tab value="chat">
              <v-icon start size="small">mdi-chat</v-icon>
              {{ tm("configSections.chat.title") }}
            </v-tab>
            <v-tab value="expression">
              <v-icon start size="small">mdi-school</v-icon>
              {{ tm("configSections.expression.title") }}
            </v-tab>
            <v-tab value="memory">
              <v-icon start size="small">mdi-brain</v-icon>
              {{ tm("configSections.memory.title") }}
            </v-tab>
            <v-tab value="emoji">
              <v-icon start size="small">mdi-emoticon</v-icon>
              {{ tm("configSections.emoji.title") }}
            </v-tab>
            <v-tab value="log">
              <v-icon start size="small">mdi-log</v-icon>
              {{ tm("configSections.log.title") }}
            </v-tab>
            <v-tab value="debug">
              <v-icon start size="small">mdi-bug</v-icon>
              {{ tm("configSections.debug.title") }}
            </v-tab>
            <v-tab value="webui">
              <v-icon start size="small">mdi-web</v-icon>
              {{ tm("configSections.webui.title") }}
            </v-tab>
            <v-tab value="other">
              <v-icon start size="small">mdi-tune</v-icon>
              {{ tm("configSections.other.title") }}
            </v-tab>
          </v-tabs>
        </v-card>

        <!-- 配置内容 -->
        <v-window v-model="activeSection">
          <v-window-item value="bot">
            <BotSection
              :config="config.bot"
              @update:config="updateSection('bot', $event)"
            />
          </v-window-item>

          <v-window-item value="personality">
            <PersonalitySection
              :config="config.personality"
              @update:config="updateSection('personality', $event)"
            />
          </v-window-item>

          <v-window-item value="chat">
            <ChatSection
              :config="config.chat"
              @update:config="updateSection('chat', $event)"
            />
          </v-window-item>

          <v-window-item value="expression">
            <ExpressionSection
              :config="config.expression"
              @update:config="updateSection('expression', $event)"
            />
          </v-window-item>

          <v-window-item value="memory">
            <MemorySection
              :config="config.memory"
              @update:config="updateSection('memory', $event)"
            />
          </v-window-item>

          <v-window-item value="emoji">
            <EmojiSection
              :config="config.emoji"
              @update:config="updateSection('emoji', $event)"
            />
          </v-window-item>

          <v-window-item value="log">
            <LogSection
              :config="config.log"
              @update:config="updateSection('log', $event)"
            />
          </v-window-item>

          <v-window-item value="debug">
            <DebugSection
              :config="config.debug"
              @update:config="updateSection('debug', $event)"
            />
          </v-window-item>

          <v-window-item value="webui">
            <WebUISection
              :config="config.webui"
              @update:config="updateSection('webui', $event)"
            />
          </v-window-item>

          <v-window-item value="other">
            <OtherSection
              :config="otherConfig"
              @update:config="updateOtherSection($event)"
            />
          </v-window-item>
        </v-window>

        <!-- 底部操作栏 -->
        <v-card class="mt-4">
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn @click="$router.back()">
              {{ tm("dialog.cancel") }}
            </v-btn>
            <v-btn color="primary" @click="handleCreate" :loading="isCreating">
              {{ tm("dialog.confirm") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "@/utils/toast";
import { useInstances } from "@/composables/useInstances";
import { getDefaultTemplateConfig, createInstance } from "@/utils/maibotApi";
import { useModuleI18n } from "@/i18n/composables";
import {
  BotSection,
  PersonalitySection,
  ChatSection,
  ExpressionSection,
  MemorySection,
  EmojiSection,
  LogSection,
  DebugSection,
  WebUISection,
  OtherSection,
} from "./config-sections";

const { tm } = useModuleI18n("features/maibot");
const router = useRouter();
const { success, error: showError } = useToast();
const { instances, refreshInstances } = useInstances();

// 视图状态
const loading = ref(true);
const isCreating = ref(false);
const error = ref<string | null>(null);
const activeSection = ref("bot");
const formRef = ref();

// 表单数据
const formData = ref({
  instance_id: "",
  name: "",
  description: "",
  port: 8001,
  enable_webui: false,
  enable_socket: false,
});

const formErrors = reactive({
  instance_id: "",
  name: "",
});

// 配置数据
const config = ref<Record<string, any>>({});
const otherConfig = ref<Record<string, any>>({});

// 已使用的端口
const usedPorts = computed(() => {
  return instances.value.map((i) => i.port);
});

// 验证实例ID
const validateInstanceId = () => {
  const id = formData.value.instance_id;
  formErrors.instance_id = "";

  if (!id) {
    formErrors.instance_id = "实例ID不能为空";
    return false;
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(id)) {
    formErrors.instance_id = "实例ID只能包含字母、数字、下划线和连字符";
    return false;
  }

  if (instances.value.some((i) => i.id === id)) {
    formErrors.instance_id = "实例ID已存在";
    return false;
  }

  return true;
};

// 验证表单
const validateForm = () => {
  let valid = true;

  if (!formData.value.instance_id) {
    formErrors.instance_id = "实例ID不能为空";
    valid = false;
  }

  if (!formData.value.name) {
    formErrors.name = "名称不能为空";
    valid = false;
  }

  return valid;
};

// 更新配置节
const updateSection = (section: string, data: any) => {
  config.value[section] = data;
};

// 更新其他配置节
const updateOtherSection = (data: any) => {
  for (const [key, value] of Object.entries(data)) {
    otherConfig.value[key] = value;
    config.value[key] = value;
  }
};

// 将配置合并为 TOML（保留模板注释的合并逻辑）
const mergeConfigToToml = (sections: Record<string, any>) => {
  const toml: Record<string, any> = {
    inner: { version: "7.3.5" },
  };

  for (const [key, value] of Object.entries(sections)) {
    if (
      [
        "bot",
        "personality",
        "chat",
        "expression",
        "memory",
        "emoji",
        "log",
        "debug",
        "webui",
      ].includes(key)
    ) {
      toml[key] = value;
    } else if (
      [
        "message_receive",
        "keyword_reaction",
        "response_post_process",
        "chinese_typo",
        "response_splitter",
        "tool",
        "voice",
        "telemetry",
        "relationship",
      ].includes(key)
    ) {
      toml[key] = value;
    }
  }

  return toml;
};

// 加载默认配置
const loadDefaultConfig = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await getDefaultTemplateConfig();
    // 后端返回 {config: {...}} 结构，config 包含 inner, bot, personality 等
    const data = response?.config || response;
    if (data) {
      // 解析配置到各 section（从 config 中提取，不包含 inner）
      config.value = {
        bot: {
          platform: data.bot?.platform || "qq",
          qq_account: data.bot?.qq_account || "",
          nickname: data.bot?.nickname || "",
          platforms: data.bot?.platforms || [],
          alias_names: data.bot?.alias_names || [],
        },
        personality: {
          personality: data.personality?.personality || "",
          reply_style: data.personality?.reply_style || "",
          plan_style: data.personality?.plan_style || "",
          visual_style: data.personality?.visual_style || "",
          state_probability: data.personality?.state_probability ?? 0.3,
          states: data.personality?.states || [],
        },
        chat: {
          talk_value: data.chat?.talk_value ?? 1,
          mentioned_bot_reply: data.chat?.mentioned_bot_reply ?? true,
          max_context_size: data.chat?.max_context_size ?? 30,
          planner_smooth: data.chat?.planner_smooth ?? 3,
          think_mode: data.chat?.think_mode || "dynamic",
          plan_reply_log_max_per_chat:
            data.chat?.plan_reply_log_max_per_chat ?? 1024,
          llm_quote: data.chat?.llm_quote ?? false,
          enable_talk_value_rules: data.chat?.enable_talk_value_rules ?? true,
          talk_value_rules: data.chat?.talk_value_rules || [],
        },
        expression: {
          all_global_jargon: data.expression?.all_global_jargon ?? true,
          enable_jargon_explanation:
            data.expression?.enable_jargon_explanation ?? true,
          jargon_mode: data.expression?.jargon_mode || "planner",
          expression_checked_only:
            data.expression?.expression_checked_only ?? true,
          expression_self_reflect:
            data.expression?.expression_self_reflect ?? true,
          expression_manual_reflect:
            data.expression?.expression_manual_reflect ?? false,
          expression_auto_check_interval:
            data.expression?.expression_auto_check_interval ?? 600,
          expression_auto_check_count:
            data.expression?.expression_auto_check_count ?? 20,
          manual_reflect_operator_id:
            data.expression?.manual_reflect_operator_id || "",
          learning_list: data.expression?.learning_list || [
            ["", "enable", "enable", "enable"],
          ],
        },
        memory: {
          max_agent_iterations: data.memory?.max_agent_iterations ?? 5,
          agent_timeout_seconds: data.memory?.agent_timeout_seconds ?? 180.0,
          global_memory: data.memory?.global_memory ?? false,
          planner_question: data.memory?.planner_question ?? true,
          global_memory_blacklist: data.memory?.global_memory_blacklist || [],
        },
        emoji: {
          emoji_chance: data.emoji?.emoji_chance ?? 0.4,
          max_reg_num: data.emoji?.max_reg_num ?? 100,
          do_replace: data.emoji?.do_replace ?? true,
          check_interval: data.emoji?.check_interval ?? 10,
          steal_emoji: data.emoji?.steal_emoji ?? true,
          content_filtration: data.emoji?.content_filtration ?? false,
          filtration_prompt: data.emoji?.filtration_prompt || "符合公序良俗",
        },
        log: {
          date_style: data.log?.date_style || "m-d H:i:s",
          log_level_style: data.log?.log_level_style || "lite",
          color_text: data.log?.color_text || "full",
          log_level: data.log?.log_level || "INFO",
          console_log_level: data.log?.console_log_level || "INFO",
          file_log_level: data.log?.file_log_level || "DEBUG",
        },
        debug: {
          show_prompt: data.debug?.show_prompt ?? false,
          show_replyer_prompt: data.debug?.show_replyer_prompt ?? false,
          show_replyer_reasoning: data.debug?.show_replyer_reasoning ?? false,
          show_jargon_prompt: data.debug?.show_jargon_prompt ?? false,
          show_memory_prompt: data.debug?.show_memory_prompt ?? false,
          show_planner_prompt: data.debug?.show_planner_prompt ?? false,
          show_lpmm_paragraph: data.debug?.show_lpmm_paragraph ?? false,
        },
        webui: {
          enabled: data.webui?.enabled ?? true,
          mode: data.webui?.mode || "production",
          anti_crawler_mode: data.webui?.anti_crawler_mode || "loose",
          allowed_ips: data.webui?.allowed_ips || "127.0.0.1",
          trust_xff: data.webui?.trust_xff ?? false,
          secure_cookie: data.webui?.secure_cookie ?? false,
        },
      };

      // 其他配置
      otherConfig.value = {
        message_receive: {
          ban_words: data.message_receive?.ban_words || [],
          ban_msgs_regex: data.message_receive?.ban_msgs_regex || [],
        },
        keyword_reaction: {
          keyword_rules: data.keyword_reaction?.keyword_rules || [],
          regex_rules: data.keyword_reaction?.regex_rules || [],
        },
        response_post_process: {
          enable_response_post_process:
            data.response_post_process?.enable_response_post_process ?? true,
        },
        chinese_typo: {
          enable: data.chinese_typo?.enable ?? true,
          error_rate: data.chinese_typo?.error_rate ?? 0.01,
        },
        response_splitter: {
          enable: data.response_splitter?.enable ?? true,
          max_length: data.response_splitter?.max_length ?? 512,
        },
        tool: {
          enable_tool: data.tool?.enable_tool ?? true,
        },
        voice: {
          enable_asr: data.voice?.enable_asr ?? false,
        },
        telemetry: {
          enable: data.telemetry?.enable ?? true,
        },
        relationship: {
          enable_relationship: data.relationship?.enable_relationship ?? true,
        },
      };

      // 合并其他配置到主配置
      for (const [key, value] of Object.entries(otherConfig.value)) {
        config.value[key] = value;
      }
    }
  } catch (err: any) {
    error.value = err.message || "加载默认配置失败";
  } finally {
    loading.value = false;
  }
};

// 创建实例
const handleCreate = async () => {
  if (!validateForm()) {
    return;
  }

  isCreating.value = true;
  error.value = null;

  try {
    // 发送配置修改项，后端会与模板合并
    await createInstance({
      instance_id: formData.value.instance_id,
      name: formData.value.name,
      description: formData.value.description,
      port: formData.value.port,
      enable_webui: formData.value.enable_webui,
      enable_socket: formData.value.enable_socket,
      config_updates: mergeConfigToToml(config.value),
    });

    success("实例创建成功！", { type: "success" });

    // 刷新实例列表并返回
    await refreshInstances();
    router.push("/maibot");
  } catch (err: any) {
    error.value = err.message || "创建实例失败";
  } finally {
    isCreating.value = false;
  }
};

// 初始化
onMounted(async () => {
  await refreshInstances();
  await loadDefaultConfig();
});
</script>
