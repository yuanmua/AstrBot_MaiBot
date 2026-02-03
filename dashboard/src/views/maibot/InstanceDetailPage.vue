<template>
  <v-container fluid class="py-6">
    <!-- 返回按钮和标题 -->
    <div class="d-flex align-center mb-4">
      <v-btn prepend-icon="mdi-arrow-left" @click="$router.back()" class="mr-4">
        {{ tm("instanceDetail.back") }}
      </v-btn>
      <div>
        <h1 class="text-h5">{{ currentInstance?.name || instanceId }}</h1>
        <p class="text-grey text-caption">
          {{ tm("instanceDetail.editConfig") }}
        </p>
      </div>
      <v-spacer />
      <!-- 重启按钮 -->
      <v-btn
        v-if="currentInstance?.status === 'running'"
        color="warning"
        variant="outlined"
        prepend-icon="mdi-restart"
        @click="handleRestart"
        :loading="restartLoading"
      >
        {{ tm("instanceDetail.restart") }}
      </v-btn>
    </div>

    <!-- 加载状态 -->
    <v-progress-linear
      v-if="loading || configLoading"
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

    <v-row v-if="currentInstance">
      <!-- 左侧：实例信息卡片 -->
      <v-col cols="12" md="3">
        <v-card class="mb-4">
          <v-card-title>{{ tm("instanceDetail.instanceInfo") }}</v-card-title>
          <v-card-text>
            <div class="mb-3">
              <div class="text-caption text-grey">
                {{ tm("instanceDetail.status") }}
              </div>
              <div class="d-flex align-center gap-2 mt-1">
                <v-chip
                  :color="getStatusColor(currentInstance.status)"
                  size="small"
                >
                  {{ getStatusText(currentInstance.status) }}
                </v-chip>
              </div>
            </div>

            <v-divider class="my-3"></v-divider>

            <div>
              <div class="text-caption text-grey">
                {{ tm("instanceDetail.basicInfo") }}
              </div>
              <div class="text-sm mt-2">
                <div class="d-flex justify-space-between py-1">
                  <span>ID:</span>
                  <span class="font-weight-bold">{{ currentInstance.id }}</span>
                </div>
                <div class="d-flex justify-space-between py-1">
                  <span>{{ tm("instanceDetail.port") }}:</span>
                  <span>{{ currentInstance.port }}</span>
                </div>
                <div class="d-flex justify-space-between py-1">
                  <span>{{ tm("instanceDetail.createdAt") }}:</span>
                  <span>{{ formatDate(currentInstance.created_at) }}</span>
                </div>
              </div>
            </div>

            <v-divider class="my-3"></v-divider>

            <!-- 操作按钮 -->
            <div class="d-flex gap-2 flex-wrap">
              <v-btn
                v-if="currentInstance.status === 'stopped'"
                size="small"
                color="success"
                @click="handleStart"
                :loading="operationLoading"
              >
                {{ tm("operations.start") }}
              </v-btn>
              <v-btn
                v-else-if="currentInstance.status === 'running'"
                size="small"
                color="error"
                @click="handleStop"
                :loading="operationLoading"
              >
                {{ tm("operations.stop") }}
              </v-btn>
              <v-btn
                size="small"
                variant="outlined"
                @click="handleRefresh"
                :loading="loading || configLoading"
              >
                {{ tm("instanceDetail.refresh") }}
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- 配置快捷操作 -->
        <v-card>
          <v-card-title>{{ tm("instanceDetail.quickActions") }}</v-card-title>
          <v-card-text>
            <v-btn
              block
              variant="tonal"
              color="info"
              class="mb-2"
              @click="resetConfig"
              :disabled="!originalConfig || isConfigChanged"
            >
              <v-icon start>mdi-restore</v-icon>
              {{ tm("instanceDetail.resetConfig") }}
            </v-btn>
            <v-btn
              block
              variant="tonal"
              @click="copyConfig"
              :disabled="!rawConfig"
            >
              <v-icon start>mdi-content-copy</v-icon>
              {{ tm("instanceDetail.copyConfig") }}
            </v-btn>
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
          <v-window-item v-if="config.bot" value="bot">
            <BotSection
              :config="config.bot"
              @update:config="updateSection('bot', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.personality" value="personality">
            <PersonalitySection
              :config="config.personality"
              @update:config="updateSection('personality', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.chat" value="chat">
            <ChatSection
              :config="config.chat"
              @update:config="updateSection('chat', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.expression" value="expression">
            <ExpressionSection
              :config="config.expression"
              @update:config="updateSection('expression', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.memory" value="memory">
            <MemorySection
              :config="config.memory"
              @update:config="updateSection('memory', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.emoji" value="emoji">
            <EmojiSection
              :config="config.emoji"
              @update:config="updateSection('emoji', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.log" value="log">
            <LogSection
              :config="config.log"
              @update:config="updateSection('log', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.debug" value="debug">
            <DebugSection
              :config="config.debug"
              @update:config="updateSection('debug', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.webui" value="webui">
            <WebUISection
              :config="config.webui"
              @update:config="updateSection('webui', $event)"
            />
          </v-window-item>

          <v-window-item v-if="config.message_receive" value="other">
            <OtherSection
              :config="config"
              @update:config="updateOtherSection($event)"
            />
          </v-window-item>
        </v-window>

        <!-- 底部操作栏 -->
        <v-card class="mt-4">
          <v-card-actions class="pa-4">
            <v-chip
              v-if="isConfigChanged"
              color="warning"
              variant="outlined"
              size="small"
            >
              <v-icon start size="small">mdi-alert</v-icon>
              {{ tm("instanceDetail.unsaved") }}
            </v-chip>
            <v-spacer />
            <v-btn @click="$router.back()">
              {{ tm("dialog.cancel") }}
            </v-btn>
            <v-btn
              color="primary"
              @click="handleSave"
              :loading="isSaving"
              :disabled="!isConfigChanged"
            >
              {{ tm("dialog.save") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- 无实例状态 -->
    <v-empty-state
      v-else-if="!loading && !configLoading"
      :headline="tm('instanceDetail.instanceNotFound')"
      :text="tm('instanceDetail.instanceNotFoundDesc')"
      icon="mdi-robot"
    >
      <template #actions>
        <v-btn @click="$router.back()">{{
          tm("instanceDetail.backToList")
        }}</v-btn>
      </template>
    </v-empty-state>

    <!-- 重启确认对话框 -->
    <v-dialog v-model="showRestartDialog" max-width="400">
      <v-card>
        <v-card-title>{{
          tm("instanceDetail.restartConfirmTitle")
        }}</v-card-title>
        <v-card-text>{{
          tm("instanceDetail.restartConfirmMessage")
        }}</v-card-text>
        <v-card-actions>
          <v-btn @click="showRestartDialog = false">{{
            tm("dialog.cancel")
          }}</v-btn>
          <v-btn
            color="warning"
            @click="confirmRestart"
            :loading="restartLoading"
          >
            {{ tm("instanceDetail.restart") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 保存成功对话框 -->
    <v-dialog v-model="showSaveSuccessDialog" max-width="400">
      <v-card>
        <v-card-title>{{ tm("instanceDetail.saveSuccessTitle") }}</v-card-title>
        <v-card-text>{{ tm("instanceDetail.saveSuccessMessage") }}</v-card-text>
        <v-card-actions>
          <v-btn @click="showSaveSuccessDialog = false">{{
            tm("instanceDetail.later")
          }}</v-btn>
          <v-btn
            color="warning"
            @click="handleSaveSuccessRestart"
            :loading="restartLoading"
          >
            {{ tm("instanceDetail.restartNow") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "@/utils/toast";
import { useModuleI18n } from "@/i18n/composables";
import { useInstances } from "@/composables/useInstances";
import { getInstanceConfig, saveInstanceConfig } from "@/utils/maibotApi";
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

const route = useRoute();
const { success: success, error: showError } = useToast();

const {
  instances,
  loading,
  instanceErrors,
  refreshInstances,
  startInstanceAsync,
  stopInstanceAsync,
  restartInstanceAsync,
} = useInstances();

const instanceId = route.params.id as string;

// 视图状态
const activeSection = ref("bot");
const configLoading = ref(false);
const isSaving = ref(false);
const operationLoading = ref(false);
const restartLoading = ref(false);
const error = ref<string | null>(null);

// 配置数据
const config = ref<Record<string, any>>({});
const originalConfig = ref<Record<string, any>>({});
// 追踪每个 section 的原始值，用于计算差异
const originalSectionConfigs = ref<Record<string, any>>({});
const rawConfig = ref("");

// 对话框状态
const showRestartDialog = ref(false);
const showSaveSuccessDialog = ref(false);

// 当前实例
const currentInstance = computed(() => {
  return instances.value.find((i) => i.id === instanceId);
});

// 配置是否已修改
const isConfigChanged = computed(() => {
  return JSON.stringify(config.value) !== JSON.stringify(originalConfig.value);
});

// 将后端配置数据转换为前端配置结构
const parseConfigToSections = (data: Record<string, any>) => {
  const sections = {
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
      state_probability: data.personality?.state_probability || 0.3,
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
      expression_checked_only: data.expression?.expression_checked_only ?? true,
      expression_self_reflect: data.expression?.expression_self_reflect ?? true,
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
    // 其他配置
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

  // 保存每个 section 的原始值副本
  for (const [key, value] of Object.entries(sections)) {
    originalSectionConfigs.value[key] = JSON.parse(JSON.stringify(value));
  }

  return sections;
};

// 更新配置节
const updateSection = (section: string, data: any) => {
  config.value[section] = data;
};

// 更新其他配置节
const updateOtherSection = (data: any) => {
  for (const [key, value] of Object.entries(data)) {
    config.value[key] = value;
  }
};

// 将配置合并回 TOML 格式
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

// 计算两个 section 的差异，返回修改过的 section 配置
const getChangedSections = () => {
  const changedSections: Record<string, any> = {};

  for (const [key, currentValue] of Object.entries(config.value)) {
    const originalValue = originalSectionConfigs.value[key];
    if (JSON.stringify(currentValue) !== JSON.stringify(originalValue)) {
      changedSections[key] = currentValue;
    }
  }

  return changedSections;
};

// 将 section 配置转换为 TOML 字符串（只包含修改的部分）
const sectionsToToml = (sections: Record<string, any>) => {
  let toml = `[inner]
version = "7.3.5"

`;

  for (const [key, value] of Object.entries(sections)) {
    toml += `[${key}]\n`;
    toml += objectToToml(value, "  ");
  }

  return toml;
};

// 将对象转换为 TOML 字符串
const objectToToml = (obj: any, indent: string = ""): string => {
  let toml = "";

  for (const [key, value] of Object.entries(obj)) {
    if (key === "version") continue;

    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      toml += `\n[${key}]\n`;
      toml += objectToToml(value, indent + "  ");
    } else if (Array.isArray(value)) {
      if (value.length > 0 && typeof value[0] === "object") {
        for (const item of value) {
          toml += `[[${key}]]\n`;
          toml += objectToToml(item, indent + "  ");
        }
      } else {
        const items = value.map((v: any) => {
          if (typeof v === "string") return `"${escapeTomlString(v)}"`;
          return String(v);
        });
        toml += `${key} = [${items.join(", ")}]\n`;
      }
    } else {
      if (typeof value === "string") {
        if (value.includes("\n")) {
          toml += `${key} = """\n${value}\n"""\n`;
        } else {
          toml += `${key} = "${escapeTomlString(value)}"\n`;
        }
      } else if (typeof value === "boolean") {
        toml += `${key} = ${value}\n`;
      } else {
        toml += `${key} = ${value}\n`;
      }
    }
  }

  return toml;
};

// 转义 TOML 字符串中的特殊字符
const escapeTomlString = (str: string): string => {
  return str
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\x08/g, "\\b")
    .replace(/\x0c/g, "\\f")
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r")
    .replace(/\t/g, "\\t");
};

// 加载配置
const loadConfig = async () => {
  configLoading.value = true;
  error.value = null;

  try {
    const data = await getInstanceConfig(instanceId);
    if (data) {
      const parsed = parseConfigToSections(data);
      config.value = parsed;
      originalConfig.value = JSON.parse(JSON.stringify(parsed));
      rawConfig.value = objectToToml(mergeConfigToToml(parsed));
    }
  } catch (err: any) {
    error.value = err.message || "加载配置失败";
  } finally {
    configLoading.value = false;
  }
};

// 重置配置
const resetConfig = () => {
  if (Object.keys(originalConfig.value).length > 0) {
    config.value = JSON.parse(JSON.stringify(originalConfig.value));
  }
};

// 复制配置
const copyConfig = async () => {
  try {
    const tomlContent = objectToToml(mergeConfigToToml(config.value));
    await navigator.clipboard.writeText(tomlContent);
    success("配置已复制到剪贴板", { type: "success" });
  } catch {
    showError("复制失败", { type: "error" });
  }
};

// 保存配置
const handleSave = async () => {
  // 只获取修改过的 section
  const changedSections = getChangedSections();

  if (Object.keys(changedSections).length === 0) {
    success("没有需要保存的更改", { type: "info" });
    return;
  }

  const tomlContent = sectionsToToml(changedSections);

  isSaving.value = true;
  error.value = null;

  try {
    await saveInstanceConfig(instanceId, undefined, tomlContent);
    success("配置已保存", { type: "success" });

    // 更新原始值副本
    for (const [key, value] of Object.entries(changedSections)) {
      originalSectionConfigs.value[key] = JSON.parse(JSON.stringify(value));
    }
    originalConfig.value = JSON.parse(JSON.stringify(config.value));
    rawConfig.value = objectToToml(mergeConfigToToml(config.value));
    showSaveSuccessDialog.value = true;
  } catch (err: any) {
    const errorMsg =
      err.response?.data?.message || err.message || "保存配置失败";
    error.value = errorMsg;
  } finally {
    isSaving.value = false;
  }
};

// 保存成功后重启
const handleSaveSuccessRestart = async () => {
  showSaveSuccessDialog.value = false;
  await confirmRestart();
};

// 重启实例
const handleRestart = () => {
  showRestartDialog.value = true;
};

const confirmRestart = async () => {
  showRestartDialog.value = false;
  restartLoading.value = true;

  try {
    const result = await restartInstanceAsync(instanceId);
    if (result) {
      success("实例重启中...", { type: "success" });
      setTimeout(() => {
        refreshInstances();
      }, 2000);
    } else {
      error.value = instanceErrors[instanceId] || "重启失败";
    }
  } finally {
    restartLoading.value = false;
  }
};

// 启动实例
const handleStart = async () => {
  operationLoading.value = true;
  try {
    await startInstanceAsync(instanceId);
    success("实例启动中...", { type: "success" });
    handleRefresh();
  } finally {
    operationLoading.value = false;
  }
};

// 停止实例
const handleStop = async () => {
  operationLoading.value = true;
  try {
    await stopInstanceAsync(instanceId);
    success("实例停止中...", { type: "success" });
    handleRefresh();
  } finally {
    operationLoading.value = false;
  }
};

// 刷新状态
const handleRefresh = async () => {
  await refreshInstances();
  await loadConfig();
};

// 状态工具函数
const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    stopped: tm("status.stopped"),
    starting: tm("status.starting"),
    running: tm("status.running"),
    stopping: tm("status.stopping"),
    error: tm("status.error"),
    restarting: tm("status.restarting"),
  };
  return map[status] || "未知";
};

const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    stopped: "grey",
    starting: "warning",
    running: "success",
    stopping: "warning",
    error: "error",
    restarting: "info",
  };
  return map[status] || "grey";
};

const formatDate = (dateStr: string | undefined): string => {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    return date.toLocaleString("zh-CN");
  } catch {
    return dateStr;
  }
};

// 初始化
onMounted(async () => {
  await refreshInstances();
  await loadConfig();
});
</script>
